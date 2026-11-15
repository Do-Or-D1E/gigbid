"""Hands runs to the worker. With REDIS_URL set (docker compose) an Arq job is enqueued; on
serverless (no Redis) the run stays queued in Postgres and is executed by the SSE stream
request that watches it, or by the scheduled tick. Either way the graph never runs inside
the request that created it."""
from __future__ import annotations

import os

from agent import runner


async def dispatch(user_id: str, kind: str, thread_id: str, *, job_id: str | None = None,
                   payload: dict | None = None) -> str:
    run_id = await runner.enqueue(user_id, kind, thread_id, job_id=job_id, payload=payload)
    if os.environ.get("REDIS_URL"):
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
        await pool.enqueue_job("run_job", run_id, _job_id=run_id)
        await pool.aclose()
    return run_id


def inline_mode() -> bool:
    return not os.environ.get("REDIS_URL")
