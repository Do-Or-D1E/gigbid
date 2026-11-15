"""Arq worker (Redis). Long agent runs and scouting execute here, never inside web
requests. Start with:  uv run arq worker.arq_worker.WorkerSettings

Idempotency: the API enqueues only a run id; `runner.claim` atomically marks it running,
so a duplicate Arq message or a restarted worker cannot execute a run twice, and a run
left 'running' by a crashed worker is reclaimed and continues from its checkpoint."""
from __future__ import annotations

import os

from arq import cron
from arq.connections import RedisSettings

from agent import db, runner
from worker import tasks


async def startup(ctx: dict) -> None:
    db.migrate()
    await runner.graphs()


async def run_job(ctx: dict, run_id: str) -> dict:
    run = await runner.claim(run_id)
    if not run:
        return {"run_id": run_id, "skipped": "already claimed or finished"}
    return await runner.execute(run)


async def scout_all(ctx: dict) -> dict:
    out = {}
    for u in await db.fetch("select distinct user_id from saved_searches where enabled"):
        out[u["user_id"]] = await tasks.scout_user(u["user_id"])
        out[u["user_id"]]["events"] = await tasks.poll_events(u["user_id"])
    redis = ctx["redis"]
    for run_ids in out.values():
        for rid in run_ids.get("queued", []) + run_ids.get("events", {}).get("conversations", []):
            await redis.enqueue_job("run_job", rid, _job_id=rid)
    return out


async def sweep(ctx: dict) -> dict:
    """Recover parked runs and pick up anything queued without an Arq message."""
    rec = await tasks.recover()
    drained = await runner.drain(max_runs=3, budget_s=120)
    return {"recover": rec, "drained": len(drained)}


class WorkerSettings:
    functions = [run_job]
    cron_jobs = [cron(scout_all, minute=set(range(0, 60, 10))), cron(sweep, minute=set(range(0, 60, 2)))]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    job_timeout = 600
    max_jobs = 4
