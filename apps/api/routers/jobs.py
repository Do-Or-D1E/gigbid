"""Job inbox and job detail."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agent import db
from apps.api.auth.users import CurrentUser
from apps.api.dispatch import dispatch
from apps.api.schemas import EvidenceOut, JobCard, JobDetailOut, MatrixRow, PriceOut, RiskFlagOut, RunOut, RunRef, SkipIn

router = APIRouter(prefix="/api", tags=["jobs"])


def card(row: dict) -> JobCard:
    job, summary = row["data"], row.get("summary") or {}
    risk = summary.get("risk") or {}
    price = row.get("price")
    return JobCard(
        job_id=row["job_id"], title=job.get("title", ""), category=job.get("category"),
        budget_type=job.get("budget_type"), budget_min=job.get("budget_min"), budget_max=job.get("budget_max"),
        posted_at=job.get("posted_at"), status=row["status"], action=row.get("action"),
        fit_score=row.get("fit_score"), risk_score=row.get("risk_score"),
        risk_flags=[RiskFlagOut(kind=f.get("kind", "other"), evidence=f.get("evidence", "")[:200],
                                severity=f.get("severity", "medium")) for f in risk.get("flags", [])],
        price=PriceOut(**{k: price.get(k) for k in PriceOut.model_fields if k in price}) if price else None,
        connects_cost=row.get("connects_cost") or job.get("connects_cost"),
        injection_detected=bool(risk.get("injected_instructions")) or any(
            f.get("kind") == "injection" for f in risk.get("flags", [])),
        thread_id=row.get("thread_id"), updated_at=row["updated_at"].isoformat() if row.get("updated_at") else None)


def run_out(r: dict) -> RunOut:
    return RunOut(run_id=r["run_id"], kind=r["kind"], status=r["status"], thread_id=r["thread_id"],
                  job_id=r.get("job_id"), created_at=r["created_at"].isoformat() if r.get("created_at") else None,
                  finished_at=r["finished_at"].isoformat() if r.get("finished_at") else None,
                  metrics=r.get("metrics") or {}, trace_url=r.get("trace_url"), error=r.get("error"))


@router.get("/jobs", response_model=list[JobCard])
async def inbox(status: str | None = None, action: str | None = None, q: str | None = None,
                user: dict = CurrentUser) -> list[JobCard]:
    sql = "select * from jobs where user_id=%s"
    args: list = [user["id"]]
    if status:
        sql += " and status=%s"
        args.append(status)
    if action:
        sql += " and action=%s"
        args.append(action)
    if q:
        sql += " and (data->>'title' ilike %s or data->>'description' ilike %s)"
        args += [f"%{q}%", f"%{q}%"]
    sql += " order by coalesce(fit_score, -1) desc, updated_at desc limit 200"
    return [card(r) for r in await db.fetch(sql, *args)]


@router.get("/jobs/{job_id}", response_model=JobDetailOut)
async def job_detail(job_id: str, user: dict = CurrentUser) -> JobDetailOut:
    row = await db.fetchone("select * from jobs where user_id=%s and job_id=%s", user["id"], job_id)
    if not row:
        raise HTTPException(404, "job not found")
    s = row.get("summary") or {}
    fit = s.get("fit") or {}
    runs = await db.fetch("select * from runs where user_id=%s and job_id=%s order by created_at desc limit 20",
                          user["id"], job_id)
    ev = {}
    if row.get("thread_id"):
        from agent import runner

        g = await runner.graphs()
        st = await g["bid"].aget_state({"configurable": {"thread_id": row["thread_id"]}})
        ev = {e["item_id"]: e for e in (st.values or {}).get("evidence", [])}
    matrix = [MatrixRow(requirement=m.get("requirement", ""), strength=m.get("strength", "none"),
                        reason=m.get("reason", ""),
                        evidence=[EvidenceOut(**{k: ev[i].get(k) for k in EvidenceOut.model_fields if k in ev[i]})
                                  for i in m.get("evidence_ids", []) if i in ev])
              for m in fit.get("matches", [])]
    pending = await db.fetchone("select 1 from approvals where user_id=%s and job_id=%s and status='pending'",
                                user["id"], job_id)
    return JobDetailOut(card=card(row), job=row["data"], job_spec=s.get("job_spec"), risk=s.get("risk"), fit=fit or None,
                        decision=s.get("decision"), matrix=matrix, claim_report=s.get("claim_report"),
                        compliance=s.get("compliance"), critiques=s.get("critiques") or [], attention=s.get("attention"),
                        runs=[run_out(r) for r in runs], approval_pending=bool(pending))


@router.post("/jobs/{job_id}/analyze", response_model=RunRef)
async def analyze(job_id: str, user: dict = CurrentUser) -> RunRef:
    row = await db.fetchone("select * from jobs where user_id=%s and job_id=%s", user["id"], job_id)
    if not row:
        raise HTTPException(404, "job not found")
    busy = await db.fetchone("select run_id, thread_id, status from runs where user_id=%s and job_id=%s and status in"
                             " ('queued','running','retry')", user["id"], job_id)
    if busy:  # idempotent: never double-analyse the same job
        return RunRef(run_id=busy["run_id"], thread_id=busy["thread_id"], status=busy["status"])
    thread = f"bid:{user['id']}:{job_id}"
    run_id = await dispatch(user["id"], "bid", thread, job_id=job_id, payload={"job": row["data"]})
    await db.execute("update jobs set status='queued', updated_at=now() where user_id=%s and job_id=%s",
                     user["id"], job_id)
    return RunRef(run_id=run_id, thread_id=thread)


@router.post("/jobs/{job_id}/draft", response_model=RunRef)
async def draft_anyway(job_id: str, user: dict = CurrentUser) -> RunRef:
    """The freelancer overrides a watch/skip recommendation and asks for a draft."""
    row = await db.fetchone("select thread_id from jobs where user_id=%s and job_id=%s", user["id"], job_id)
    if not row or not row.get("thread_id"):
        raise HTTPException(409, "analyse the job first")
    run_id = await dispatch(user["id"], "bid_override", row["thread_id"], job_id=job_id, payload={
        "override": {"decision": {"action": "bid", "reasons": ["Freelancer chose to bid"], "auto": False},
                     "status": "pricing"}})
    return RunRef(run_id=run_id, thread_id=row["thread_id"])


@router.post("/jobs/{job_id}/skip", response_model=JobCard)
async def skip(job_id: str, body: SkipIn, user: dict = CurrentUser) -> JobCard:
    await db.execute("update jobs set status='skipped', action='skip', summary = summary || %s, updated_at=now()"
                     " where user_id=%s and job_id=%s", db.jsonb({"skip_reason": body.reason}), user["id"], job_id)
    row = await db.fetchone("select * from jobs where user_id=%s and job_id=%s", user["id"], job_id)
    if not row:
        raise HTTPException(404, "job not found")
    return card(row)


@router.post("/scout", response_model=dict)
async def scout_now(user: dict = CurrentUser) -> dict:
    from apps.api.dispatch import inline_mode
    from worker.tasks import scout_user

    res = await scout_user(user["id"], force=True, max_new=8)
    if not inline_mode():
        from arq import create_pool
        from arq.connections import RedisSettings
        import os

        pool = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
        for rid in res["queued"]:
            await pool.enqueue_job("run_job", rid, _job_id=rid)
        await pool.aclose()
    return res
