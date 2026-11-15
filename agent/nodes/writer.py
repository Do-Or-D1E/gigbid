"""Proposal Writer: cover letter and screening answers with evidence citations. Reads
promoted style rules and outcome insights from long-term memory (never raw history)."""
from __future__ import annotations

import json

from agent import llm, settings
from agent.handoffs import ProposalDraft
from agent.memory.store import outcome_insights, style_rules
from agent.nodes._base import job_block, node
from agent.prompts import load_prompt
from rag.verify import evidence_block


def evidence_for_writer(state: dict, limit: int = 8) -> list:
    from agent.handoffs import EvidenceItem

    fit = state.get("fit") or {}
    preferred = [i for m in fit.get("matches", []) for i in m.get("evidence_ids", [])]
    pool = {e["item_id"]: e for e in state.get("evidence", [])}
    ordered = list(dict.fromkeys([i for i in preferred if i in pool] +
                                 sorted(pool, key=lambda i: -pool[i].get("score", 0))))
    return [EvidenceItem(**{k: v for k, v in pool[i].items() if k in EvidenceItem.model_fields}) for i in ordered[:limit]]


@node("writer")
async def writer(state: dict, config: dict) -> dict:
    job, spec = state["job"], state.get("job_spec") or {}
    evidence = evidence_for_writer(state)
    user_id = state.get("user_id", "")
    rules = await style_rules(user_id)
    insights = await outcome_insights(user_id, spec.get("category", ""))
    critique = (state.get("critiques") or [])[-1] if state.get("critiques") else None
    parts = [
        job_block(job),
        "Requirements (from the analyst): " + json.dumps([r.get("text") for r in spec.get("requirements", [])]),
        "Fit matches: " + json.dumps([{k: m.get(k) for k in ("requirement", "strength", "evidence_ids")}
                                      for m in (state.get("fit") or {}).get("matches", [])]),
        "No evidence for (do not claim): " + json.dumps((state.get("fit") or {}).get("missing", [])),
        f"Price to mention if useful: {json.dumps({k: (state.get('price') or {}).get(k) for k in ('bid_type', 'amount')})}",
        "Style notes learned from the freelancer's edits: " + (json.dumps(rules) if rules else "none yet"),
        "What worked before in this category: " + (json.dumps(insights) if insights else "no data yet"),
        evidence_block(evidence),
    ]
    if critique and critique.get("verdict") == "revise":
        parts.append("Critique notes to fix: " + json.dumps(critique.get("issues", [])))
    max_words = int(settings.get("writer.max_words", 260))
    draft, _ = await llm.call("writer", load_prompt("writer", max_words=max_words), "\n\n".join(parts),
                              ProposalDraft, temperature=0.4)
    draft.job_id = job["job_id"]
    draft.version = int((state.get("draft") or {}).get("version", 0)) + 1
    known = {e.item_id for e in evidence}
    draft.cited_evidence_ids = [i for i in draft.cited_evidence_ids if i in known]
    return {"draft": draft.model_dump(), "status": "drafted"}


async def regenerate_paragraph(state: dict, index: int, instruction: str = "") -> str:
    """Proposal studio: rewrite one paragraph on request (the result is re-checked by Compliance)."""
    paragraphs = [p for p in (state.get("draft") or {}).get("cover_letter", "").split("\n\n") if p.strip()]
    evidence = evidence_for_writer(state)
    user = (f"Paragraph {index + 1} of {len(paragraphs)}:\n{paragraphs[index]}\n\nWhole proposal for context:\n"
            + "\n\n".join(paragraphs) + f"\n\nUser instruction: {instruction or 'make it stronger'}\n\n"
            + evidence_block(evidence))
    text, _ = await llm.call("writer", load_prompt("regenerate_paragraph"), user, temperature=0.5)
    return str(text).strip()
