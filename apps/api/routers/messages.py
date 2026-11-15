"""Pipeline board and client messages. Marketplace data is read through the Marketplace
MCP server (the API never calls GigSim directly)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agent import db, runner
from agent.mcp_client import MarketplaceDown, McpGateway
from apps.api.auth.users import CurrentUser
from apps.api.dispatch import dispatch
from apps.api.routers.approvals import approval_out
from apps.api.routers.jobs import run_out
from apps.api.schemas import MessageOut, PipelineCard, PipelineOut, RunRef, ThreadDetailOut, ThreadOut

router = APIRouter(prefix="/api", tags=["messages"])
STAGES = ["drafted", "submitted", "viewed", "replied", "interview", "hired", "lost"]


@router.get("/pipeline", response_model=PipelineOut)
async def pipeline(user: dict = CurrentUser) -> PipelineOut:
    cols: dict[str, list[PipelineCard]] = {s: [] for s in STAGES}
    for a in await db.fetch("select a.*, j.data from approvals a left join jobs j on j.user_id=a.user_id and"
                            " j.job_id=a.job_id where a.user_id=%s and a.kind='proposal' and a.status='pending'",
                            user["id"]):
        price = (a["payload"] or {}).get("price") or {}
        cols["drafted"].append(PipelineCard(proposal_id=a["thread_id"], job_id=a.get("job_id"),
                                            title=(a.get("data") or {}).get("title", ""), stage="drafted",
                                            amount=price.get("amount"), connects=price.get("connects_cost"),
                                            thread_id=a["thread_id"],
                                            updated_at=a["created_at"].isoformat()))
    for p in await db.fetch("select * from pipeline where user_id=%s order by updated_at desc", user["id"]):
        stage = p["stage"] if p["stage"] in cols else "submitted"
        cols[stage].append(PipelineCard(proposal_id=p["proposal_id"], job_id=p.get("job_id"),
                                        title=p["data"].get("title", ""), stage=stage, amount=p["data"].get("amount"),
                                        connects=p["data"].get("connects"), updated_at=p["updated_at"].isoformat()))
    return PipelineOut(columns=cols)


@router.post("/pipeline/sync", response_model=dict)
async def sync(user: dict = CurrentUser) -> dict:
    from worker.tasks import poll_events

    try:
        return await poll_events(user["id"])
    except MarketplaceDown as exc:
        raise HTTPException(503, f"marketplace unavailable: {exc}") from exc


async def _gw(user: dict) -> McpGateway:
    profile = await runner.profile_for(user["id"])
    return McpGateway(user["id"], profile["persona_id"], trace_id=f"ui-{user['id']}")


@router.get("/messages/threads", response_model=list[ThreadOut])
async def threads(user: dict = CurrentUser) -> list[ThreadOut]:
    try:
        async with await _gw(user) as gw:
            data = await gw.call("list_threads", {})
    except MarketplaceDown as exc:
        raise HTTPException(503, f"marketplace unavailable: {exc}") from exc
    pending = {r["payload"].get("thread_id") for r in await db.fetch(
        "select payload from approvals where user_id=%s and kind='message' and status='pending'", user["id"])}
    out = []
    for t in data.get("threads", []):
        last = t.get("last_message") or {}
        out.append(ThreadOut(thread_id=t["thread_id"], job_id=t.get("job_id"), title=t.get("job_title") or t.get("title", ""),
                             last_message=(last.get("text") if isinstance(last, dict) else str(last or ""))[:200],
                             last_sender=last.get("sender") if isinstance(last, dict) else None,
                             updated_at=t.get("updated_at"), pending_reply=t["thread_id"] in pending))
    return out


@router.get("/messages/threads/{thread_id}", response_model=ThreadDetailOut)
async def thread(thread_id: str, user: dict = CurrentUser) -> ThreadDetailOut:
    try:
        async with await _gw(user) as gw:
            data = await gw.call("list_messages", {"thread_id": thread_id})
    except MarketplaceDown as exc:
        raise HTTPException(503, f"marketplace unavailable: {exc}") from exc
    appr = await db.fetchone("select * from approvals where user_id=%s and kind='message' and payload->>'thread_id'=%s"
                             " order by created_at desc limit 1", user["id"], thread_id)
    runs = await db.fetch("select * from runs where user_id=%s and thread_id like %s order by created_at desc limit 10",
                          user["id"], f"conv:{user['id']}:{thread_id}:%")
    return ThreadDetailOut(
        thread_id=thread_id,
        messages=[MessageOut(sender=m.get("sender") or "?", text=m.get("text", ""),
                             at=m.get("sent_at") or m.get("at") or m.get("sim_time")) for m in data.get("messages", [])],
        approval=approval_out(appr) if appr else None, runs=[run_out(r) for r in runs])


@router.post("/messages/threads/{thread_id}/suggest", response_model=RunRef)
async def suggest(thread_id: str, user: dict = CurrentUser) -> RunRef:
    busy = await db.fetchone("select run_id, thread_id, status from runs where user_id=%s and thread_id like %s and"
                             " status in ('queued','running')", user["id"], f"conv:{user['id']}:{thread_id}:%")
    if busy:
        return RunRef(run_id=busy["run_id"], thread_id=busy["thread_id"], status=busy["status"])
    import uuid

    tid = f"conv:{user['id']}:{thread_id}:{uuid.uuid4().hex[:6]}"
    run_id = await dispatch(user["id"], "conversation", tid, payload={"thread_id": thread_id})
    return RunRef(run_id=run_id, thread_id=tid)
