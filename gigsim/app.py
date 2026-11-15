"""GigSim FastAPI application (all routes under /v1).

Run:  GIGSIM_DATABASE_URL=postgresql://... uv run uvicorn gigsim.app:app --port 8081
"""

from __future__ import annotations

import hashlib
import hmac
import json
import random
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import psycopg
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, clients_sim, policy, ratelimit, seed_loader
from . import clock as clk
from .config import Settings
from .models import AdminConfig, ClockAdvance, LoadJobs, MessageCreate, ProposalCreate
from .store import Store, load_kv, set_kv


class ApiError(Exception):
    def __init__(self, status: int, body: dict, headers: dict | None = None):
        self.status, self.body, self.headers = status, body, headers or {}


# ---------------------------------------------------------------------------------------------
# Per-request context and auth
# ---------------------------------------------------------------------------------------------


@dataclass
class AppState:
    settings: Settings
    store: Store
    extractor: clients_sim.FeatureExtractor
    taxonomy: dict


@dataclass
class Principal:
    admin: bool
    account_id: str | None
    token: str


class Ctx:
    def __init__(self, state: AppState, conn: psycopg.Connection):
        self.state, self.settings, self.conn = state, state.settings, conn
        kv = load_kv(conn)
        self.clock_state = kv.get("clock") or clk.new_clock_state(self.settings.time_scale)
        cfg = kv.get("config") or {}
        self.error_rate = float(cfg.get("error_rate", self.settings.error_rate))
        self.rate_limit = int(cfg.get("rate_limit_per_min", self.settings.rate_limit_per_min))
        self.policy_version = policy.normalize_version(cfg.get("policy_version", self.settings.policy_version))
        self.now_us = clk.sim_now_us(self.clock_state)


def get_ctx(request: Request):
    state: AppState = request.app.state.gs
    conn = state.store.connect()
    try:
        yield Ctx(state, conn)
    finally:
        conn.close()


def _authenticate(request: Request, ctx: Ctx) -> Principal:
    m = re.match(r"^Bearer\s+(\S+)\s*$", request.headers.get("authorization", ""), re.I)
    if not m:
        raise ApiError(401, {"error": "unauthorized"}, {"WWW-Authenticate": "Bearer"})
    token = m.group(1)
    if hmac.compare_digest(token.encode(), ctx.settings.admin_token.encode()):
        return Principal(True, None, token)
    row = ctx.conn.execute("SELECT account_id FROM accounts WHERE token = %s", (token,)).fetchone()
    if row is None:
        raise ApiError(401, {"error": "unauthorized"}, {"WWW-Authenticate": "Bearer"})
    retry = ratelimit.check(ctx.conn, token, ctx.rate_limit)
    if retry is not None:
        raise ApiError(429, {"error": "rate_limited", "retry_after": retry}, {"Retry-After": str(retry)})
    _maybe_inject_error(ctx)
    return Principal(False, row["account_id"], token)


def _maybe_inject_error(ctx: Ctx) -> None:
    rate = ctx.error_rate
    if rate <= 0:
        return
    if rate < 1:
        n = ctx.conn.execute(
            "UPDATE counters SET n = n + 1 WHERE name = 'error_counter' RETURNING n"
        ).fetchone()["n"]
        if random.Random(f"{ctx.settings.error_seed}:{n}").random() >= rate:
            return
    raise ApiError(503, {"error": "upstream_unavailable"})


def any_auth(request: Request, ctx: Ctx = Depends(get_ctx)) -> Principal:
    return _authenticate(request, ctx)


def account_auth(request: Request, ctx: Ctx = Depends(get_ctx)) -> Principal:
    p = _authenticate(request, ctx)
    if p.admin:
        raise ApiError(403, {"error": "forbidden", "detail": "this endpoint needs a freelancer account token"})
    return p


def admin_auth(request: Request, ctx: Ctx = Depends(get_ctx)) -> Principal:
    p = _authenticate(request, ctx)
    if not p.admin:
        raise ApiError(403, {"error": "forbidden", "detail": "admin token required"})
    return p


# ---------------------------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------------------------


