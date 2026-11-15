"""Live Upwork adapter. Talks to the official Upwork MCP server
(https://mcp.upwork.com/mcp) through MultiServerMCPClient over Streamable HTTP, using the
user's OAuth 2.1 access token (stored encrypted, see apps/api/routers/oauth.py).

Upwork's tool names are mapped onto GigBid's port in upwork_tools.yaml, so neither this
server's tools nor the graph change between GigSim and live mode.

Platform respect, enforced here and not by convention:
* write tools only ever create DRAFTS; the user confirms them on Upwork itself;
* no browser automation, no session cookies, no scraping: only MCP tool calls;
* reads are rate limited by the caller and scheduled no more often than
  `scheduling.live_scout_interval_minutes`.
This adapter was not exercised end to end (no Upwork account was available); the tool map
must be confirmed with `uv run python scripts/upwork_discover.py` after connecting."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from agent import settings
from mcp_servers.marketplace.adapters.base import MarketplaceRejected, MarketplaceUnavailable

TOOL_MAP = yaml.safe_load((Path(__file__).with_name("upwork_tools.yaml")).read_text(encoding="utf-8"))


class UpworkLiveAdapter:
    name = "upwork_live"

    def __init__(self, access_token: str) -> None:
        self.url = settings.get("marketplace.upwork_mcp_url")
        self.token = access_token

    async def _call(self, port_name: str, args: dict[str, Any]) -> Any:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        spec = TOOL_MAP.get(port_name)
        if not spec:
            raise MarketplaceRejected(501, {"error": f"{port_name} is not available in live mode"})
        client = MultiServerMCPClient({"upwork": {
            "transport": "streamable_http", "url": self.url,
            "headers": {"Authorization": f"Bearer {self.token}"},
        }})
        mapped = {spec.get("args", {}).get(k, k): v for k, v in args.items() if v is not None}
        try:
            async with client.session("upwork") as session:
                result = await session.call_tool(spec["tool"], mapped)
        except Exception as exc:  # noqa: BLE001
            raise MarketplaceUnavailable(f"Upwork MCP error: {exc}") from exc
        if result.isError:
            raise MarketplaceRejected(400, {"error": str(result.content)[:500]})
        if result.structuredContent:
            return result.structuredContent
        text = "".join(getattr(c, "text", "") for c in result.content)
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text}

    async def search_jobs(self, query, category, skills, limit):
        out = await self._call("search_jobs", {"query": query, "category": category, "limit": limit})
        return out.get("jobs", out) if isinstance(out, dict) else out

    async def get_job(self, job_id):
        return await self._call("get_job", {"job_id": job_id})

    async def get_client_history(self, client_id):
        return await self._call("get_client_history", {"client_id": client_id})

    async def get_connects_balance(self):
        return await self._call("get_connects_balance", {})

    async def quote_connects(self, job_id):
        job = await self.get_job(job_id)
        return {"job_id": job_id, "connects_cost": job.get("connects_cost") or job.get("connectsRequired")}

    async def get_pricing_stats(self, category, skills):
        # Upwork exposes no market statistics; fall back to GigSim's historical statistics.
        from mcp_servers.marketplace.adapters.gigsim import GigSimAdapter

        return await GigSimAdapter("gs-ai_ml-dev").get_pricing_stats(category, skills)

    async def get_policy(self):
        return {"version": "upwork", "rules": "See Upwork Terms of Service and the GigBid policy pack."}

    async def list_threads(self):
        return await self._call("list_threads", {})

    async def list_messages(self, thread_id):
        return await self._call("list_messages", {"thread_id": thread_id})

    async def list_proposals(self, status):
        return await self._call("list_proposals", {"status": status})

    async def get_events(self, since):
        return {"events": [], "next": since}

    async def create_proposal_draft(self, payload, idempotency_key):
        return await self._call("create_proposal_draft", {**payload, "idempotency_key": idempotency_key})

    async def submit_proposal(self, draft_id, idempotency_key):
        # Live mode never submits on its own: the draft stays on Upwork for the user to confirm.
        return {"proposal_id": draft_id, "status": "awaiting_user_confirmation_on_upwork",
                "connects_spent": 0, "note": "Confirm this draft on Upwork to send it."}

    async def send_message(self, thread_id, text, idempotency_key):
        return await self._call("send_message", {"thread_id": thread_id, "text": text})
