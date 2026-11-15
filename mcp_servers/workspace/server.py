"""GigBid Workspace MCP server: free calendar slots, tentative interview holds and email
drafts. Backed by a local mock (allowed by the brief): a deterministic weekly busy
schedule per user plus holds and drafts stored in Postgres (or memory without a DB).
The agent only ever sees these MCP tools, so swapping in Google Calendar/Gmail later is
an adapter change.

    uv run python -m mcp_servers.workspace.server --port 8103
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from agent import settings
from mcp_servers import common

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)

mcp = FastMCP("gigbid-workspace", instructions="Calendar slots, tentative interview holds and email drafts.",
              stateless_http=True, json_response=True)

_mem_holds: dict[str, dict] = {}
_mem_drafts: dict[str, dict] = {}


class Slot(BaseModel):
    start: str
    end: str
    label: str


class SlotList(BaseModel):
    timezone: str
    slots: list[Slot]


class Hold(BaseModel):
    hold_id: str
    start: str
    end: str
    title: str
    status: str = "tentative"
    replay: bool = False


class EmailDraft(BaseModel):
    draft_id: str
    subject: str
    body: str
    status: str = "draft"
    replay: bool = False


def _busy(user: str, day: datetime) -> list[tuple[int, int]]:
    """Deterministic busy hours for a user on a day (mock calendar)."""
    seed = int(hashlib.sha256(f"{user}:{day.date()}".encode()).hexdigest()[:8], 16)
    blocks = [(9 + seed % 3, 10 + seed % 3), (13 + (seed >> 3) % 3, 14 + (seed >> 3) % 3)]
    return blocks


def _holds(user: str) -> list[dict]:
    if settings.database_url():
        from agent import db

        with db.connect() as conn:
            conn.execute("create table if not exists workspace_holds (hold_id text primary key, user_id text,"
                         " start_ts timestamptz, end_ts timestamptz, title text, idem text unique)")
            return list(conn.execute("select hold_id, start_ts, end_ts, title from workspace_holds where user_id=%s",
                                     (user,)).fetchall())
    return [h for h in _mem_holds.values() if h["user_id"] == user]


@mcp.tool(annotations=READ, title="Free calendar slots")
def free_slots(
    ctx: Context,
    days: Annotated[int, Field(ge=1, le=14, description="How many days ahead to look")] = 5,
    duration_minutes: Annotated[int, Field(ge=15, le=120)] = 30,
    max_slots: Annotated[int, Field(ge=1, le=10)] = 3,
    start_date: Annotated[str | None, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
) -> SlotList:
    """Free interview slots in working hours (09:00-17:00 UTC, weekdays), skipping busy blocks and holds."""
    who = common.identity(ctx)
    base = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc) if start_date else \
        datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    taken = [(h["start_ts"] if "start_ts" in h else datetime.fromisoformat(h["start"])) for h in _holds(who["sub"])]
    slots: list[Slot] = []
    for d in range(days):
        day = base + timedelta(days=d)
        if day.weekday() >= 5:
            continue
        busy = _busy(who["sub"], day)
        for hour in (10, 11, 14, 15, 16):
            if any(b0 <= hour < b1 for b0, b1 in busy):
                continue
            start = day.replace(hour=hour)
            if any(abs((t - start).total_seconds()) < 3600 for t in taken):
                continue
            end = start + timedelta(minutes=duration_minutes)
            slots.append(Slot(start=start.isoformat(), end=end.isoformat(),
                              label=start.strftime("%a %d %b, %H:%M UTC")))
            break  # at most one slot per day, spreads options across days
        if len(slots) >= max_slots:
            break
    common.audit("workspace", "free_slots", who["sub"], {"days": days}, {"n": len(slots)}, common.trace_id(ctx))
    return SlotList(timezone="UTC", slots=slots)


@mcp.tool(annotations=WRITE, title="Create interview hold")
def create_interview_hold(
    start: Annotated[str, Field(description="ISO start time from free_slots")],
    title: Annotated[str, Field(min_length=3, max_length=120)],
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128, pattern=r"^[\w\-:.]+$")],
    ctx: Context,
    duration_minutes: Annotated[int, Field(ge=15, le=120)] = 30,
) -> Hold:
    """Place a TENTATIVE calendar hold for an interview slot the user approved."""
    who = common.identity(ctx)
    try:
        s = datetime.fromisoformat(start)
    except ValueError as exc:
        raise ToolError(f"bad start time: {exc}") from exc
    e = s + timedelta(minutes=duration_minutes)
    hold_id = "hold-" + hashlib.sha256(f"{who['sub']}:{idempotency_key}".encode()).hexdigest()[:12]
    if settings.database_url():
        from agent import db

        with db.connect() as conn:
            _holds(who["sub"])
            row = conn.execute("select hold_id from workspace_holds where idem=%s", (idempotency_key,)).fetchone()
            if row:
                return Hold(hold_id=row["hold_id"], start=s.isoformat(), end=e.isoformat(), title=title, replay=True)
            conn.execute("insert into workspace_holds values (%s,%s,%s,%s,%s,%s)",
                         (hold_id, who["sub"], s, e, title, idempotency_key))
    else:
        if hold_id in _mem_holds:
            return Hold(**{**_mem_holds[hold_id]["out"], "replay": True})
        _mem_holds[hold_id] = {"user_id": who["sub"], "start": s.isoformat(),
                               "out": {"hold_id": hold_id, "start": s.isoformat(), "end": e.isoformat(), "title": title}}
    common.audit("workspace", "create_interview_hold", who["sub"], {"start": start, "title": title},
                 {"hold_id": hold_id}, common.trace_id(ctx))
    return Hold(hold_id=hold_id, start=s.isoformat(), end=e.isoformat(), title=title)


@mcp.tool(annotations=WRITE, title="Create email draft")
def create_email_draft(
    subject: Annotated[str, Field(min_length=3, max_length=150)],
    body: Annotated[str, Field(min_length=10, max_length=5000)],
    idempotency_key: Annotated[str, Field(min_length=8, max_length=128, pattern=r"^[\w\-:.]+$")],
    ctx: Context,
) -> EmailDraft:
    """Save an email DRAFT in the user's own mailbox (for example an interview reminder). Never sends."""
    who = common.identity(ctx)
    draft_id = "draft-" + hashlib.sha256(f"{who['sub']}:{idempotency_key}".encode()).hexdigest()[:12]
    if draft_id in _mem_drafts:
        return EmailDraft(**{**_mem_drafts[draft_id], "replay": True})
    _mem_drafts[draft_id] = {"draft_id": draft_id, "subject": subject, "body": body}
    common.audit("workspace", "create_email_draft", who["sub"], {"subject": subject}, {"draft_id": draft_id},
                 common.trace_id(ctx))
    return EmailDraft(draft_id=draft_id, subject=subject, body=body)


def http_app():
    return common.BearerGuard(mcp.streamable_http_app(), required=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="GigBid workspace MCP server")
    parser.add_argument("--port", type=int, default=8103)
    args = parser.parse_args()
    import uvicorn

    uvicorn.run(http_app(), host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
