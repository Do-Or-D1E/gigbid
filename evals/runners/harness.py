"""Evaluation harness: brings up a local stack in-process so every runner measures the real
system (same graphs, nodes, prompts and MCP servers), without a browser.

* embedded Postgres (pgserver) for GigSim, the audit log and the ledger, unless
  DATABASE_URL is already set;
* GigSim mounted in-process (GIGSIM_BASE_URL=inproc) with dev-set jobs and clients loaded;
* MCP servers in-process (MCP_TRANSPORT=inproc);
* graphs compiled with an in-memory checkpointer and store (evals never send anything:
  the bid graph is built without the approval/submit tail unless a runner submits to
  GigSim on purpose for the outcome metric).
LLM responses are cached on disk (GIGBID_LLM_CACHE=1) so a re-run costs nothing."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
DATASETS = ROOT / "evals" / "datasets"
PERSONAS = ["ai_ml", "fullstack", "data_analyst"]
ADMIN = os.environ.get("GIGSIM_ADMIN_TOKEN", "gigsim-admin-dev")


def setup_env(*, cache: bool = True, profile: str | None = None) -> None:
    os.environ.setdefault("APP_SECRET", "eval-secret-0123456789-abcdefghijklmnopqrstuv")
    os.environ["MCP_TRANSPORT"] = "inproc"
    os.environ["GIGSIM_BASE_URL"] = "inproc"
    os.environ.setdefault("GIGSIM_RATE_LIMIT_PER_MIN", "100000")
    os.environ.setdefault("GIGSIM_ERROR_RATE", "0")
    os.environ.setdefault("GIGSIM_CLIENT_MODE", "llm")
    if cache:
        os.environ["GIGBID_LLM_CACHE"] = "1"
    if profile:
        os.environ["GIGBID_PROFILE"] = profile
    if not os.environ.get("DATABASE_URL"):
        import pgserver

        srv = pgserver.get_server(str(ROOT / ".pgdata"), cleanup_mode=None)
        uri = srv.get_uri()
        os.environ["DATABASE_URL"] = uri
    os.environ.setdefault("GIGSIM_DATABASE_URL", os.environ["DATABASE_URL"])
    from agent import settings

    settings.reload()


def load_dev(persona: str, n: int | None = None, *, path: Path | None = None) -> list[dict]:
    p = path or DATASETS / f"dev_{persona}.jsonl"
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:n] if n else rows


def sample(rows: list[dict], n: int, seed: int = 4016, *, stratify: str = "action") -> list[dict]:
    """Deterministic stratified sample (keeps the bid/skip and job-type mix)."""
    import random

    rng = random.Random(seed)
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r["gold"].get(stratify)), []).append(r)
    out: list[dict] = []
    for key in sorted(groups):
        g = groups[key][:]
        rng.shuffle(g)
        out += g[: max(1, round(n * len(groups[key]) / len(rows)))]
    rng.shuffle(out)
    return out[:n]


class Stack:
    """Async context: GigSim lifespan + in-process MCP + compiled graphs."""

    def __init__(self, *, submit: bool = False) -> None:
        self.submit = submit
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "Stack":
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore

        from agent import db
        from agent.graphs import bid_graph, conversation_graph
        from agent.memory.store import set_fallback
        from gigsim.app import app as gigsim_app

        db.migrate()
        await self._stack.enter_async_context(gigsim_app.router.lifespan_context(gigsim_app))
        self.store = InMemoryStore()
        set_fallback(self.store)
        saver = InMemorySaver()
        self.bid = bid_graph.build(saver, self.store, interrupt=self.submit)
        self.conversation = conversation_graph.build(saver, self.store)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._stack.aclose()

    async def gigsim(self, method: str, path: str, *, token: str = ADMIN, **kw) -> Any:
        import httpx

        from gigsim.app import app as gigsim_app

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gigsim_app), base_url="http://gigsim",
                                     timeout=60) as c:
            r = await c.request(method, f"/v1{path}", headers={"Authorization": f"Bearer {token}"}, **kw)
            r.raise_for_status()
            return r.json()

    async def load_jobs(self, rows: list[dict]) -> None:
        clients = {c["client_id"]: c for c in json.loads((ROOT / "gigsim" / "seed" / "clients.json").read_text(
            encoding="utf-8"))}
        holdout_clients = ROOT / "evals" / "holdout" / "clients.json"
        if holdout_clients.exists():
            clients.update({c["client_id"]: c for c in json.loads(holdout_clients.read_text(encoding="utf-8"))})
        jobs = [r["job"] for r in rows]
        need = [clients[j["client_id"]] for j in jobs if j.get("client_id") in clients]
        for i in range(0, len(jobs), 100):
            await self.gigsim("POST", "/admin/load_jobs", json={"jobs": jobs[i:i + 100], "clients": need})

    async def run_bid(self, persona: str, job: dict, *, user: str | None = None, profile: dict | None = None,
                      until: str | None = None, thread: str | None = None) -> tuple[dict, dict]:
        """Run the bid graph for one job; returns (final_state, metrics)."""
        from agent import llm, tracing
        from agent.mcp_client import McpGateway
        from agent.runner import _brief  # noqa: F401

        user = user or f"eval-{persona}"
        prof = profile or json.loads((ROOT / "data" / "personas" / persona / "profile.json").read_text(encoding="utf-8"))
        usages: list[llm.Usage] = []
        spans: list[tracing.Span] = []
        tu, tt = llm.usage_sink.set(usages), tracing.current_trace.set(spans)
        t0 = time.perf_counter()
        err = None
        final: dict = {}
        try:
            async with McpGateway(user, persona, trace_id=f"eval-{job['job_id']}") as gw:
                cfg = {"configurable": {"thread_id": thread or f"eval:{persona}:{job['job_id']}:{time.time_ns()}",
                                        "gateway": gw}, "recursion_limit": 80,
                       "run_name": f"eval:{job['job_id']}", "tags": ["eval"]}
                inp = {"user_id": user, "persona": persona, "job_id": job["job_id"], "job": job,
                       "profile": {**prof, "persona_id": persona}, "run_id": cfg["configurable"]["thread_id"]}
                if until:
                    async for _ in self.bid.astream(inp, cfg, stream_mode="updates", interrupt_after=[until]):
                        pass
                else:
                    async for _ in self.bid.astream(inp, cfg, stream_mode="updates"):
                        pass
                final = (await self.bid.aget_state(cfg)).values
                self.last_config = cfg
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {str(exc)[:300]}"
        finally:
            llm.usage_sink.reset(tu)
            tracing.current_trace.reset(tt)
        m = {**llm.summarize(usages), "latency_s": round(time.perf_counter() - t0, 3), "error": err,
             "tool_calls": len([s for s in spans if s.kind == "tool"]),
             "models": sorted({u.model for u in usages if not u.error})}
        return final, m


def write_result(name: str, data: Any) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    if name.endswith(".jsonl"):
        path.write_text("".join(json.dumps(r, default=str) + "\n" for r in data), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    return path


def spend_report() -> dict:
    from agent import llm

    return {"billed_usd_total_ledger": round(llm.ledger().total(), 5)}


def run(coro) -> Any:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(coro)
