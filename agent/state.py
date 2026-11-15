"""Typed graph state. Three things are kept apart:

* State (this file): what one job or conversation needs right now.
* Execution trace (agent/tracing.py): every tool name, argument, result and model call,
  persisted for audit and debugging, never fed back into state.
* Long-term memory (agent/memory/): only promoted knowledge, written to the LangGraph
  store by explicit rules.

Reducers sit on every key that the parallel branches (analyst, risk, fit) write."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_evidence(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    """Union of evidence items by id, keeping the best score."""
    out: dict[str, dict] = {e["item_id"]: e for e in (left or [])}
    for e in right or []:
        if e["item_id"] not in out or e.get("score", 0) > out[e["item_id"]].get("score", 0):
            out[e["item_id"]] = e
    return list(out.values())


def last_value(left: Any, right: Any) -> Any:
    return right if right is not None else left


class BidState(TypedDict, total=False):
    # who and what
    user_id: str
    persona: str
    job_id: str
    run_id: str
    profile: dict[str, Any]            # rates, floor, Connects budget, autonomy (snapshot at run start)
    job: dict[str, Any]                # raw job from the marketplace; description is untrusted
    client: dict[str, Any]
    injection_hits: list[str]
    # parallel analyses
    job_spec: dict[str, Any]           # JobSpec
    risk: dict[str, Any]               # RiskReport
    fit: dict[str, Any]                # FitReport
    evidence: Annotated[list[dict[str, Any]], merge_evidence]
    refused_requirements: list[str]
    # decision and price
    decision: dict[str, Any]           # BidDecision
    price: dict[str, Any]              # PriceQuote
    # drafting loop
    draft: dict[str, Any]              # ProposalDraft
    claim_report: dict[str, Any]       # ClaimReport (before/after)
    critiques: Annotated[list[dict[str, Any]], operator.add]
    revisions: int
    compliance: dict[str, Any]         # ComplianceVerdict
    preview: dict[str, Any]            # dry_run preview shown on the approval screen
    approval: dict[str, Any]           # ApprovalDecision
    edits: Annotated[list[dict[str, Any]], operator.add]
    submission: dict[str, Any]
    # control
    status: Annotated[str, last_value]
    attention: Annotated[str | None, last_value]
    steps: Annotated[int, operator.add]
    tokens: Annotated[int, operator.add]
    cost_usd: Annotated[float, operator.add]
    list_cost_usd: Annotated[float, operator.add]
    errors: Annotated[list[str], operator.add]
    timings: Annotated[dict[str, float], lambda a, b: {**(a or {}), **(b or {})}]


class ConversationState(TypedDict, total=False):
    user_id: str
    persona: str
    thread_id: str
    run_id: str
    profile: dict[str, Any]
    job_id: str | None
    messages: list[dict[str, Any]]
    last_client_message: dict[str, Any]
    injection_hits: list[str]
    intent: dict[str, Any]             # MessageIntent
    slots: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    reply: dict[str, Any]              # ReplyDraft
    compliance: dict[str, Any]
    preview: dict[str, Any]
    approval: dict[str, Any]
    edits: Annotated[list[dict[str, Any]], operator.add]
    sent: dict[str, Any]
    status: Annotated[str, last_value]
    attention: Annotated[str | None, last_value]
    steps: Annotated[int, operator.add]
    tokens: Annotated[int, operator.add]
    cost_usd: Annotated[float, operator.add]
    list_cost_usd: Annotated[float, operator.add]
    errors: Annotated[list[str], operator.add]
    timings: Annotated[dict[str, float], lambda a, b: {**(a or {}), **(b or {})}]
