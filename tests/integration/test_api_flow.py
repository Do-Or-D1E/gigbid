"""Full-stack integration test through the HTTP API (GigSim and MCP mounted in-process):
register -> onboard -> scout -> analyse a bid-worthy job (SSE stream) -> approval pending ->
approve -> graph resumes -> proposal submitted exactly once (a second approve is refused and
GigSim shows one proposal). Needs an LLM key; skipped otherwise.

    GIGBID_PROFILE=paid uv run pytest tests/integration -q -s
"""
from __future__ import annotations

import json
import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.skipif(not (os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
                                     or os.path.exists(".env")), reason="needs an LLM key")


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


async def _stream(client, run_id: str, headers: dict) -> list[dict]:
    events = []
    async with client.stream("GET", f"/api/runs/{run_id}/stream", headers=headers, timeout=600) as r:
        async for line in r.aiter_lines():
            if line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if "kind" not in data and "status" in data:  # stream terminator: {"status": ...}
                    break
                events.append(data)
    return events


@pytest.mark.anyio
async def test_inbox_to_submitted_exactly_once():
    from evals.runners import harness as H

    H.setup_env(cache=True)
    os.environ.update(INPROC_SERVICES="1", MCP_TRANSPORT="inproc", GIGSIM_BASE_URL="inproc",
                      GIGSIM_CLIENT_MODE="heuristic")
    from agent import settings

    settings.reload()
    from apps.api import main

    rows = [r for r in H.load_dev("ai_ml") if r["gold"]["action"] == "bid" and "standard" in r["gold"]["job_type"]]
    job = rows[3]["job"]
    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120) as c:
            from gigsim.app import app as gs

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gs), base_url="http://g") as g:
                await g.post("/v1/admin/load_jobs", json={"jobs": [job], "clients": []},
                             headers={"Authorization": "Bearer gigsim-admin-dev"})
            email = f"it-{uuid.uuid4().hex[:6]}@example.com"
            tok = (await c.post("/api/auth/register", json={"email": email, "password": "password123",
                                                            "name": "IT"})).json()["token"]
            h = {"Authorization": f"Bearer {tok}"}
            r = await c.post("/api/onboarding", headers=h, json={
                "persona_id": "ai_ml", "marketplace": "gigsim", "hourly_rate_usd": 55, "min_project_usd": 500,
                "weekly_connects_budget": 80})
            assert r.status_code == 200 and r.json()["onboarded"]
            # Put the known job in the inbox the way the scout does, then analyse it.
            from agent import db

            await db.execute("insert into jobs(user_id, job_id, data, status) values (%s,%s,%s,'new')",
                             r.json()["id"], job["job_id"], db.jsonb(job))
            ref = (await c.post(f"/api/jobs/{job['job_id']}/analyze", headers=h)).json()
            events = await _stream(c, ref["run_id"], h)
            nodes = [e.get("node") for e in events if e.get("kind") == "start"]
            assert {"analyst", "risk_assessor", "fit_matcher"} <= set(nodes), nodes
            detail = (await c.get(f"/api/jobs/{job['job_id']}", headers=h)).json()
            assert detail["card"]["action"] in ("bid", "watch", "skip")
            if detail["card"]["action"] != "bid":
                pytest.skip(f"model chose {detail['card']['action']}; approval path not exercised")
            appr = (await c.get(f"/api/approvals/{ref['thread_id']}", headers=h)).json()
            assert appr["status"] == "pending" and appr["payload"]["preview"]["connects_cost"] > 0
            dec = (await c.post(f"/api/approvals/{ref['thread_id']}/decision", headers=h,
                                json={"action": "approve"})).json()
            again = await c.post(f"/api/approvals/{ref['thread_id']}/decision", headers=h, json={"action": "approve"})
            assert again.status_code == 409  # a second click cannot resume or submit twice
            await _stream(c, dec["run_id"], h)
            run = (await c.get(f"/api/runs/{dec['run_id']}", headers=h)).json()
            assert run["status"] == "submitted", run
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gs), base_url="http://g") as g:
                props = (await g.get("/v1/proposals", headers={"Authorization": "Bearer gs-ai_ml-dev"})).json()
            mine = [p for p in props.get("proposals", props) if p["job_id"] == job["job_id"] and p["status"] != "draft"]
            assert len(mine) == 1, mine
