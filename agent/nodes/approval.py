"""Human approval and submission for the bid graph.

prepare_approval  builds the approval payload: draft, evidence behind every claim, risk
                  report, price rationale and the marketplace dry_run preview.
human_approval    interrupt(): the graph stops here until the user approves, edits or
                  rejects in the web UI. Edits are diffed into style memory and sent back
                  through Compliance; rejections keep their reason for analytics.
submit            creates the draft and submits it with deterministic idempotency keys,
                  so a crash and retry can never submit twice or spend Connects twice."""
from __future__ import annotations

import difflib
import hashlib

from langgraph.types import interrupt

from agent.handoffs import ApprovalDecision
from agent.memory.store import record_edit
from agent.nodes._base import gateway, node


def _key(*parts: str) -> str:
    return "gb-" + hashlib.sha256(":".join(parts).encode()).hexdigest()[:24]


def claims_with_evidence(state: dict) -> list[dict]:
    pool = {e["item_id"]: e for e in state.get("evidence", [])}
    out = []
    for c in (state.get("claim_report") or {}).get("claims", []):
        out.append({**c, "evidence": [{"item_id": i, "title": pool.get(i, {}).get("title", ""),
                                       "snippet": pool.get(i, {}).get("snippet", "")[:400],
                                       "source": pool.get(i, {}).get("source", "")}
                                      for i in c.get("evidence_ids", [])]})
    return out


@node("prepare_approval")
async def prepare_approval(state: dict, config: dict) -> dict:
    gw = gateway(config)
    draft, price, job = state["draft"], state.get("price") or {}, state["job"]
    draft_prev = await gw.call("create_proposal_draft", {
        "job_id": job["job_id"], "cover_letter": draft["cover_letter"], "bid_amount": price.get("amount", 1),
        "bid_type": price.get("bid_type", "fixed"), "idempotency_key": _key(state.get("run_id", ""), "preview"),
        "screening_answers": draft.get("screening_answers", []), "dry_run": True})
    submit_prev = await gw.call("submit_proposal", {"draft_id": "pending-draft", "job_id": job["job_id"],
                                                    "idempotency_key": _key("preview", job["job_id"]),
                                                    "dry_run": True})
    preview = {
        "payload": (draft_prev.get("preview") or {}).get("payload"),
        "policy_warnings": (draft_prev.get("preview") or {}).get("policy_warnings", []),
        "connects_cost": (submit_prev.get("preview") or {}).get("connects_cost"),
        "connects_balance": (submit_prev.get("preview") or {}).get("connects_balance"),
        "balance_after": (submit_prev.get("preview") or {}).get("balance_after"),
    }
    return {"preview": preview, "status": "awaiting_approval"}


@node("human_approval")
async def human_approval(state: dict, config: dict) -> dict:
    payload = {
        "kind": "proposal",
        "job": {k: state["job"].get(k) for k in ("job_id", "title", "category", "budget_type", "budget_min",
                                                  "budget_max", "client_id")},
        "draft": state["draft"],
        "claims": claims_with_evidence(state),
        "claim_report": {k: (state.get("claim_report") or {}).get(k)
                         for k in ("unsupported_before", "unsupported_after", "rewritten",
                                   "unsupported_before_first_draft")},
        "risk": state.get("risk"),
        "fit": state.get("fit"),
        "price": state.get("price"),
        "critiques": state.get("critiques", []),
        "compliance": state.get("compliance"),
        "preview": state.get("preview"),
        "decision": state.get("decision"),
    }
    raw = interrupt(payload)
    decision = ApprovalDecision.model_validate(raw)
    out: dict = {"approval": decision.model_dump()}
    if decision.action == "reject":
        out["status"] = "rejected"
    elif decision.action == "edit":
        original = state["draft"]["cover_letter"]
        edited = decision.edited_cover_letter or original
        diff = list(difflib.unified_diff(original.splitlines(), edited.splitlines(), lineterm="", n=0))
        mem = await record_edit(state.get("user_id", ""), original, edited)
        draft = {**state["draft"], "cover_letter": edited, "version": state["draft"].get("version", 1) + 1}
        if decision.edited_answers:
            draft["screening_answers"] = [a.model_dump() for a in decision.edited_answers]
        out.update({"draft": draft, "status": "edited",
                    "edits": [{"diff": diff[:80], "features": mem["features"], "promoted": mem["promoted"]}]})
    else:
        out["status"] = "approved"
    return out


def route_after_approval(state: dict) -> str:
    status = state.get("status")
    if status == "approved":
        return "submit"
    if status == "edited":
        return "compliance"
    return "end"


@node("submit")
async def submit(state: dict, config: dict) -> dict:
    gw = gateway(config)
    draft, price, job = state["draft"], state.get("price") or {}, state["job"]
    thread = state.get("job_id", job["job_id"]) + ":" + state.get("user_id", "")
    content = hashlib.sha256(draft["cover_letter"].encode()).hexdigest()[:12]
    created = await gw.call("create_proposal_draft", {
        "job_id": job["job_id"], "cover_letter": draft["cover_letter"], "bid_amount": price.get("amount", 1),
        "bid_type": price.get("bid_type", "fixed"), "screening_answers": draft.get("screening_answers", []),
        "idempotency_key": _key(thread, "draft", content)})
    sent = await gw.call("submit_proposal", {"draft_id": created["draft_id"], "job_id": job["job_id"],
                                             "idempotency_key": _key(thread, "submit", created["draft_id"])})
    return {"submission": {"draft": created, "submit": sent}, "status": "submitted"}
