"""Agent run viewer: live SSE stream, events, spans per node, checkpoint history and replay
from any checkpoint, and public LangSmith share links."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from agent import db, runner
from apps.api.auth.users import CurrentUser
from apps.api.dispatch import dispatch
from apps.api.routers.jobs import run_out
from apps.api.schemas import CheckpointOut, RunDetailOut, RunEventOut, RunOut, RunRef, ShareOut, SpanOut
from apps.api.streaming import stream_run

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs", response_model=list[RunOut])
async def list_runs(limit: int = 50, user: dict = CurrentUser) -> list[RunOut]:
    rows = await db.fetch("select * from runs where user_id=%s order by created_at desc limit %s", user["id"],
                          min(limit, 200))
    return [run_out(r) for r in rows]


@router.get("/runs/{run_id}", response_model=RunDetailOut)
async def get_run(run_id: str, user: dict = CurrentUser) -> RunDetailOut:
    r = await db.fetchone("select * from runs where run_id=%s and user_id=%s", run_id, user["id"])
    if not r:
        raise HTTPException(404, "run not found")
    events = await db.fetch("select * from run_events where run_id=%s order by id", run_id)
    spans = await db.fetch("select * from spans where run_id=%s order by id", run_id)
    per_node: dict[str, dict] = {}
    for s in spans:
        n = per_node.setdefault(s["node"] or s["name"], {"node": s["node"] or s["name"], "llm_calls": 0, "tool_calls": 0,
                                                         "tokens": 0, "usd": 0.0, "list_usd": 0.0, "latency_s": 0.0})
        n["llm_calls" if s["kind"] == "llm" else "tool_calls"] += 1
        n["tokens"] += (s["input_tokens"] or 0) + (s["output_tokens"] or 0)
        n["usd"] += s["usd"] or 0
        n["list_usd"] += s["list_usd"] or 0
        n["latency_s"] += s["latency_s"] or 0
    base = run_out(r)
    return RunDetailOut(**base.model_dump(),
                        events=[RunEventOut(id=e["id"], ts=e["ts"].isoformat(), kind=e["kind"], node=e["node"],
                                            payload=e["payload"]) for e in events],
                        spans=[SpanOut(**{k: s[k] for k in SpanOut.model_fields if k in s and s[k] is not None})
                               for s in spans],
                        per_node=list(per_node.values()))


@router.get("/runs/{run_id}/stream")
async def stream(run_id: str, request: Request, user: dict = CurrentUser):
    last = int(request.headers.get("last-event-id") or request.query_params.get("after") or 0)
    return EventSourceResponse(stream_run(run_id, user["id"], last), ping=15)


@router.get("/runs/{run_id}/history", response_model=list[CheckpointOut])
async def history(run_id: str, user: dict = CurrentUser) -> list[CheckpointOut]:
    r = await db.fetchone("select * from runs where run_id=%s and user_id=%s", run_id, user["id"])
    if not r:
        raise HTTPException(404, "run not found")
    g = await runner.graphs()
    graph = g["conversation"] if r["kind"].startswith("conversation") else g["bid"]
    out = []
    async for snap in graph.aget_state_history({"configurable": {"thread_id": r["thread_id"]}}, limit=60):
        out.append(CheckpointOut(checkpoint_id=snap.config["configurable"]["checkpoint_id"], next=list(snap.next),
                                 created_at=snap.created_at, status=(snap.values or {}).get("status")))
    return out


@router.post("/runs/{run_id}/replay/{checkpoint_id}", response_model=RunRef)
async def replay(run_id: str, checkpoint_id: str, user: dict = CurrentUser) -> RunRef:
    """Time travel: re-run the thread from a checkpoint. LangGraph forks the thread at that
    checkpoint, so the original history stays intact and the replay is a new branch."""
    r = await db.fetchone("select * from runs where run_id=%s and user_id=%s", run_id, user["id"])
    if not r:
        raise HTTPException(404, "run not found")
    g = await runner.graphs()
    graph = g["conversation"] if r["kind"].startswith("conversation") else g["bid"]
    snap = await graph.aget_state({"configurable": {"thread_id": r["thread_id"], "checkpoint_id": checkpoint_id}})
    if not snap.values:
        raise HTTPException(404, "checkpoint not found")
    kind = "conversation_replay" if r["kind"].startswith("conversation") else "replay"
    new_run = await dispatch(user["id"], kind, r["thread_id"], job_id=r.get("job_id"),
                             payload={"checkpoint_id": checkpoint_id})
    return RunRef(run_id=new_run, thread_id=r["thread_id"])


@router.post("/runs/{run_id}/share", response_model=ShareOut)
async def share(run_id: str, user: dict = CurrentUser) -> ShareOut:
    r = await db.fetchone("select trace_url from runs where run_id=%s and user_id=%s", run_id, user["id"])
    if not r or not r.get("trace_url"):
        raise HTTPException(404, "no LangSmith trace for this run")
    if r["trace_url"].startswith("http"):
        return ShareOut(url=r["trace_url"])
    if not os.environ.get("LANGSMITH_API_KEY"):
        raise HTTPException(503, "LangSmith is not configured")
    from langsmith import Client

    ls_run_id = r["trace_url"].rsplit(":", 1)[-1]
    url = Client().share_run(ls_run_id)
    await db.execute("update runs set trace_url=%s where run_id=%s", url, run_id)
    return ShareOut(url=url)
