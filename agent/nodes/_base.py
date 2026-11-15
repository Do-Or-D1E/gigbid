"""Node wrapper shared by every graph node: step and token budgets, usage accounting,
progress events for the UI stream, degraded-mode handling and per-node timing."""
from __future__ import annotations

import functools
import json
import time
from typing import Any, Awaitable, Callable

from langgraph.config import get_stream_writer

from agent import llm, settings, tracing
from agent.mcp_client import MarketplaceDown, McpGateway

HALT = ("needs_attention", "marketplace_down", "blocked", "dead_letter")


def gateway(config: dict) -> McpGateway:
    return config["configurable"]["gateway"]


def emit(event: dict[str, Any]) -> None:
    try:
        get_stream_writer()(event)
    except Exception:  # noqa: BLE001 - outside a graph run (tests)
        pass


def _over_budget(state: dict) -> str | None:
    max_steps = int(settings.get("budgets.max_steps_per_thread", 40))
    max_tokens = int(settings.get("budgets.max_tokens_per_thread", 60000))
    if state.get("steps", 0) >= max_steps:
        return f"step budget exceeded ({state.get('steps')} >= {max_steps})"
    if state.get("tokens", 0) >= max_tokens:
        return f"token budget exceeded ({state.get('tokens')} >= {max_tokens})"
    return None


def node(name: str) -> Callable[[Callable[..., Awaitable[dict]]], Callable[..., Awaitable[dict]]]:
    def deco(fn: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
        @functools.wraps(fn)
        async def wrapped(state: dict, config: dict) -> dict:
            if state.get("status") in HALT:
                return {}
            reason = _over_budget(state)
            if reason:
                emit({"node": name, "event": "needs_attention", "reason": reason})
                return {"status": "needs_attention", "attention": reason}
            sink: list[llm.Usage] = []
            tok_u = llm.usage_sink.set(sink)
            tok_n = tracing.current_node.set(name)
            emit({"node": name, "event": "start"})
            t0 = time.perf_counter()
            try:
                out = await fn(state, config) or {}
            except MarketplaceDown:
                # Re-raise: the checkpoint keeps this node pending, so the run resumes here once
                # the marketplace is back (degraded mode: queue the work and recover).
                emit({"node": name, "event": "marketplace_down"})
                raise
            except llm.BudgetExceeded as exc:
                out = {"status": "needs_attention", "attention": f"Spend cap reached: {exc}"}
            finally:
                llm.usage_sink.reset(tok_u)
                tracing.current_node.reset(tok_n)
            s = llm.summarize(sink)
            elapsed = time.perf_counter() - t0
            out["steps"] = 1
            out["tokens"] = s["input_tokens"] + s["output_tokens"]
            out["cost_usd"] = s["billed_usd"]
            out["list_cost_usd"] = s["list_usd"]
            out["timings"] = {name: round(elapsed, 3)}
            emit({"node": name, "event": "end", "latency_s": round(elapsed, 2), "tokens": out["tokens"],
                  "summary": _summary(name, out)})
            return out
        wrapped.__gigbid_node__ = name  # type: ignore[attr-defined]
        return wrapped
    return deco


def _summary(name: str, out: dict) -> str:
    for key in ("decision", "risk", "fit", "price", "compliance", "job_spec"):
        if key in out and isinstance(out[key], dict):
            v = out[key]
            if key == "decision":
                return f"{v.get('action')}: {'; '.join(v.get('reasons', [])[:2])}"
            if key == "risk":
                return f"risk {v.get('risk_score')} scam={v.get('is_scam')}"
            if key == "fit":
                return f"fit {v.get('fit_score')} coverage {v.get('coverage')}"
            if key == "price":
                return f"{v.get('bid_type')} ${v.get('amount')} ({v.get('connects_cost')} Connects)"
            if key == "compliance":
                return f"compliance {v.get('verdict')}"
            if key == "job_spec":
                return f"{len(v.get('requirements', []))} requirements"
    if "critiques" in out and out["critiques"]:
        return f"critic {out['critiques'][-1].get('verdict')}"
    if out.get("status"):
        return str(out["status"])
    return ""


def job_block(job: dict) -> str:
    """Job post as delimited untrusted data plus trusted metadata."""
    from agent.guardrails import untrusted

    meta = {k: job.get(k) for k in ("job_id", "title", "category", "skills", "budget_type", "budget_min",
                                    "budget_max", "duration", "experience_level", "proposals_count")}
    questions = "\n".join(f"- {q}" for q in job.get("screening_questions") or [])
    body = f"Title: {job.get('title', '')}\n\n{job.get('description', '')}\n\nScreening questions:\n{questions}"
    return f"Listing metadata (from the marketplace API): {json.dumps(meta)}\n\n{untrusted('job_post', body)}"