def run_idempotent(ctx: Ctx, request: Request, account_id: str, payload: Any, fn) -> JSONResponse:
    key = (request.headers.get("idempotency-key") or "").strip()
    if not key:
        raise ApiError(400, {"error": "missing_idempotency_key", "detail": "Idempotency-Key header is required"})
    if len(key) > 255:
        raise ApiError(400, {"error": "invalid_idempotency_key"})
    req_hash = hashlib.sha256(
        json.dumps({"path": request.url.path, "body": payload}, sort_keys=True, default=str).encode()
    ).hexdigest()
    conn = ctx.conn
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"idem:{account_id}:{key}",))
        row = conn.execute(
            "SELECT request_hash, status, body FROM idempotency WHERE account_id = %s AND key = %s",
            (account_id, key),
        ).fetchone()
        if row:
            if row["request_hash"] != req_hash:
                raise ApiError(409, {"error": "idempotency_conflict"})
            return JSONResponse(row["body"], status_code=row["status"], headers={"Idempotent-Replay": "true"})
        status, body = fn()
        conn.execute(
            "INSERT INTO idempotency (account_id, key, request_hash, status, body, created_us) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (account_id, key, req_hash, status, Jsonb(body), ctx.now_us),
        )
    return JSONResponse(body, status_code=status)


# ---------------------------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------------------------


def get_visible_job(ctx: Ctx, job_id: str) -> dict | None:
    row = ctx.conn.execute(
        "SELECT data FROM jobs WHERE job_id = %s AND (release_us IS NULL OR release_us <= %s)",
        (job_id, ctx.now_us),
    ).fetchone()
    return row["data"] if row else None


def get_client(conn, client_id: str | None) -> dict | None:
    if not client_id:
        return None
    row = conn.execute("SELECT data FROM clients WHERE client_id = %s", (client_id,)).fetchone()
    return row["data"] if row else None


def connects_state(ctx: Ctx, account_id: str) -> dict:
    acct = ctx.conn.execute(
        "SELECT weekly_allowance FROM accounts WHERE account_id = %s", (account_id,)
    ).fetchone()
    allowance = acct["weekly_allowance"]
    ws = clk.week_start_us(ctx.now_us)
    rows = ctx.conn.execute(
        "SELECT proposal_id, job_id, amount, at_us FROM connects_ledger "
        "WHERE account_id = %s AND at_us >= %s AND at_us <= %s AND kind = 'spend' ORDER BY id",
        (account_id, ws, ctx.now_us),
    ).fetchall()
    spent_total = sum(r["amount"] for r in rows)
    return {
        "balance": allowance - spent_total,
        "weekly_allowance": allowance,
        "week_start": clk.iso(ws),
        "next_reset": clk.iso(ws + clk.US_PER_WEEK),
        "spent": [
            {"proposal_id": r["proposal_id"], "job_id": r["job_id"], "amount": r["amount"], "at": clk.iso(r["at_us"])}
            for r in rows
        ],
    }


PROPOSAL_SELECT = """
SELECT p.*,
  CASE WHEN p.status = 'draft' THEN 'draft' ELSE COALESCE(
    (SELECT e.status_to FROM events e WHERE e.proposal_id = p.proposal_id AND e.status_to IS NOT NULL
       AND e.deliver_us <= %(now)s ORDER BY e.status_rank DESC, e.event_id DESC LIMIT 1), 'submitted') END AS eff_status,
  (SELECT t.thread_id FROM threads t WHERE t.proposal_id = p.proposal_id AND EXISTS (
     SELECT 1 FROM messages m WHERE m.thread_id = t.thread_id AND m.sender = 'client'
       AND m.created_us <= %(now)s)) AS visible_thread
FROM proposals p
"""


def proposal_out(r: dict) -> dict:
    return {
        "proposal_id": r["proposal_id"],
        "job_id": r["job_id"],
        "client_id": r["client_id"],
        "status": r["eff_status"],
        "cover_letter": r["cover_letter"],
        "screening_answers": r["screening_answers"],
        "bid_amount": r["bid_amount"],
        "bid_type": r["bid_type"],
        "connects_spent": r["connects_spent"],
        "created_at": clk.iso(r["created_us"]),
        "submitted_at": clk.iso(r["submitted_us"]),
        "thread_id": r["visible_thread"],
    }


