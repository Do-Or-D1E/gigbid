"""Postgres persistence (psycopg 3). Everything lives in the `gigsim` schema.

One short-lived connection per request (no pool, no background threads), autocommit on, with
explicit `conn.transaction()` blocks around multi-statement writes. Safe with many processes.
"""

from __future__ import annotations

import time

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import clock as clk
from .config import Settings

SCHEMA = "gigsim"
INIT_LOCK_KEY = 4016_0001

DDL = """
CREATE TABLE IF NOT EXISTS kv (key text PRIMARY KEY, value jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS counters (name text PRIMARY KEY, n bigint NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS accounts (
    account_id text PRIMARY KEY, token text UNIQUE NOT NULL, name text,
    weekly_allowance int NOT NULL DEFAULT 80);
CREATE TABLE IF NOT EXISTS clients (client_id text PRIMARY KEY, data jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (
    job_id text PRIMARY KEY, client_id text, source text NOT NULL, data jsonb NOT NULL,
    search_text text NOT NULL, skills_lc text[] NOT NULL DEFAULT '{}', category text,
    posted_us bigint, release_us bigint, seq bigserial);
CREATE INDEX IF NOT EXISTS jobs_client_idx ON jobs (client_id);
CREATE INDEX IF NOT EXISTS jobs_release_idx ON jobs (release_us);
CREATE TABLE IF NOT EXISTS historical_jobs (
    job_id text PRIMARY KEY, client_id text, category text, skills_lc text[] NOT NULL DEFAULT '{}',
    budget_type text, price double precision, posted_us bigint, data jsonb NOT NULL);
CREATE INDEX IF NOT EXISTS hist_client_idx ON historical_jobs (client_id);
CREATE SEQUENCE IF NOT EXISTS proposal_seq;
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id text PRIMARY KEY, account_id text NOT NULL, job_id text NOT NULL, client_id text,
    cover_letter text NOT NULL, screening_answers jsonb NOT NULL DEFAULT '[]',
    bid_amount double precision NOT NULL, bid_type text NOT NULL, status text NOT NULL,
    connects_spent int NOT NULL DEFAULT 0, created_us bigint NOT NULL, submitted_us bigint,
    policy_version text, decision jsonb);
CREATE INDEX IF NOT EXISTS proposals_acct_idx ON proposals (account_id, job_id);
CREATE TABLE IF NOT EXISTS connects_ledger (
    id bigserial PRIMARY KEY, account_id text NOT NULL, proposal_id text, job_id text,
    amount int NOT NULL, at_us bigint NOT NULL, kind text NOT NULL DEFAULT 'spend');
CREATE INDEX IF NOT EXISTS ledger_acct_idx ON connects_ledger (account_id, at_us);
CREATE TABLE IF NOT EXISTS idempotency (
    account_id text NOT NULL, key text NOT NULL, request_hash text NOT NULL, status int NOT NULL,
    body jsonb NOT NULL, created_us bigint NOT NULL, PRIMARY KEY (account_id, key));
CREATE TABLE IF NOT EXISTS events (
    event_id bigserial PRIMARY KEY, account_id text NOT NULL, proposal_id text, thread_id text,
    job_id text, type text NOT NULL, deliver_us bigint NOT NULL, status_to text, status_rank int,
    cancelable boolean NOT NULL DEFAULT false, payload jsonb NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS events_acct_idx ON events (account_id, deliver_us, event_id);
CREATE INDEX IF NOT EXISTS events_prop_idx ON events (proposal_id);
CREATE TABLE IF NOT EXISTS threads (
    thread_id text PRIMARY KEY, account_id text NOT NULL, proposal_id text NOT NULL, job_id text,
    client_id text, state jsonb NOT NULL, created_us bigint NOT NULL);
CREATE INDEX IF NOT EXISTS threads_acct_idx ON threads (account_id);
CREATE TABLE IF NOT EXISTS messages (
    message_id bigserial PRIMARY KEY, thread_id text NOT NULL, sender text NOT NULL, text text NOT NULL,
    intent text, created_us bigint NOT NULL, meta jsonb NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS messages_thread_idx ON messages (thread_id, created_us, message_id);
CREATE TABLE IF NOT EXISTS rate_events (token_hash text NOT NULL, ts double precision NOT NULL);
CREATE INDEX IF NOT EXISTS rate_events_idx ON rate_events (token_hash, ts);
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key text PRIMARY KEY, model text, features jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS llm_usage (
    id bigserial PRIMARY KEY, at_us bigint NOT NULL, model text, proposal_id text,
    prompt_tokens int NOT NULL DEFAULT 0, completion_tokens int NOT NULL DEFAULT 0,
    cost_usd double precision NOT NULL DEFAULT 0, cache_key text);
"""

