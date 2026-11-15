"""Run executor shared by the worker (Arq) and the serverless inline mode.

A run is one execution step of a graph thread: a new bid analysis, a resume after a human
decision, a continuation after the marketplace came back, or a conversation turn. The
`runs` table is the durable queue; claiming is a single UPDATE, so two workers can never
execute the same run, and a crashed worker's run is reclaimed after its heartbeat goes
stale and continues from the last checkpoint (submission is idempotent)."""
from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import AsyncExitStack
from typing import Any

from langgraph.types import Command

from agent import db, llm, settings, tracing
from agent.mcp_client import MarketplaceDown, McpGateway

STALE_S = 180
_graphs: dict[str, Any] = {}
_stack: AsyncExitStack | None = None
_lock = asyncio.Lock()


async def graphs() -> dict[str, Any]:
    """Compile both graphs once per process with the Postgres checkpointer and store."""
    global _stack
    async with _lock:
        if _graphs:
            return _graphs
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.store.postgres.aio import AsyncPostgresStore

        from agent.graphs import bid_graph, conversation_graph
        from agent.memory.store import set_fallback

        _stack = AsyncExitStack()
        saver = await _stack.enter_async_context(AsyncPostgresSaver.from_conn_string(db.url()))
        store = await _stack.enter_async_context(AsyncPostgresStore.from_conn_string(db.url()))
        await saver.setup()
        await store.setup()
        set_fallback(store)
        _graphs.update(bid=bid_graph.build(saver, store), conversation=conversation_graph.build(saver, store),
                       store=store, saver=saver)
        return _graphs


async def profile_for(user_id: str) -> dict[str, Any]:
    import json

    from rag.ingest.loaders import PERSONA_DIR

    user = await db.fetchone("select persona_id from users where id=%s", user_id)
    row = await db.fetchone("select data from user_settings where user_id=%s", user_id)
    persona = (user or {}).get("persona_id") or "ai_ml"
    base: dict[str, Any] = {}
    p = PERSONA_DIR / persona / "profile.json"
    if p.exists():
        base = json.loads(p.read_text(encoding="utf-8"))
    data = (row or {}).get("data") or {}
    base.update({k: v for k, v in data.items() if v not in (None, "")})
    base.setdefault("autonomy", settings.get("autonomy.default", "suggest"))
    base["persona_id"] = persona
    return base


# ----------------------------------------------------------------------------- queue
async def enqueue(user_id: str, kind: str, thread_id: str, *, job_id: str | None = None,
                  payload: dict | None = None) -> str:
    run_id = "run_" + uuid.uuid4().hex[:16]
    trace_id = tracing.request_trace.get() or uuid.uuid4().hex
    await db.execute("insert into runs(run_id, user_id, thread_id, kind, job_id, input, trace_id) "
                     "values (%s,%s,%s,%s,%s,%s,%s)", run_id, user_id, thread_id, kind, job_id,
                     db.jsonb(payload or {}), trace_id)
    await event(run_id, "queued", None, {"kind": kind})
    return run_id


async def claim(run_id: str | None = None) -> dict | None:
    """Claim a specific run, or the oldest queued one, or a stale running one."""
    cond = "run_id=%s and " if run_id else ""
    args: tuple = (run_id,) if run_id else ()
    sql = (f"update runs set status='running', attempts=attempts+1, started_at=coalesce(started_at, now()),"
           f" heartbeat_at=now() where run_id = (select run_id from runs where {cond}"
           f" (status in ('queued','retry') or (status='running' and heartbeat_at < now() - interval '{STALE_S} seconds'))"
           f" order by created_at limit 1 for update skip locked) returning *")
    return await db.fetchone(sql, *args)


async def event(run_id: str, kind: str, node: str | None, payload: dict | None = None) -> None:
    await db.execute("insert into run_events(run_id, kind, node, payload) values (%s,%s,%s,%s)",
                     run_id, kind, node, db.jsonb(payload or {}))


async def _heartbeat(run_id: str) -> None:
    await db.execute("update runs set heartbeat_at=now() where run_id=%s", run_id)


