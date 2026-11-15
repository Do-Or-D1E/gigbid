"""Execution trace, kept apart from graph state. Every LLM call and every MCP tool call of a
run is appended here (PII masked) and persisted to the `spans` table; LangSmith receives
the same run as a tree with tokens per node. State only carries totals for budgets."""
from __future__ import annotations

import contextvars
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from agent.guardrails import mask_pii


@dataclass
class Span:
    kind: str                 # llm | tool | node
    name: str
    node: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    list_usd: float = 0.0
    latency_s: float = 0.0
    args: Any = None
    result: Any = None
    error: str | None = None
    ts: float = field(default_factory=time.time)


current_trace: contextvars.ContextVar[list[Span] | None] = contextvars.ContextVar("current_trace", default=None)
# Trace id of the UI request that caused a run (X-Trace-Id), carried into the run, the graph
# metadata, every MCP call (_meta / header) and the audit log.
request_trace: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_trace", default=None)
current_node: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_node", default=None)


def add(span: Span) -> None:
    trace = current_trace.get()
    if trace is not None:
        span.args = mask_pii(span.args)
        span.result = mask_pii(span.result)
        trace.append(span)


def as_dicts(spans: list[Span]) -> list[dict]:
    return [asdict(s) for s in spans]


def persist(spans: list[Span], *, run_id: str, trace_id: str | None, user_id: str | None) -> None:
    from agent import db, settings

    if not settings.database_url() or not spans:
        return
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "insert into spans(trace_id, run_id, user_id, node, kind, name, model, input_tokens, output_tokens,"
                " usd, list_usd, latency_s, error) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [(trace_id, run_id, user_id, s.node, s.kind, s.name, s.model, s.input_tokens, s.output_tokens,
                  s.usd, s.list_usd, s.latency_s, s.error) for s in spans])
