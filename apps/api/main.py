"""GigBid API (FastAPI).

Local / docker compose: the API talks to separately running MCP servers, GigSim and an Arq
worker. Serverless (Vercel, INPROC_SERVICES=1): GigSim and the three MCP servers are
mounted in this same process (/gigsim, /mcp/portfolio, /mcp/marketplace, /mcp/workspace)
and the agent reaches them in-process; the MCP servers are still reachable over HTTP with
bearer auth for external clients."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from agent import db, settings, tracing
from agent.guardrails import mask_pii
from apps.api.routers import analytics, approvals, auth, jobs, messages, runs


class PiiFilter(logging.Filter):
    """Masks emails, phones, handles and card numbers in every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_pii(str(record.msg))
        if record.args:
            record.args = tuple(mask_pii(a) if isinstance(a, str) else a for a in record.args)
        return True


for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "httpx"):
    logging.getLogger(name).addFilter(PiiFilter())

if sys.platform == "win32":  # psycopg async needs the selector loop on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

INPROC = os.environ.get("INPROC_SERVICES") == "1"


async def seed_reviewer() -> None:
    email, password = os.environ.get("REVIEWER_EMAIL"), os.environ.get("REVIEWER_PASSWORD")
    if not email or not password:
        return
    from apps.api.auth.users import create_user, store_marketplace_token

    user = await db.fetchone("select * from users where email=%s", email.lower())
    if user:
        return
    user = await create_user(email, password, "Reviewer")
    persona = os.environ.get("REVIEWER_PERSONA", "ai_ml")
    await db.execute("update users set persona_id=%s where id=%s", persona, user["id"])
    await db.execute("update user_settings set data = data || %s where user_id=%s",
                     db.jsonb({"marketplace": "gigsim"}), user["id"])
    await store_marketplace_token(user["id"], "gigsim", persona, f"gs-{persona}-dev")
    await db.execute("insert into saved_searches(user_id, name, query, interval_minutes) values (%s,%s,%s,%s)",
                     user["id"], "All new jobs", "", 30)


_stack: AsyncExitStack | None = None
_started = False
_start_lock = None


async def ensure_started() -> None:
    """Idempotent startup. Runs from the lifespan, or from the first request on runtimes that
    do not send ASGI lifespan events (serverless)."""
    global _stack, _started, _start_lock
    import asyncio

    if _started:
        return
    _start_lock = _start_lock or asyncio.Lock()
    async with _start_lock:
        if _started:
            return
        _stack = AsyncExitStack()
        db.migrate()
        await seed_reviewer()
        if INPROC:
            from gigsim.app import app as gigsim_app
            from mcp_servers.marketplace.server import mcp as mk
            from mcp_servers.portfolio.server import mcp as pf
            from mcp_servers.workspace.server import mcp as ws

            await _stack.enter_async_context(gigsim_app.router.lifespan_context(gigsim_app))
            for server in (pf, mk, ws):
                await _stack.enter_async_context(server.session_manager.run())
        _started = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_started()
    try:
        yield
    finally:
        if _stack:
            await _stack.aclose()


app = FastAPI(title="GigBid API", version="0.1.0", lifespan=lifespan,
              description="Multi-agent freelancer copilot: jobs, approvals, runs, analytics.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Trace-Id"])


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    await ensure_started()
    trace = request.headers.get("x-trace-id") or uuid.uuid4().hex
    token = tracing.request_trace.set(trace)
    try:
        response = await call_next(request)
    finally:
        tracing.request_trace.reset(token)
    response.headers["X-Trace-Id"] = trace
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logging.getLogger("gigbid").exception("unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "internal error", "trace_id": tracing.request_trace.get()}, status_code=500)


for r in (auth.router, jobs.router, approvals.router, messages.router, runs.router, analytics.router):
    app.include_router(r)

if INPROC:
    from gigsim.app import app as _gigsim_app
    from mcp_servers.marketplace.server import http_app as _mk_http
    from mcp_servers.portfolio.server import http_app as _pf_http
    from mcp_servers.workspace.server import http_app as _ws_http

    app.mount("/gigsim", _gigsim_app)
    app.mount("/mcp/portfolio", _pf_http())
    app.mount("/mcp/marketplace", _mk_http())
    app.mount("/mcp/workspace", _ws_http())

# Serve the built web app (single-origin deployments). Unknown paths fall back to index.html.
WEB_DIST = Path(os.environ.get("WEB_DIST", settings.ROOT / "apps" / "web" / "dist"))
if WEB_DIST.exists():
    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        target = WEB_DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