# ----------------------------------------------------------------------------- execute
async def execute(run: dict) -> dict:
    g = await graphs()
    kind, user_id, thread_id, run_id = run["kind"], run["user_id"], run["thread_id"], run["run_id"]
    graph = g["conversation"] if kind.startswith("conversation") else g["bid"]
    profile = await profile_for(user_id)
    persona = profile["persona_id"]
    spans: list[tracing.Span] = []
    usages: list[llm.Usage] = []
    tok_t, tok_u = tracing.current_trace.set(spans), llm.usage_sink.set(usages)
    t0 = time.perf_counter()
    status, error = "done", None
    root_run_id = None
    payload = run.get("input") or {}
    try:
        async with McpGateway(user_id, persona, trace_id=run["trace_id"]) as gw:
            config = {"configurable": {"thread_id": thread_id, "gateway": gw},
                      "run_name": f"{graph.name}:{run.get('job_id') or thread_id}",
                      "metadata": {"gigbid_run_id": run_id, "trace_id": run["trace_id"], "user_id": user_id,
                                   "kind": kind, "profile": settings.config()["profile"]},
                      "tags": [kind, settings.config()["profile"]], "recursion_limit": 80}
            if payload.get("checkpoint_id"):  # replay from a checkpoint (time travel fork)
                config["configurable"]["checkpoint_id"] = payload["checkpoint_id"]
            snapshot = await graph.aget_state(config)
            if kind in ("bid", "conversation") and not snapshot.values:
                inp: Any = {"user_id": user_id, "persona": persona, "run_id": run_id, "profile": profile,
                            **({"job_id": run["job_id"], "job": payload.get("job")} if kind == "bid" else
                               {"thread_id": payload["thread_id"], "job_id": run.get("job_id")})}
            elif snapshot.interrupts and payload.get("decision"):
                inp = Command(resume=payload["decision"])
            elif payload.get("override"):
                await graph.aupdate_state(config, payload["override"], as_node="decide")
                inp = None
            else:
                inp = None  # continue from the last checkpoint (retry / recovery)
            from langchain_core.tracers.context import collect_runs

            with collect_runs() as cb:
                last_beat = time.monotonic()
                async for mode, chunk in graph.astream(inp, config, stream_mode=["updates", "custom"]):
                    if mode == "custom":
                        await event(run_id, chunk.get("event", "custom"), chunk.get("node"), chunk)
                    else:
                        for node, update in chunk.items():
                            if node == "__interrupt__":
                                intr = update[0].value if update else {}
                                await _store_approval(run, intr)
                                await event(run_id, "interrupt", None, {"kind": intr.get("kind")})
                                status = "awaiting_approval"
                            else:
                                await event(run_id, "update", node, _brief(update))
                    if time.monotonic() - last_beat > 15:
                        await _heartbeat(run_id)
                        last_beat = time.monotonic()
                if cb.traced_runs:
                    root_run_id = str(cb.traced_runs[0].id)
            final = (await graph.aget_state(config)).values
            if status != "awaiting_approval":
                status = _final_status(final)
            await _sync_job(run, final)
    except MarketplaceDown as exc:
        status, error = "waiting_marketplace", str(exc)[:500]
        await event(run_id, "marketplace_down", None, {"error": error})
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {str(exc)[:500]}"
        status = "retry" if run.get("attempts", 1) < 3 else "dead_letter"
        await event(run_id, "error", None, {"error": error, "next": status})
    finally:
        tracing.current_trace.reset(tok_t)
        llm.usage_sink.reset(tok_u)
    metrics = {**llm.summarize(usages), "latency_s": round(time.perf_counter() - t0, 3)}
    trace_url = None
    if root_run_id and settings.get("observability.langsmith", True):
        import os

        trace_url = f"langsmith:{os.environ.get('LANGSMITH_PROJECT', 'gigbid')}:{root_run_id}"
    tracing.persist(spans, run_id=run_id, trace_id=run["trace_id"], user_id=user_id)
    await db.execute("update runs set status=%s, error=%s, metrics=%s, trace_url=coalesce(%s, trace_url),"
                     " finished_at=case when %s in ('done','awaiting_approval','dead_letter','needs_attention',"
                     "'blocked','skipped','submitted','rejected','sent') then now() else finished_at end where run_id=%s",
                     status, error, db.jsonb(metrics), trace_url, status, run_id)
    await event(run_id, "done", None, {"status": status, **metrics})
    if status == "dead_letter" and run.get("job_id"):
        await db.execute("update jobs set status='dead_letter', updated_at=now() where user_id=%s and job_id=%s",
                         user_id, run["job_id"])
    return {"status": status, "error": error, **metrics}


