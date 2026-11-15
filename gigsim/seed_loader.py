"""Seed loading: clients.json, stream_jobs.jsonl, historical jobs (for pricing stats)."""

from __future__ import annotations

import json
from pathlib import Path

from psycopg.types.json import Jsonb

from . import clock as clk
from .config import Settings

# Fields that exist in seed/stream files but must never be exposed to agents (ground truth labels).
INTERNAL_JOB_FIELDS = ("release_order", "dup_of", "release_at_offset_hours", "gold")


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def public_job(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in INTERNAL_JOB_FIELDS}


def _search_text(job: dict) -> str:
    parts = [job.get("title", ""), job.get("description", ""), " ".join(job.get("skills") or [])]
    return " ".join(str(p) for p in parts).lower()


def upsert_job(conn, job: dict, source: str, release_us: int | None = None) -> None:
    skills_lc = [str(s).lower() for s in (job.get("skills") or [])]
    conn.execute(
        """INSERT INTO jobs (job_id, client_id, source, data, search_text, skills_lc, category, posted_us, release_us)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (job_id) DO UPDATE SET client_id = EXCLUDED.client_id, source = EXCLUDED.source,
             data = EXCLUDED.data, search_text = EXCLUDED.search_text, skills_lc = EXCLUDED.skills_lc,
             category = EXCLUDED.category, posted_us = EXCLUDED.posted_us, release_us = EXCLUDED.release_us""",
        (
            job["job_id"], job.get("client_id"), source, Jsonb(job), _search_text(job), skills_lc,
            job.get("category"), clk.parse_iso(job.get("posted_at")), release_us,
        ),
    )


def upsert_client(conn, client: dict) -> None:
    conn.execute(
        "INSERT INTO clients (client_id, data) VALUES (%s,%s) "
        "ON CONFLICT (client_id) DO UPDATE SET data = EXCLUDED.data",
        (client["client_id"], Jsonb(client)),
    )


def stream_release_us(job: dict, settings: Settings) -> int:
    if job.get("release_at_offset_hours") is not None:
        hours = float(job["release_at_offset_hours"])
    else:
        hours = float(job.get("release_order") or 0) * settings.stream_interval_hours
    return clk.EPOCH_US + clk.hours_to_us(hours)


def _count(conn, sql: str) -> int:
    return conn.execute(sql).fetchone()["c"]


def historical_price(j: dict) -> float | None:
    if j.get("awarded_usd") is not None:
        return float(j["awarded_usd"])
    lo, hi = j.get("budget_min"), j.get("budget_max")
    if lo is not None and hi is not None:
        return (float(lo) + float(hi)) / 2
    return None


def load_historical(conn, rows: list[dict]) -> int:
    n = 0
    for j in rows:
        conn.execute(
            """INSERT INTO historical_jobs (job_id, client_id, category, skills_lc, budget_type, price, posted_us, data)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (job_id) DO NOTHING""",
            (
                j["job_id"], j.get("client_id"), j.get("category"),
                [str(s).lower() for s in (j.get("skills") or [])], j.get("budget_type"),
                historical_price(j), clk.parse_iso(j.get("posted_at")), Jsonb(j),
            ),
        )
        n += 1
    return n


def seed_if_empty(conn, settings: Settings) -> dict:
    """Load seed files into tables that are empty. Missing files are fine (tables stay empty)."""
    loaded = {"clients": 0, "stream_jobs": 0, "historical_jobs": 0}
    seed_dir = Path(settings.seed_dir)
    data_dir = Path(settings.data_dir)
    if _count(conn, "SELECT count(*) AS c FROM clients") == 0:
        p = seed_dir / "clients.json"
        if p.exists():
            clients = json.loads(p.read_text(encoding="utf-8"))
            for c in clients:
                upsert_client(conn, c)
            loaded["clients"] = len(clients)
    if _count(conn, "SELECT count(*) AS c FROM jobs WHERE source = 'stream'") == 0:
        rows = read_jsonl(seed_dir / "stream_jobs.jsonl")
        for j in rows:
            upsert_job(conn, j, "stream", stream_release_us(j, settings))
        loaded["stream_jobs"] = len(rows)
    if _count(conn, "SELECT count(*) AS c FROM historical_jobs") == 0:
        loaded["historical_jobs"] = load_historical(conn, read_jsonl(data_dir / "jobs" / "historical.jsonl"))
    return loaded
