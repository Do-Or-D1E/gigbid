"""Analytics, health (degraded-mode banner), the serverless worker tick, and the Upwork
OAuth 2.1 connect flow."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from collections import Counter

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from agent import db, settings
from agent.mcp_client import MarketplaceDown, McpGateway
from apps.api.auth.users import CurrentUser, store_marketplace_token
from apps.api.schemas import AnalyticsOut, CategoryStat, HealthOut

router = APIRouter(prefix="/api", tags=["analytics"])


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return round(v[min(len(v) - 1, int(round(q * (len(v) - 1))))], 3)


@router.get("/analytics", response_model=AnalyticsOut)
async def analytics(user: dict = CurrentUser) -> AnalyticsOut:
    pipe = await db.fetch("select stage, data from pipeline where user_id=%s", user["id"])
    cats: dict[str, Counter] = {}
    connects = 0
    for p in pipe:
        c = cats.setdefault(p["data"].get("category") or "other", Counter())
        c["submitted"] += 1
        c["replied"] += p["stage"] in ("replied", "interview", "hired")
        c["hired"] += p["stage"] == "hired"
        connects += int(p["data"].get("connects") or 0)
    by_cat = [CategoryStat(category=k, submitted=v["submitted"], replied=v["replied"], hired=v["hired"],
                           reply_rate=round(v["replied"] / v["submitted"], 3) if v["submitted"] else 0.0,
                           hire_rate=round(v["hired"] / v["submitted"], 3) if v["submitted"] else 0.0)
              for k, v in sorted(cats.items())]
    replies = sum(c["replied"] for c in cats.values())
    runs = await db.fetch("select kind, status, metrics from runs where user_id=%s and status not in"
                          " ('queued','running','retry')", user["id"])
    analysed = [r for r in runs if r["kind"] == "bid"]
    proposals = [r for r in runs if r["kind"] == "bid" and r["status"] == "awaiting_approval"]
    lat_job = [r["metrics"].get("latency_s", 0) for r in analysed if r["metrics"]]
    lat_prop = [r["metrics"].get("latency_s", 0) for r in proposals if r["metrics"]]
    cost_job = [r["metrics"].get("list_usd", 0) for r in analysed if r["metrics"]]
    rejections = Counter((a["decision"] or {}).get("reason") or "no reason" for a in await db.fetch(
        "select decision from approvals where user_id=%s and status='rejected'", user["id"]))
    decisions = Counter(r["action"] or "pending" for r in await db.fetch("select action from jobs where user_id=%s",
                                                                          user["id"]))
    return AnalyticsOut(
        by_category=by_cat, connects_spent=connects, connects_per_reply=round(connects / replies, 2) if replies else None,
        jobs_analysed=len(analysed), proposals=len(proposals),
        latency={"p50_job_s": _pct(lat_job, 0.5), "p95_job_s": _pct(lat_job, 0.95),
                 "p50_proposal_s": _pct(lat_prop, 0.5), "p95_proposal_s": _pct(lat_prop, 0.95),
                 "declared_p95_job_s": settings.get("budgets.declared.p95_latency_s_per_job_analysed"),
                 "declared_p95_proposal_s": settings.get("budgets.declared.p95_latency_s_per_proposal")},
        cost={"mean_list_usd_per_job": round(sum(cost_job) / len(cost_job), 5) if cost_job else None,
              "billed_usd_total": round(sum(r["metrics"].get("billed_usd", 0) for r in runs if r["metrics"]), 5),
              "declared_usd_per_job": settings.get("budgets.declared.usd_per_job_analysed"),
              "declared_usd_per_proposal": settings.get("budgets.declared.usd_per_proposal")},
        rejection_reasons=[{"reason": k, "count": v} for k, v in rejections.most_common(8)],
        decisions=dict(decisions))


_health_cache: dict = {"t": 0.0, "value": None}


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    """Unauthenticated. The UI polls this to show the 'marketplace unavailable' banner."""
    db_ok, mk, detail = True, "unknown", ""
    try:
        await db.fetchone("select 1")
    except Exception as exc:  # noqa: BLE001
        db_ok, detail = False, f"db: {exc}"[:200]
    if time.monotonic() - _health_cache["t"] < 10 and _health_cache["value"]:
        mk, detail = _health_cache["value"]
    elif db_ok:
        try:
            async with McpGateway("health-probe", "ai_ml", trace_id="health", scopes=["read"]) as gw:
                await gw.call("get_policy", {}, retries=0, timeout=12)
            mk = "up"
        except MarketplaceDown as exc:
            mk, detail = "down", str(exc)[:200]
        except Exception as exc:  # noqa: BLE001
            mk, detail = "down", f"{type(exc).__name__}: {exc}"[:200]
        _health_cache.update(t=time.monotonic(), value=(mk, detail))
    return HealthOut(ok=db_ok and mk != "down", db=db_ok, marketplace=mk, marketplace_detail=detail,
                     model_profile=settings.config()["profile"], marketplace_mode=settings.get("marketplace.mode"),
                     policy_version=int(settings.get("policy.version", 1)), rag_variant=settings.get("rag.variant", ""))


@router.api_route("/worker/tick", methods=["GET", "POST"], include_in_schema=False)
async def tick(request: Request) -> JSONResponse:
    """Serverless worker step, called by Vercel Cron / the GitHub Actions schedule."""
    secret = os.environ.get("CRON_SECRET", "")
    auth = request.headers.get("authorization", "")
    if not secret or auth != f"Bearer {secret}":
        raise HTTPException(401, "bad cron secret")
    from worker.tasks import tick as do_tick

    return JSONResponse(await do_tick(budget_s=float(os.environ.get("TICK_BUDGET_S", "200"))))


# ----------------------------------------------------------------------------- Upwork OAuth 2.1
def _base_url(request: Request) -> str:
    return os.environ.get("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")


@router.get("/oauth/upwork/client.json", include_in_schema=False)
async def client_metadata(request: Request) -> JSONResponse:
    """OAuth client ID metadata document: Upwork's MCP auth server accepts this URL as client_id."""
    base = _base_url(request)
    return JSONResponse({"client_id": f"{base}/api/oauth/upwork/client.json", "client_name": "GigBid",
                         "redirect_uris": [f"{base}/api/oauth/upwork/callback"], "grant_types":
                         ["authorization_code", "refresh_token"], "response_types": ["code"],
                         "token_endpoint_auth_method": "none"})


