"""SSE bridge to LangGraph streams. The worker writes every node event (from LangGraph's
`updates` and `custom` stream modes) to `run_events`; this endpoint tails that table, so a
page refresh or a second tab sees the same live progress and nothing is lost. In inline
(serverless) mode the stream request itself claims and executes a queued run."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from agent import db, runner
from apps.api.dispatch import inline_mode

TERMINAL = {"done", "awaiting_approval", "dead_letter", "needs_attention", "blocked", "skipped", "submitted",
            "rejected", "sent", "waiting_marketplace", "retry"}


async def _events_since(run_id: str, after: int) -> list[dict]:
    return await db.fetch("select id, ts, kind, node, payload from run_events where run_id=%s and id>%s order by id",
                          run_id, after)


async def stream_run(run_id: str, user_id: str, last_id: int = 0) -> AsyncIterator[dict]:
    run = await db.fetchone("select status from runs where run_id=%s and user_id=%s", run_id, user_id)
    if not run:
        yield {"event": "error", "data": json.dumps({"error": "run not found"})}
        return
    task = None
    if inline_mode() and run["status"] in ("queued", "retry"):
        claimed = await runner.claim(run_id)
        if claimed:
            task = asyncio.create_task(runner.execute(claimed))
    idle = 0
    while True:
        rows = await _events_since(run_id, last_id)
        for r in rows:
            last_id = r["id"]
            yield {"id": str(r["id"]), "event": r["kind"],
                   "data": json.dumps({"id": r["id"], "ts": r["ts"].isoformat(), "kind": r["kind"], "node": r["node"],
                                       "payload": r["payload"]}, default=str)}
        status = (await db.fetchone("select status from runs where run_id=%s", run_id))["status"]
        if status in TERMINAL and not rows and (task is None or task.done()):
            yield {"event": "end", "data": json.dumps({"status": status})}
            return
        idle = 0 if rows else idle + 1
        if idle and idle % 20 == 0:
            yield {"event": "ping", "data": "{}"}
        await asyncio.sleep(0.4)
