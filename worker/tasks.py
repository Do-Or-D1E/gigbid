"""Background work: scheduled scouting, run execution, marketplace event polling and
recovery after a marketplace outage. Used by the Arq worker (docker compose) and by the
serverless tick endpoint (Vercel cron / GitHub Actions schedule)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from agent import db, runner, settings
from agent.mcp_client import MarketplaceDown, McpGateway
from agent.nodes.scout import dedupe_key, run_saved_search


async def scout_user(user_id: str, *, force: bool = False, max_new: int = 10) -> dict:
    """Run every due saved search for one user, dedupe and queue bid runs for new jobs."""
    profile = await runner.profile_for(user_id)
    live = settings.get("marketplace.mode") == "upwork_live"
    floor = int(settings.get("scheduling.live_scout_interval_minutes" if live else
                             "scheduling.gigsim_scout_interval_minutes"))
    searches = await db.fetch("select * from saved_searches where user_id=%s and enabled", user_id)
    now = datetime.now(timezone.utc)
    queued, dups = [], 0
    async with McpGateway(user_id, profile["persona_id"], trace_id=f"scout-{user_id}") as gw:
        for s in searches:
            interval = max(int(s["interval_minutes"]), floor)
            if not force and s["last_run_at"] and (now - s["last_run_at"]).total_seconds() < interval * 60:
                continue
            known = [r["data"] for r in await db.fetch(
                "select data from jobs where user_id=%s order by created_at desc limit 300", user_id)]
            new, dup = await run_saved_search(gw, s, known)
            dups += len(dup)
            for job in new[: max_new - len(queued)]:
                key = dedupe_key(job)
                exists = await db.fetchone("select 1 from jobs where user_id=%s and (job_id=%s or dedupe_key=%s)",
                                           user_id, job["job_id"], key)
                if exists:
                    dups += 1
                    continue
                await db.execute("insert into jobs(user_id, job_id, data, dedupe_key, status) values (%s,%s,%s,%s,'queued')"
                                 " on conflict do nothing", user_id, job["job_id"], db.jsonb(job), key)
                thread = f"bid:{user_id}:{job['job_id']}"
                queued.append(await runner.enqueue(user_id, "bid", thread, job_id=job["job_id"], payload={"job": job}))
            await db.execute("update saved_searches set last_run_at=now() where id=%s", s["id"])
    return {"queued": queued, "duplicates": dups}


async def poll_events(user_id: str) -> dict:
    """Pull marketplace events: move pipeline cards, start conversation runs, learn outcomes."""
    profile = await runner.profile_for(user_id)
    cur = await db.fetchone("select cursor from marketplace_cursor where user_id=%s", user_id)
    stage_of = {"proposal_viewed": "viewed", "client_message": "replied", "interview_requested": "interview",
                "hired": "hired", "lost": "lost"}
    started, moved = [], 0
    async with McpGateway(user_id, profile["persona_id"], trace_id=f"events-{user_id}") as gw:
        data = await gw.call("get_events", {"since": (cur or {}).get("cursor")})
        for ev in data.get("events", []):
            pid = ev.get("proposal_id")
            stage = stage_of.get(ev.get("type", ""))
            if pid and stage:
                await db.execute("update pipeline set stage=%s, data=data || %s, updated_at=now()"
                                 " where user_id=%s and proposal_id=%s",
                                 stage, db.jsonb({f"{stage}_at": ev.get("at") or ev.get("sim_time")}), user_id, pid)
                moved += 1
            if ev.get("type") in ("client_message", "interview_requested") and ev.get("thread_id"):
                thread = f"conv:{user_id}:{ev['thread_id']}:{ev.get('event_id') or ev.get('id')}"
                busy = await db.fetchone("select 1 from runs where thread_id like %s and status in"
                                         " ('queued','running','awaiting_approval')",
                                         f"conv:{user_id}:{ev['thread_id']}:%")
                if not busy:
                    started.append(await runner.enqueue(user_id, "conversation", thread, job_id=ev.get("job_id"),
                                                        payload={"thread_id": ev["thread_id"]}))
            if ev.get("type") in ("hired", "lost", "client_message") and pid:
                await _learn_outcome(user_id, pid)
        await db.execute("insert into marketplace_cursor(user_id, cursor, polled_at) values (%s,%s,now())"
                         " on conflict (user_id) do update set cursor=excluded.cursor, polled_at=now()",
                         user_id, data.get("next"))
    return {"moved": moved, "conversations": started}


async def _learn_outcome(user_id: str, proposal_id: str) -> None:
    from agent.memory.store import refresh_outcomes

    row = await db.fetchone("select data from pipeline where user_id=%s and proposal_id=%s", user_id, proposal_id)
    category = (row or {}).get("data", {}).get("category")
    if not category:
        return
    rows = await db.fetch("select stage, data from pipeline where user_id=%s and data->>'category'=%s",
                          user_id, category)
    await runner.graphs()
    outcome_rows = [{"outcome": {"viewed": None, "submitted": None}.get(r["stage"], r["stage"]),
                     "evidence_count": r["data"].get("evidence_count", 0), "words": r["data"].get("words", 0)}
                    for r in rows]
    await refresh_outcomes(user_id, category, outcome_rows, runner._graphs["store"])


async def recover() -> dict:
    """Re-queue runs parked while the marketplace was down, once it answers again."""
    parked = await db.fetch("select run_id, user_id from runs where status='waiting_marketplace' order by created_at")
    if not parked:
        return {"requeued": 0}
    user = parked[0]["user_id"]
    profile = await runner.profile_for(user)
    try:
        async with McpGateway(user, profile["persona_id"], trace_id="health") as gw:
            await gw.call("get_connects_balance", {}, retries=0)
    except MarketplaceDown:
        return {"requeued": 0, "marketplace": "down"}
    await db.execute("update runs set status='queued' where status='waiting_marketplace'")
    return {"requeued": len(parked)}


async def tick(budget_s: float = 240) -> dict:
    """One serverless worker step: scout due searches, poll events, recover, drain runs."""
    out: dict = {"scout": {}, "events": {}}
    users = await db.fetch("select distinct user_id from saved_searches where enabled")
    for u in users:
        try:
            out["scout"][u["user_id"]] = await scout_user(u["user_id"], max_new=3)
            out["events"][u["user_id"]] = await poll_events(u["user_id"])
        except MarketplaceDown as exc:
            out["marketplace"] = f"down: {exc}"[:200]
            break
    out["recover"] = await recover()
    out["runs"] = await runner.drain(max_runs=4, budget_s=budget_s)
    return json.loads(json.dumps(out, default=str))
