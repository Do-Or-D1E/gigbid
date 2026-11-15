"""Approvals: the human gate. A decision resumes the interrupted LangGraph thread (as a new
run, executed by the worker); pending approvals live in Postgres, so a page refresh or an
API restart never loses one."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agent import db
from apps.api.auth.users import CurrentUser
from apps.api.dispatch import dispatch
from apps.api.schemas import ApprovalOut, DecisionIn, RegenerateIn, RegenerateOut, RunRef

router = APIRouter(prefix="/api", tags=["approvals"])


def approval_out(r: dict) -> ApprovalOut:
    return ApprovalOut(thread_id=r["thread_id"], kind=r["kind"], job_id=r.get("job_id"), status=r["status"],
                       payload=r["payload"], decision=r.get("decision"), run_id=r.get("run_id"),
                       created_at=r["created_at"].isoformat() if r.get("created_at") else None)


@router.get("/approvals", response_model=list[ApprovalOut])
async def list_approvals(status: str = "pending", user: dict = CurrentUser) -> list[ApprovalOut]:
    rows = await db.fetch("select * from approvals where user_id=%s and status=%s order by created_at desc",
                          user["id"], status)
    return [approval_out(r) for r in rows]


@router.get("/approvals/{thread_id}", response_model=ApprovalOut)
async def get_approval(thread_id: str, user: dict = CurrentUser) -> ApprovalOut:
    row = await db.fetchone("select * from approvals where user_id=%s and thread_id=%s", user["id"], thread_id)
    if not row:
        raise HTTPException(404, "no approval for this thread")
    return approval_out(row)


@router.post("/approvals/{thread_id}/decision", response_model=RunRef)
async def decide(thread_id: str, body: DecisionIn, user: dict = CurrentUser) -> RunRef:
    if body.action == "reject" and not (body.reason or "").strip():
        raise HTTPException(422, "a reason is required to reject")
    if body.action == "edit" and not (body.edited_cover_letter or body.edited_answers):
        raise HTTPException(422, "an edit needs the edited text")
    # Atomic pending -> decided: a double click or a retried request cannot resume twice.
    row = await db.fetchone("update approvals set status=%s, decision=%s, decided_at=now() where user_id=%s and"
                            " thread_id=%s and status='pending' returning *",
                            {"approve": "approved", "edit": "edited", "reject": "rejected"}[body.action],
                            db.jsonb({**body.model_dump(), "user_id": user["id"]}), user["id"], thread_id)
    if not row:
        raise HTTPException(409, "nothing pending for this thread (already decided?)")
    kind = "conversation_resume" if row["kind"] == "message" else "bid_resume"
    run_id = await dispatch(user["id"], kind, thread_id, job_id=row.get("job_id"),
                            payload={"decision": {**body.model_dump(exclude_none=True), "user_id": user["id"]}})
    if row.get("job_id") and row["kind"] == "proposal":
        await db.execute("update jobs set status=%s, updated_at=now() where user_id=%s and job_id=%s",
                         {"approve": "submitting", "edit": "rechecking", "reject": "rejected"}[body.action],
                         user["id"], row["job_id"])
    return RunRef(run_id=run_id, thread_id=thread_id)


@router.post("/proposals/{thread_id}/regenerate", response_model=RegenerateOut)
async def regenerate(thread_id: str, body: RegenerateIn, user: dict = CurrentUser) -> RegenerateOut:
    """Proposal studio: rewrite one paragraph. The result goes through the deterministic policy
    scrub immediately and through the full Compliance Guard when the user submits an edit."""
    from agent import llm, runner
    from agent.nodes.compliance import scrub
    from agent.nodes.writer import regenerate_paragraph

    row = await db.fetchone("select 1 from approvals where user_id=%s and thread_id=%s", user["id"], thread_id)
    if not row:
        raise HTTPException(404, "no draft for this thread")
    g = await runner.graphs()
    state = (await g["bid"].aget_state({"configurable": {"thread_id": thread_id}})).values
    paragraphs = [p for p in (state.get("draft") or {}).get("cover_letter", "").split("\n\n") if p.strip()]
    if body.paragraph_index >= len(paragraphs):
        raise HTTPException(422, "no such paragraph")
    try:
        text = await regenerate_paragraph(state, body.paragraph_index, body.instruction)
    except llm.BudgetExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    cleaned, violations = scrub(text)
    return RegenerateOut(text=cleaned, removed=[v.excerpt for v in violations])