RESET_TABLES = (
    "kv, counters, clients, jobs, historical_jobs, proposals, connects_ledger, idempotency, events, "
    "threads, messages, rate_events, llm_cache, llm_usage"
)

# Seed freelancer accounts (account id == persona id).
ACCOUNTS = [
    ("ai_ml", "gs-ai_ml-dev", "AI/ML Engineer"),
    ("fullstack", "gs-fullstack-dev", "Full-stack Developer"),
    ("data_analyst", "gs-data_analyst-dev", "Data Analyst"),
]


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(
            self.settings.database_url,
            autocommit=True,
            row_factory=dict_row,
            options=f"-c search_path={SCHEMA}",
        )

    # ---- schema / init ---------------------------------------------------------------------

    def init(self) -> None:
        """Create schema/tables idempotently, seed accounts, clock and (if empty) seed data."""
        from . import seed_loader

        with psycopg.connect(self.settings.database_url, autocommit=True, row_factory=dict_row) as boot:
            boot.execute("SELECT pg_advisory_lock(%s)", (INIT_LOCK_KEY,))
            try:
                boot.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            finally:
                boot.execute("SELECT pg_advisory_unlock(%s)", (INIT_LOCK_KEY,))
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_lock(%s)", (INIT_LOCK_KEY,))
            try:
                conn.execute(DDL)
                self._init_state(conn)
                seed_loader.seed_if_empty(conn, self.settings)
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (INIT_LOCK_KEY,))

    def _init_state(self, conn) -> None:
        for acct_id, token, name in ACCOUNTS:
            conn.execute(
                "INSERT INTO accounts (account_id, token, name, weekly_allowance) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (account_id) DO NOTHING",
                (acct_id, token, name, self.settings.weekly_allowance),
            )
        row = conn.execute("SELECT value FROM kv WHERE key = 'clock'").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO kv (key, value) VALUES ('clock', %s) ON CONFLICT (key) DO NOTHING",
                (Jsonb(clk.new_clock_state(self.settings.time_scale)),),
            )
        else:
            state = row["value"]
            if float(state.get("scale", 0)) != float(self.settings.time_scale):
                # Rebase so changing GIGSIM_TIME_SCALE on restart does not make time jump.
                now = time.time()
                new = {**state, "base_us": clk.sim_now_us(state, now), "start_real": now,
                       "scale": float(self.settings.time_scale)}
                conn.execute("UPDATE kv SET value = %s WHERE key = 'clock'", (Jsonb(new),))
        conn.execute("INSERT INTO counters (name, n) VALUES ('error_counter', 0) ON CONFLICT DO NOTHING")

    def reset(self, conn) -> None:
        """Wipe all data and reseed (accounts, clock, seed files)."""
        from . import seed_loader

        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (INIT_LOCK_KEY,))
            conn.execute(f"TRUNCATE {RESET_TABLES} RESTART IDENTITY")
            conn.execute("ALTER SEQUENCE proposal_seq RESTART WITH 1")
            self._init_state(conn)
            seed_loader.seed_if_empty(conn, self.settings)


# ---- generic helpers ---------------------------------------------------------------------------


def load_kv(conn) -> dict:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM kv").fetchall()}


def set_kv(conn, key: str, value) -> None:
    conn.execute(
        "INSERT INTO kv (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (key, Jsonb(value)),
    )
