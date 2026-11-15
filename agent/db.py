"""Postgres access shared by the API, worker and MCP servers. Every query that touches user
data is scoped by tenant (user id). The audit log is append-only (a trigger rejects
UPDATE and DELETE)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from agent import settings

SCHEMA = """
create extension if not exists vector;

create table if not exists users (
  id text primary key, email text unique not null, password_hash text not null, name text not null,
  persona_id text, created_at timestamptz default now());

create table if not exists user_settings (
  user_id text primary key references users(id) on delete cascade, data jsonb not null default '{}'::jsonb,
  updated_at timestamptz default now());

create table if not exists saved_searches (
  id bigserial primary key, user_id text references users(id) on delete cascade, name text not null,
  query text not null default '', filters jsonb not null default '{}'::jsonb, interval_minutes int not null default 30,
  last_run_at timestamptz, enabled boolean not null default true);

create table if not exists marketplace_accounts (
  user_id text references users(id) on delete cascade, mode text not null, account_id text not null,
  enc_token text not null, meta jsonb not null default '{}'::jsonb, created_at timestamptz default now(),
  primary key (user_id, mode));

create table if not exists jobs (
  user_id text references users(id) on delete cascade, job_id text not null, data jsonb not null,
  dedupe_key text, status text not null default 'new', action text, fit_score real, risk_score real,
  price jsonb, connects_cost int, summary jsonb not null default '{}'::jsonb, thread_id text,
  created_at timestamptz default now(), updated_at timestamptz default now(), primary key (user_id, job_id));
create index if not exists jobs_user_status on jobs(user_id, status);
create index if not exists jobs_dedupe on jobs(user_id, dedupe_key);

create table if not exists runs (
  run_id text primary key, user_id text references users(id) on delete cascade, thread_id text not null,
  kind text not null, job_id text, status text not null default 'queued', attempts int not null default 0,
  error text, input jsonb not null default '{}'::jsonb, metrics jsonb not null default '{}'::jsonb,
  trace_id text, trace_url text, created_at timestamptz default now(), started_at timestamptz,
  finished_at timestamptz, heartbeat_at timestamptz);
create index if not exists runs_status on runs(status, created_at);
create index if not exists runs_thread on runs(thread_id);

create table if not exists run_events (
  id bigserial primary key, run_id text not null, ts timestamptz default now(), kind text not null,
  node text, payload jsonb not null default '{}'::jsonb);
create index if not exists run_events_run on run_events(run_id, id);

create table if not exists approvals (
  thread_id text primary key, user_id text references users(id) on delete cascade, run_id text, kind text not null,
  job_id text, payload jsonb not null, status text not null default 'pending', decision jsonb,
  created_at timestamptz default now(), decided_at timestamptz);

create table if not exists pipeline (
  user_id text references users(id) on delete cascade, proposal_id text not null, job_id text, stage text not null,
  data jsonb not null default '{}'::jsonb, updated_at timestamptz default now(), primary key (user_id, proposal_id));

create table if not exists uploads (
  user_id text references users(id) on delete cascade, item_id text not null, kind text not null, title text not null,
  text text not null, created_at timestamptz default now(), primary key (user_id, item_id));

create table if not exists marketplace_cursor (
  user_id text primary key references users(id) on delete cascade, cursor text, polled_at timestamptz);

create table if not exists spans (
  id bigserial primary key, trace_id text, run_id text, user_id text, node text, kind text, name text,
  model text, input_tokens int default 0, output_tokens int default 0, usd double precision default 0,
  list_usd double precision default 0, latency_s double precision default 0, error text, ts timestamptz default now());
create index if not exists spans_run on spans(run_id);

create table if not exists audit_log (
  id bigserial primary key, ts timestamptz default now(), user_id text, server text, tool text not null,
  args jsonb, result jsonb, trace_id text, dry_run boolean default false, ok boolean default true);

create or replace function audit_log_append_only() returns trigger language plpgsql as $$
begin raise exception 'audit_log is append-only'; end $$;
drop trigger if exists audit_log_no_change on audit_log;
create trigger audit_log_no_change before update or delete on audit_log
  for each row execute function audit_log_append_only();

create table if not exists evidence_chunks (
  owner text not null, flavour text not null, chunk_id text not null, item_id text not null, text text not null,
  meta jsonb not null, embedding vector(256), primary key (owner, flavour, chunk_id));
"""


def url() -> str:
    u = settings.database_url()
    if not u:
        raise RuntimeError("DATABASE_URL is not set")
    return u


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(url(), autocommit=True, row_factory=dict_row) as conn:
        yield conn


def migrate() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)


def jsonb(value: Any) -> Jsonb:
    return Jsonb(json.loads(json.dumps(value, default=str)))


_pool = None


async def pool():
    global _pool
    if _pool is None:
        from psycopg_pool import AsyncConnectionPool

        _pool = AsyncConnectionPool(url(), min_size=1, max_size=8, open=False,
                                    kwargs={"autocommit": True, "row_factory": dict_row})
        await _pool.open()
    return _pool


@asynccontextmanager
async def aconnect() -> AsyncIterator[psycopg.AsyncConnection]:
    p = await pool()
    async with p.connection() as conn:
        yield conn


async def fetch(sql: str, *args: Any) -> list[dict]:
    async with aconnect() as conn:
        cur = await conn.execute(sql, args)
        return await cur.fetchall() if cur.description else []


async def fetchone(sql: str, *args: Any) -> dict | None:
    rows = await fetch(sql, *args)
    return rows[0] if rows else None


async def execute(sql: str, *args: Any) -> None:
    async with aconnect() as conn:
        await conn.execute(sql, args)
