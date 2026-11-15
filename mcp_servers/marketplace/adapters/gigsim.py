"""GigSim adapter: REST calls with timeouts, bounded retries with backoff, Retry-After on
429, and a clear MarketplaceUnavailable when the simulator stays down."""
from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from agent import settings
from mcp_servers.marketplace.adapters.base import MarketplaceRejected, MarketplaceUnavailable


class GigSimAdapter:
    name = "gigsim"

    def __init__(self, token: str, base_url: str | None = None) -> None:
        self.base = (base_url or settings.get("marketplace.gigsim_base_url")).rstrip("/")
        self.token = token
        self.timeout = float(settings.get("marketplace.timeout_s", 15))
        self.retries = int(settings.get("marketplace.retries", 3))
        self.backoff = float(settings.get("marketplace.backoff_s", 0.8))

    async def _req(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None,
                   idem: str | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"}
        if idem:
            headers["Idempotency-Key"] = idem
        params = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
        last: str = ""
        for attempt in range(self.retries + 1):
            try:
                if self.base == "inproc":  # serverless: GigSim is mounted in the same process
                    from gigsim.app import app as gigsim_app

                    client_cm = httpx.AsyncClient(transport=httpx.ASGITransport(app=gigsim_app),
                                                  base_url="http://gigsim", timeout=self.timeout)
                    url = f"/v1{path}"
                else:
                    client_cm = httpx.AsyncClient(timeout=self.timeout)
                    url = f"{self.base}/v1{path}"
                async with client_cm as client:
                    r = await client.request(method, url, params=params, json=json, headers=headers)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                if r.status_code < 300:
                    return r.json()
                if r.status_code == 429:
                    wait = float(r.headers.get("Retry-After", "1"))
                    last = "rate_limited"
                    await asyncio.sleep(min(wait, 10.0))
                    continue
                if r.status_code >= 500:
                    last = f"{r.status_code}: {r.text[:200]}"
                else:
                    try:
                        body = r.json()
                    except ValueError:
                        body = {"error": r.text[:300]}
                    raise MarketplaceRejected(r.status_code, body)
            if attempt < self.retries:
                await asyncio.sleep(self.backoff * (2 ** attempt) + random.random() * 0.2)
        raise MarketplaceUnavailable(f"GigSim unavailable after {self.retries + 1} attempts ({last})")

    async def search_jobs(self, query, category, skills, limit):
        data = await self._req("GET", "/jobs", params={"query": query, "category": category,
                                                       "skills": ",".join(skills or []) or None, "limit": limit})
        return data.get("jobs", data) if isinstance(data, dict) else data

    async def get_job(self, job_id):
        return await self._req("GET", f"/jobs/{job_id}")

    async def get_client_history(self, client_id):
        return await self._req("GET", f"/clients/{client_id}")

    async def get_connects_balance(self):
        return await self._req("GET", "/me/connects")

    async def quote_connects(self, job_id):
        q = await self._req("GET", "/connects/quote", params={"job_id": job_id})
        return {**q, "connects_cost": q.get("cost", q.get("connects_cost", 0))}

    async def get_pricing_stats(self, category, skills):
        return await self._req("GET", "/stats/pricing", params={"category": category,
                                                                "skills": ",".join(skills or []) or None})

    async def get_policy(self):
        return await self._req("GET", "/policy")

    async def list_threads(self):
        data = await self._req("GET", "/threads")
        rows = data.get("threads", data) if isinstance(data, dict) else data
        return [{**t, "last_message": {"text": t.get("last_message_preview", ""), "sender": t.get("last_sender")},
                 "updated_at": t.get("last_message_at")} for t in rows]

    async def list_messages(self, thread_id):
        data = await self._req("GET", f"/threads/{thread_id}/messages")
        return data.get("messages", data) if isinstance(data, dict) else data

    async def list_proposals(self, status):
        data = await self._req("GET", "/proposals", params={"status": status})
        return data.get("proposals", data) if isinstance(data, dict) else data

    async def get_events(self, since):
        data = await self._req("GET", "/events", params={"since": since})
        return {"events": data.get("events", []), "next": data.get("next_cursor", data.get("next"))}

    async def create_proposal_draft(self, payload, idempotency_key):
        return await self._req("POST", "/proposals", json=payload, idem=idempotency_key)

    async def submit_proposal(self, draft_id, idempotency_key):
        return await self._req("POST", f"/proposals/{draft_id}/submit", json={}, idem=idempotency_key)

    async def send_message(self, thread_id, text, idempotency_key):
        return await self._req("POST", f"/threads/{thread_id}/messages", json={"text": text}, idem=idempotency_key)