@router.get("/oauth/upwork/start", response_model=dict)
async def upwork_start(request: Request, user: dict = CurrentUser) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        meta = (await c.get("https://mcp.upwork.com/.well-known/oauth-authorization-server")).json()
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    await db.execute("update user_settings set data = data || %s where user_id=%s",
                     db.jsonb({"oauth_pending": {"state": state, "verifier": verifier, "t": time.time()}}), user["id"])
    base = _base_url(request)
    params = httpx.QueryParams({"response_type": "code", "client_id": f"{base}/api/oauth/upwork/client.json",
                                "redirect_uri": f"{base}/api/oauth/upwork/callback", "code_challenge": challenge,
                                "code_challenge_method": "S256", "state": f"{user['id']}.{state}",
                                "resource": settings.get("marketplace.upwork_mcp_url")})
    return {"authorize_url": f"{meta['authorization_endpoint']}?{params}"}


@router.get("/oauth/upwork/callback", include_in_schema=False)
async def upwork_callback(request: Request, code: str, state: str) -> RedirectResponse:
    user_id, _, nonce = state.partition(".")
    row = await db.fetchone("select data from user_settings where user_id=%s", user_id)
    pending = ((row or {}).get("data") or {}).get("oauth_pending") or {}
    if pending.get("state") != nonce or time.time() - pending.get("t", 0) > 900:
        raise HTTPException(400, "OAuth state mismatch or expired")
    base = _base_url(request)
    async with httpx.AsyncClient(timeout=20) as c:
        meta = (await c.get("https://mcp.upwork.com/.well-known/oauth-authorization-server")).json()
        tok = await c.post(meta["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": f"{base}/api/oauth/upwork/callback",
            "client_id": f"{base}/api/oauth/upwork/client.json", "code_verifier": pending["verifier"]})
    if tok.status_code >= 300:
        raise HTTPException(400, "token exchange failed")
    tokens = tok.json()
    tokens["obtained_at"] = time.time()
    await store_marketplace_token(user_id, "upwork_live", "upwork", tokens)  # encrypted at rest, never logged
    await db.execute("update user_settings set data = data - 'oauth_pending' where user_id=%s", user_id)
    return RedirectResponse(f"{base}/settings?connected=upwork")

