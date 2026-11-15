"""Shared plumbing for GigBid's MCP servers: identity (signed service token from the HTTP
Authorization header or the request _meta for in-process calls), trace ids, a per-user
rate limiter, the append-only audit log, and the bearer-token ASGI guard."""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from agent import settings
from agent.guardrails import mask_pii
from agent.security import verify_service_token

AUDIT_FILE = settings.ROOT / "cache" / "audit.jsonl"


class AuthError(PermissionError):
    pass


# In-process transport: the gateway sets these before opening memory-stream sessions; the
# server tasks inherit them (contextvars are copied when the server task group starts).
import contextvars  # noqa: E402

INPROC_AUTH: contextvars.ContextVar[str | None] = contextvars.ContextVar("inproc_auth", default=None)
INPROC_TRACE: contextvars.ContextVar[str | None] = contextvars.ContextVar("inproc_trace", default=None)


def _meta(ctx: Any) -> dict:
    try:
        meta = ctx.request_context.meta
    except Exception:  # noqa: BLE001 - no request context (direct call in tests)
        return {}
    if meta is None:
        return {}
    return meta.model_dump() if hasattr(meta, "model_dump") else dict(meta)


def _header(ctx: Any, name: str) -> str | None:
    try:
        req = ctx.request_context.request
    except Exception:  # noqa: BLE001
        return None
    if req is None:
        return None
    return req.headers.get(name)


def identity(ctx: Any, *, required: bool = True, default_persona: str | None = None) -> dict:
    token = _meta(ctx).get("auth")
    if not token:
        header = _header(ctx, "authorization") or ""
        token = header[7:] if header.lower().startswith("bearer ") else None
    if not token:
        token = INPROC_AUTH.get()
    if token:
        try:
            return verify_service_token(token)
        except Exception as exc:  # noqa: BLE001
            raise AuthError(f"invalid service token: {exc}") from exc
    if required:
        raise AuthError("missing service token")
    persona = default_persona or os.environ.get("PORTFOLIO_OWNER", "ai_ml")
    return {"sub": f"local:{persona}", "tenant": f"local:{persona}", "persona": persona, "scopes": ["read"]}


def trace_id(ctx: Any) -> str | None:
    return _meta(ctx).get("trace_id") or _header(ctx, "x-trace-id") or INPROC_TRACE.get()


class RateLimiter:
    """Sliding-window limiter per user, kept under the marketplace's own limit."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def wait_time(self, key: str) -> float:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) < self.per_minute:
                q.append(now)
                return 0.0
            return 60 - (now - q[0]) + 0.01


def audit(server: str, tool: str, user: str | None, args: dict, result: Any, trace: str | None,
          *, dry_run: bool = False, ok: bool = True) -> None:
    row = {"server": server, "tool": tool, "user_id": user, "args": mask_pii(args),
           "result": mask_pii(_shrink(result)), "trace_id": trace, "dry_run": dry_run, "ok": ok}
    if settings.database_url():
        from agent import db

        with db.connect() as conn:
            conn.execute(
                "insert into audit_log(user_id, server, tool, args, result, trace_id, dry_run, ok)"
                " values (%s,%s,%s,%s,%s,%s,%s,%s)",
                (user, server, tool, db.jsonb(row["args"]), db.jsonb(row["result"]), trace, dry_run, ok))
    else:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        row["ts"] = time.time()
        with open(AUDIT_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")


def _shrink(value: Any, limit: int = 2000) -> Any:
    text = json.dumps(value, default=str)
    if len(text) <= limit:
        return json.loads(text)
    return {"truncated": text[:limit]}


class BearerGuard:
    """ASGI middleware: rejects HTTP requests without a valid service token (401)."""

    def __init__(self, app, *, required: bool = True) -> None:
        self.app = app
        self.required = required

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.required:
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            auth = headers.get("authorization", "")
            ok = False
            if auth.lower().startswith("bearer "):
                try:
                    verify_service_token(auth[7:])
                    ok = True
                except Exception:  # noqa: BLE001
                    ok = False
            if not ok:
                body = b'{"error":"unauthorized"}'
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def tool_snapshot(server) -> list[dict]:
    """Stable description of every tool (name, schemas, annotations) for contract tests."""
    import asyncio

    tools = asyncio.run(server.list_tools())
    out = []
    for t in sorted(tools, key=lambda x: x.name):
        out.append({
            "name": t.name,
            "description": (t.description or "").strip(),
            "input_schema": t.inputSchema,
            "output_schema": t.outputSchema,
            "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else None,
        })
    return out


def data_path(*parts: str) -> Path:
    return settings.ROOT.joinpath(*parts)