def fetch_proposal(ctx: Ctx, account_id: str, proposal_id: str) -> dict | None:
    r = ctx.conn.execute(
        PROPOSAL_SELECT + " WHERE p.proposal_id = %(pid)s AND p.account_id = %(acct)s",
        {"now": ctx.now_us, "pid": proposal_id, "acct": account_id},
    ).fetchone()
    return proposal_out(r) if r else None


@lru_cache(maxsize=32)
def _first_name(data_dir: str, account_id: str) -> str:
    p = Path(data_dir) / "personas" / account_id / "profile.json"
    try:
        name = json.loads(p.read_text(encoding="utf-8")).get("name", "")
        return name.split()[0] if name.strip() else "there"
    except (OSError, ValueError, IndexError):
        return "there"


def err(status: int, error: str, **extra) -> ApiError:
    return ApiError(status, {"error": error, **extra})


# ---------------------------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------------------------


def create_app(settings: Settings | None = None, llm_client: object | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = settings or Settings.from_env()
        store = Store(s)
        store.init()
        taxonomy = clients_sim.load_taxonomy(s.data_dir)
        client = llm_client
        mode = s.client_mode
        if mode == "llm" and client is None:
            if s.llm_api_key:
                from openai import OpenAI

                client = OpenAI(api_key=s.llm_api_key, base_url=s.llm_base_url)
            else:
                mode = "heuristic"
        extractor = clients_sim.FeatureExtractor(mode, s.llm_model, taxonomy, client)
        app.state.gs = AppState(s, store, extractor, taxonomy)
        yield

    app = FastAPI(title="GigSim", version=__version__, lifespan=lifespan)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(exc.body, status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        detail = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse({"error": "validation_error", "detail": detail}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse({"error": code, "detail": exc.detail}, status_code=exc.status_code)

    # ---- health / meta ---------------------------------------------------------------------

    @app.get("/v1/health")
    def health(request: Request):
        try:
            state: AppState = request.app.state.gs
            with state.store.connect() as conn:
                conn.execute("SELECT 1")
        except Exception:
            return JSONResponse({"status": "db_unavailable"}, status_code=503)
        return {"status": "ok", "version": __version__}

    @app.get("/v1/clock")
    def get_clock(ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth)):
        return {"sim_time": clk.iso(ctx.now_us), "sim_epoch": clk.iso(clk.EPOCH_US),
                "time_scale": ctx.clock_state["scale"], "week_start": clk.iso(clk.week_start_us(ctx.now_us))}

    @app.get("/v1/me")
    def me(ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        row = ctx.conn.execute("SELECT account_id, name FROM accounts WHERE account_id = %s", (p.account_id,)).fetchone()
        return {"account_id": row["account_id"], "name": row["name"]}

    @app.get("/v1/policy")
    def get_policy(ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth)):
        return {**policy.describe(ctx.policy_version, ctx.settings.data_dir), "active": True}

    # ---- jobs ------------------------------------------------------------------------------

    @app.get("/v1/jobs")
    def list_jobs(
        query: str | None = None, category: str | None = None, skills: str | None = None,
        posted_after: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
        ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth),
    ):
        where = ["(release_us IS NULL OR release_us <= %s)"]
        params: list[Any] = [ctx.now_us]
        if category:
            where.append("lower(category) = lower(%s)")
            params.append(category)
        if skills:
            wanted = [s.strip().lower() for s in skills.split(",") if s.strip()]
            if wanted:
                where.append("skills_lc && %s::text[]")
                params.append(wanted)
        if posted_after:
            ts = clk.parse_iso(posted_after)
            if ts is None:
                raise err(422, "validation_error", detail="posted_after must be an ISO 8601 timestamp")
            where.append("posted_us > %s")
            params.append(ts)
        score_sql, score_params = "0", []
        tokens = [t for t in re.findall(r"[a-z0-9+#.]+", (query or "").lower()) if len(t) >= 2 and t not in
                  ("the", "and", "for", "with", "to", "of", "in", "a", "an")]
        if tokens:
            parts = []
            for t in dict.fromkeys(tokens):
                parts.append("(CASE WHEN search_text ~ %s THEN 1 ELSE 0 END)")
                score_params.append(r"(^|[^a-z0-9])" + re.escape(t.strip(".")) + r"s?([^a-z0-9]|$)")
            score_sql = " + ".join(parts)
        sql = (
            f"SELECT data, posted_us, job_id, score, count(*) OVER() AS total FROM ("
            f"SELECT data, posted_us, job_id, ({score_sql}) AS score FROM jobs WHERE {' AND '.join(where)}) s "
            f"{'WHERE score > 0' if tokens else ''} "
            f"ORDER BY score DESC, posted_us DESC NULLS LAST, job_id LIMIT %s OFFSET %s"
        )
        rows = ctx.conn.execute(sql, [*score_params, *params, limit, offset]).fetchall()
        total = rows[0]["total"] if rows else 0
        if not rows and offset:
            # offset beyond the end: report the real total
            cnt_sql = (f"SELECT count(*) AS c FROM (SELECT ({score_sql}) AS score FROM jobs WHERE "
                       f"{' AND '.join(where)}) s {'WHERE score > 0' if tokens else ''}")
            total = ctx.conn.execute(cnt_sql, [*score_params, *params]).fetchone()["c"]
        return {"jobs": [seed_loader.public_job(r["data"]) for r in rows], "total": total,
                "limit": limit, "offset": offset}

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth)):
        job = get_visible_job(ctx, job_id)
        if job is None:
            raise err(404, "job_not_found", job_id=job_id)
        return seed_loader.public_job(job)

    # ---- clients ---------------------------------------------------------------------------

    @app.get("/v1/clients/{client_id}")
    def get_client_route(client_id: str, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth)):
        c = get_client(ctx.conn, client_id)
        if c is None:
            raise err(404, "client_not_found", client_id=client_id)
        out = {k: v for k, v in c.items() if k != "hidden"}
        jobs_posted = out.get("jobs_posted") or 0
        out["hire_rate"] = round((out.get("hires") or 0) / jobs_posted, 3) if jobs_posted else None
        rows = ctx.conn.execute(
            """SELECT data FROM (
                 SELECT data, posted_us FROM jobs WHERE client_id = %(c)s AND (release_us IS NULL OR release_us <= %(now)s)
                 UNION ALL SELECT data, posted_us FROM historical_jobs WHERE client_id = %(c)s) u
               ORDER BY posted_us DESC NULLS LAST LIMIT 5""",
            {"c": client_id, "now": ctx.now_us},
        ).fetchall()
        out["recent_jobs"] = [
            {k: r["data"].get(k) for k in ("job_id", "title", "category", "budget_type", "budget_min",
                                           "budget_max", "posted_at", "proposals_count")}
            for r in rows
        ]
        return out

    # ---- connects / pricing ----------------------------------------------------------------

    @app.get("/v1/me/connects")
    def my_connects(ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        return connects_state(ctx, p.account_id)

    @app.get("/v1/connects/quote")
    def quote(job_id: str, ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        job = get_visible_job(ctx, job_id)
        if job is None:
            raise err(404, "job_not_found", job_id=job_id)
        q = policy.connects_cost(job, ctx.policy_version)
        bal = connects_state(ctx, p.account_id)["balance"]
        return {"job_id": job_id, "policy_version": ctx.policy_version, "cost": q["cost"], "base_cost": q["base"],
                "surcharge": q["surcharge"], "reasons": q["reasons"], "balance": bal,
                "affordable": bal >= q["cost"]}

    @app.get("/v1/stats/pricing")
    def pricing_stats(category: str | None = None, skills: str | None = None,
                      ctx: Ctx = Depends(get_ctx), _: Principal = Depends(any_auth)):
        where, params = ["price IS NOT NULL"], []
        if category:
            where.append("lower(category) = lower(%s)")
            params.append(category)
        wanted = [s.strip().lower() for s in (skills or "").split(",") if s.strip()]
        if wanted:
            where.append("skills_lc && %s::text[]")
            params.append(wanted)
        out: dict[str, Any] = {"category": category, "skills": wanted}
        for btype in ("fixed", "hourly"):
            r = ctx.conn.execute(
                "SELECT count(*) AS count, percentile_cont(0.25) WITHIN GROUP (ORDER BY price) AS p25, "
                "percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS p50, "
                "percentile_cont(0.75) WITHIN GROUP (ORDER BY price) AS p75, avg(price) AS mean "
                f"FROM historical_jobs WHERE budget_type = %s AND {' AND '.join(where)}",
                [btype, *params],
            ).fetchone()
            out[btype] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}
        return out

    # ---- proposals -------------------------------------------------------------------------

    @app.post("/v1/proposals")
    def create_proposal(body: ProposalCreate, request: Request, ctx: Ctx = Depends(get_ctx),
                        p: Principal = Depends(account_auth)):
        def work():
            job = get_visible_job(ctx, body.job_id)
            if job is None:
                raise err(404, "job_not_found", job_id=body.job_id)
            bad = policy.find_disallowed_links([body.cover_letter, *body.screening_answers], ctx.policy_version)
            if bad:
                raise ApiError(422, {"error": "policy_violation", "rule": "link_restriction"})
            n = ctx.conn.execute("SELECT nextval('proposal_seq') AS n").fetchone()["n"]
            pid = f"prop_{n:06d}"
            ctx.conn.execute(
                "INSERT INTO proposals (proposal_id, account_id, job_id, client_id, cover_letter, screening_answers, "
                "bid_amount, bid_type, status, created_us) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s)",
                (pid, p.account_id, body.job_id, job.get("client_id"), body.cover_letter,
                 Jsonb(body.screening_answers), body.bid_amount, body.bid_type, ctx.now_us),
            )
            return 201, fetch_proposal(ctx, p.account_id, pid)

        return run_idempotent(ctx, request, p.account_id, body.model_dump(), work)

    @app.post("/v1/proposals/{proposal_id}/submit")
    def submit_proposal(proposal_id: str, request: Request, ctx: Ctx = Depends(get_ctx),
                        p: Principal = Depends(account_auth)):
        def work():
            conn = ctx.conn
            conn.execute("SELECT 1 FROM accounts WHERE account_id = %s FOR UPDATE", (p.account_id,))
            prop = conn.execute(
                "SELECT * FROM proposals WHERE proposal_id = %s AND account_id = %s FOR UPDATE",
                (proposal_id, p.account_id),
            ).fetchone()
            if prop is None:
                raise err(404, "proposal_not_found", proposal_id=proposal_id)
            if prop["status"] != "draft":
                raise err(409, "already_submitted", proposal_id=proposal_id)
            job = get_visible_job(ctx, prop["job_id"])
            if job is None:
                raise err(404, "job_not_found", job_id=prop["job_id"])
            dup = conn.execute(
                "SELECT proposal_id FROM proposals WHERE account_id = %s AND job_id = %s AND status = 'submitted'",
                (p.account_id, prop["job_id"]),
            ).fetchone()
            if dup:
                raise err(409, "already_submitted", job_id=prop["job_id"], proposal_id=dup["proposal_id"])
            if policy.find_disallowed_links([prop["cover_letter"], *prop["screening_answers"]], ctx.policy_version):
                raise ApiError(422, {"error": "policy_violation", "rule": "link_restriction"})
            quote_ = policy.connects_cost(job, ctx.policy_version)
            balance = connects_state(ctx, p.account_id)["balance"]
            if balance < quote_["cost"]:
                raise err(402, "insufficient_connects", required=quote_["cost"], balance=balance)
            conn.execute(
                "INSERT INTO connects_ledger (account_id, proposal_id, job_id, amount, at_us, kind) "
                "VALUES (%s,%s,%s,%s,%s,'spend')",
                (p.account_id, proposal_id, prop["job_id"], quote_["cost"], ctx.now_us),
            )
            client = get_client(conn, prop["client_id"]) or {"client_id": prop["client_id"] or "unknown", "hidden": {}}
            proposal = {"cover_letter": prop["cover_letter"], "screening_answers": prop["screening_answers"],
                        "bid_amount": prop["bid_amount"], "bid_type": prop["bid_type"]}
            features = ctx.state.extractor.extract(conn, proposal_id, proposal, job, client, ctx.now_us)
            plan = clients_sim.build_plan(
                proposal_id, proposal, job, client, features,
                _first_name(str(ctx.settings.data_dir), p.account_id), ctx.state.extractor.mode,
            )
            clients_sim.persist_plan(conn, plan, account_id=p.account_id, proposal_id=proposal_id,
                                     job_id=prop["job_id"], client_id=prop["client_id"], now_us=ctx.now_us)
            conn.execute(
                "UPDATE proposals SET status = 'submitted', submitted_us = %s, connects_spent = %s, "
                "policy_version = %s, decision = %s WHERE proposal_id = %s",
                (ctx.now_us, quote_["cost"], ctx.policy_version, Jsonb(plan["decision"]), proposal_id),
            )
            return 200, fetch_proposal(ctx, p.account_id, proposal_id)

        return run_idempotent(ctx, request, p.account_id, None, work)

    @app.get("/v1/proposals")
    def list_proposals(status: str | None = None, ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        rows = ctx.conn.execute(
            PROPOSAL_SELECT + " WHERE p.account_id = %(acct)s ORDER BY p.created_us DESC, p.proposal_id DESC",
            {"now": ctx.now_us, "acct": p.account_id},
        ).fetchall()
        items = [proposal_out(r) for r in rows]
        if status:
            items = [i for i in items if i["status"] == status]
        return {"proposals": items, "count": len(items)}

    @app.get("/v1/proposals/{proposal_id}")
    def get_proposal(proposal_id: str, ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        out = fetch_proposal(ctx, p.account_id, proposal_id)
        if out is None:
            raise err(404, "proposal_not_found", proposal_id=proposal_id)
        return out

    # ---- events ----------------------------------------------------------------------------

    @app.get("/v1/events")
    def get_events(since: str | None = None, limit: int = Query(100, ge=1, le=500),
                   ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        cond, params = "", []
        if since:
            m = re.fullmatch(r"(\d+)\.(\d+)", since)
            if m:
                cond, params = "AND (deliver_us, event_id) > (%s, %s)", [int(m.group(1)), int(m.group(2))]
            elif since.isdigit():
                eid = int(since)
                ref = ctx.conn.execute(
                    "SELECT deliver_us FROM events WHERE event_id = %s AND account_id = %s", (eid, p.account_id)
                ).fetchone()
                if ref:
                    cond, params = "AND (deliver_us, event_id) > (%s, %s)", [ref["deliver_us"], eid]
                else:
                    cond, params = "AND event_id > %s", [eid]
            else:
                raise err(422, "validation_error", detail="since must be a cursor from next_cursor or an event_id")
        rows = ctx.conn.execute(
            "SELECT event_id, type, proposal_id, thread_id, job_id, deliver_us, payload FROM events "
            f"WHERE account_id = %s AND deliver_us <= %s {cond} ORDER BY deliver_us, event_id LIMIT %s",
            [p.account_id, ctx.now_us, *params, limit],
        ).fetchall()
        events = [{"event_id": r["event_id"], "type": r["type"], "proposal_id": r["proposal_id"],
                   "thread_id": r["thread_id"], "job_id": r["job_id"], "at": clk.iso(r["deliver_us"]),
                   "payload": r["payload"]} for r in rows]
        next_cursor = f"{rows[-1]['deliver_us']}.{rows[-1]['event_id']}" if rows else (since or "0.0")
        return {"events": events, "next_cursor": next_cursor}

    # ---- threads / messages ----------------------------------------------------------------

    def message_out(r: dict) -> dict:
        out = {"message_id": r["message_id"], "thread_id": r["thread_id"], "sender": r["sender"],
               "text": r["text"], "created_at": clk.iso(r["created_us"])}
        if r["sender"] == "client":
            out["intent"] = r["intent"]
            if (r["meta"] or {}).get("signals"):
                out["signals"] = r["meta"]["signals"]
        else:
            out["proposed_times"] = (r["meta"] or {}).get("proposed_times", [])
        return out

    def visible_thread(ctx: Ctx, account_id: str, thread_id: str) -> dict:
        t = ctx.conn.execute(
            "SELECT * FROM threads WHERE thread_id = %s AND account_id = %s AND EXISTS ("
            "SELECT 1 FROM messages m WHERE m.thread_id = threads.thread_id AND m.sender = 'client' "
            "AND m.created_us <= %s)", (thread_id, account_id, ctx.now_us),
        ).fetchone()
        if t is None:
            raise err(404, "thread_not_found", thread_id=thread_id)
        return t

    @app.get("/v1/threads")
    def list_threads(ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        rows = ctx.conn.execute(
            """SELECT t.thread_id, t.proposal_id, t.job_id, t.client_id, t.state,
                 (SELECT data->>'name' FROM clients c WHERE c.client_id = t.client_id) AS client_name,
                 (SELECT data->>'title' FROM jobs j WHERE j.job_id = t.job_id) AS job_title,
                 lm.sender AS last_sender, lm.text AS last_text, lm.created_us AS last_us, lm.n AS message_count
               FROM threads t JOIN LATERAL (
                 SELECT m.sender, m.text, m.created_us, count(*) OVER() AS n FROM messages m
                 WHERE m.thread_id = t.thread_id AND m.created_us <= %s ORDER BY m.created_us DESC, m.message_id DESC
                 LIMIT 1) lm ON true
               WHERE t.account_id = %s AND EXISTS (SELECT 1 FROM messages m WHERE m.thread_id = t.thread_id
                 AND m.sender = 'client' AND m.created_us <= %s)
               ORDER BY lm.created_us DESC, t.thread_id""",
            (ctx.now_us, p.account_id, ctx.now_us),
        ).fetchall()
        return {"threads": [{
            "thread_id": r["thread_id"], "proposal_id": r["proposal_id"], "job_id": r["job_id"],
            "job_title": r["job_title"], "client_id": r["client_id"], "client_name": r["client_name"],
            "last_message_at": clk.iso(r["last_us"]), "last_sender": r["last_sender"],
            "last_message_preview": r["last_text"][:140], "message_count": r["message_count"],
        } for r in rows]}

    @app.get("/v1/threads/{thread_id}/messages")
    def thread_messages(thread_id: str, ctx: Ctx = Depends(get_ctx), p: Principal = Depends(account_auth)):
        visible_thread(ctx, p.account_id, thread_id)
        rows = ctx.conn.execute(
            "SELECT * FROM messages WHERE thread_id = %s AND created_us <= %s ORDER BY created_us, message_id",
            (thread_id, ctx.now_us),
        ).fetchall()
        return {"thread_id": thread_id, "messages": [message_out(r) for r in rows]}

    @app.post("/v1/threads/{thread_id}/messages")
    def post_message(thread_id: str, body: MessageCreate, request: Request, ctx: Ctx = Depends(get_ctx),
                     p: Principal = Depends(account_auth)):
        def work():
            conn = ctx.conn
            visible_thread(ctx, p.account_id, thread_id)
            t = conn.execute("SELECT * FROM threads WHERE thread_id = %s FOR UPDATE", (thread_id,)).fetchone()
            times = clients_sim.extract_times(body.text)
            mid = clients_sim.insert_message(conn, thread_id, "freelancer", body.text, None, ctx.now_us,
                                             {"proposed_times": times})
            clients_sim.on_freelancer_message(conn, t, body.text, ctx.now_us)
            row = conn.execute("SELECT * FROM messages WHERE message_id = %s", (mid,)).fetchone()
            return 201, message_out(row)

        return run_idempotent(ctx, request, p.account_id, body.model_dump(), work)

    # ---- admin -----------------------------------------------------------------------------

    @app.post("/v1/admin/reset")
    def admin_reset(ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        ctx.state.store.reset(ctx.conn)
        return {"status": "reset"}

    @app.post("/v1/admin/load_jobs")
    def admin_load_jobs(body: LoadJobs, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        for i, j in enumerate(body.jobs):
            if not isinstance(j.get("job_id"), str) or not j.get("job_id") or not isinstance(j.get("title"), str):
                raise err(422, "validation_error", detail=f"jobs[{i}] needs string job_id and title")
        for i, c in enumerate(body.clients):
            if not isinstance(c.get("client_id"), str) or not c.get("client_id"):
                raise err(422, "validation_error", detail=f"clients[{i}] needs a string client_id")
        with ctx.conn.transaction():
            for c in body.clients:
                seed_loader.upsert_client(ctx.conn, c)
            for j in body.jobs:
                seed_loader.upsert_job(ctx.conn, j, "admin", None)
        return {"jobs_loaded": len(body.jobs), "clients_loaded": len(body.clients)}

    @app.post("/v1/admin/clock/advance")
    def admin_advance(body: ClockAdvance, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        with ctx.conn.transaction():
            row = ctx.conn.execute("SELECT value FROM kv WHERE key = 'clock' FOR UPDATE").fetchone()
            state = row["value"] if row else clk.new_clock_state(ctx.settings.time_scale)
            now = time.time()
            state = {**state, "base_us": clk.sim_now_us(state, now) + clk.hours_to_us(body.hours),
                     "start_real": now, "advanced_hours": state.get("advanced_hours", 0.0) + body.hours}
            set_kv(ctx.conn, "clock", state)
        return {"sim_time": clk.iso(clk.sim_now_us(state)), "advanced_hours_total": state["advanced_hours"]}

    @app.post("/v1/admin/config")
    def admin_config(body: AdminConfig, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        update = body.model_dump(exclude_none=True)
        if "policy_version" in update:
            try:
                update["policy_version"] = policy.normalize_version(update["policy_version"])
            except ValueError as exc:
                raise err(422, "validation_error", detail=str(exc))
        with ctx.conn.transaction():
            row = ctx.conn.execute("SELECT value FROM kv WHERE key = 'config' FOR UPDATE").fetchone()
            cfg = {**(row["value"] if row else {}), **update}
            set_kv(ctx.conn, "config", cfg)
        return {
            "error_rate": float(cfg.get("error_rate", ctx.settings.error_rate)),
            "rate_limit_per_min": int(cfg.get("rate_limit_per_min", ctx.settings.rate_limit_per_min)),
            "policy_version": cfg.get("policy_version", policy.normalize_version(ctx.settings.policy_version)),
        }

    @app.get("/v1/admin/llm_usage")
    def admin_llm_usage(ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        tot = ctx.conn.execute(
            "SELECT count(*) AS calls, coalesce(sum(prompt_tokens),0)::bigint AS prompt_tokens, "
            "coalesce(sum(completion_tokens),0)::bigint AS completion_tokens, "
            "coalesce(sum(cost_usd),0) AS total_cost_usd FROM llm_usage"
        ).fetchone()
        hits = ctx.conn.execute("SELECT n FROM counters WHERE name = 'llm_cache_hits'").fetchone()
        rows = ctx.conn.execute(
            "SELECT id, at_us, model, proposal_id, prompt_tokens, completion_tokens, cost_usd "
            "FROM llm_usage ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return {
            "mode": ctx.state.extractor.mode, "model": ctx.settings.llm_model,
            "pricing_usd_per_1m_tokens": {"input": clients_sim.PRICES_PER_M.get(ctx.settings.llm_model, clients_sim.DEFAULT_PRICE)[0],
                                          "output": clients_sim.PRICES_PER_M.get(ctx.settings.llm_model, clients_sim.DEFAULT_PRICE)[1]},
            **tot, "cache_hits": hits["n"] if hits else 0,
            "recent": [{"id": r["id"], "at": clk.iso(r["at_us"]), "model": r["model"], "proposal_id": r["proposal_id"],
                        "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
                        "cost_usd": r["cost_usd"]} for r in rows],
        }

    @app.get("/v1/admin/proposals/{proposal_id}/decision")
    def admin_decision(proposal_id: str, ctx: Ctx = Depends(get_ctx), _: Principal = Depends(admin_auth)):
        row = ctx.conn.execute(
            "SELECT proposal_id, account_id, job_id, client_id, decision FROM proposals WHERE proposal_id = %s",
            (proposal_id,),
        ).fetchone()
        if row is None or row["decision"] is None:
            raise err(404, "decision_not_found", proposal_id=proposal_id)
        return {k: row[k] for k in ("proposal_id", "account_id", "job_id", "client_id")} | {"decision": row["decision"]}

    return app


app = create_app()