def _final_status(final: dict) -> str:
    s = final.get("status") or "done"
    return {"skipped": "skipped", "watch": "done", "submitted": "submitted", "rejected": "rejected",
            "blocked": "blocked", "needs_attention": "needs_attention", "sent": "sent"}.get(s, "done")


async def _store_approval(run: dict, payload: dict) -> None:
    await db.execute(
        "insert into approvals(thread_id, user_id, run_id, kind, job_id, payload, status) values (%s,%s,%s,%s,%s,%s,'pending')"
        " on conflict (thread_id) do update set payload=excluded.payload, run_id=excluded.run_id, status='pending',"
        " decision=null, created_at=now(), decided_at=null",
        run["thread_id"], run["user_id"], run["run_id"], payload.get("kind", "proposal"), run.get("job_id"),
        db.jsonb(payload))


async def _sync_job(run: dict, final: dict) -> None:
    """Mirror the graph's outcome into the jobs/pipeline tables the UI reads."""
    if not run.get("job_id") or run["kind"].startswith("conversation"):
        return
    decision, fit, risk, price = (final.get(k) or {} for k in ("decision", "fit", "risk", "price"))
    status = final.get("status") or "analysed"
    summary = {"decision": decision, "fit": fit, "risk": risk, "job_spec": final.get("job_spec"),
               "claim_report": final.get("claim_report"), "compliance": final.get("compliance"),
               "critiques": final.get("critiques", []), "attention": final.get("attention"),
               "timings": final.get("timings"), "tokens": final.get("tokens"), "cost_usd": final.get("cost_usd"),
               "list_cost_usd": final.get("list_cost_usd")}
    await db.execute(
        "update jobs set status=%s, action=%s, fit_score=%s, risk_score=%s, price=%s, connects_cost=%s, summary=%s,"
        " thread_id=%s, updated_at=now() where user_id=%s and job_id=%s",
        status, decision.get("action"), fit.get("fit_score"), risk.get("risk_score"), db.jsonb(price or None),
        (price or {}).get("connects_cost"), db.jsonb(summary), run["thread_id"], run["user_id"], run["job_id"])
    sub = final.get("submission") or {}
    if sub.get("submit", {}).get("proposal_id"):
        pid = sub["submit"]["proposal_id"]
        draft = final.get("draft") or {}
        await db.execute(
            "insert into pipeline(user_id, proposal_id, job_id, stage, data) values (%s,%s,%s,'submitted',%s)"
            " on conflict (user_id, proposal_id) do nothing", run["user_id"], pid, run["job_id"],
            db.jsonb({"category": (final.get("job_spec") or {}).get("category"), "title": final["job"].get("title"),
                      "words": len(draft.get("cover_letter", "").split()),
                      "evidence_count": len(draft.get("cited_evidence_ids", [])),
                      "connects": sub["submit"].get("connects_spent"), "amount": (price or {}).get("amount"),
                      "cost_usd": final.get("cost_usd"), "list_cost_usd": final.get("list_cost_usd")}))


def _brief(update: Any) -> dict:
    import json

    if not isinstance(update, dict):
        return {"value": str(update)[:500]}
    keep = {}
    for k, v in update.items():
        if k in ("evidence", "job", "client", "profile"):
            keep[k] = f"<{len(v) if hasattr(v, '__len__') else 1} items>"
        else:
            keep[k] = v
    text = json.dumps(keep, default=str)
    return json.loads(text) if len(text) < 6000 else {"truncated": text[:6000]}


async def drain(max_runs: int = 5, budget_s: float = 240) -> list[dict]:
    """Serverless worker step: execute queued runs until the time budget is used."""
    t0 = time.monotonic()
    out = []
    while len(out) < max_runs and time.monotonic() - t0 < budget_s:
        run = await claim()
        if not run:
            break
        out.append({"run_id": run["run_id"], **await execute(run)})
    return out
