"""Critic: grounding, personalisation, opening, coverage, length. Sends the draft back at
most `writer.max_revisions` times (2), then lets it through with its notes attached."""
from __future__ import annotations

import json
import re

from agent import llm, settings
from agent.handoffs import Critique, CritiqueIssue
from agent.nodes._base import job_block, node
from agent.prompts import load_prompt

GENERIC = re.compile(r"^\s*(dear (sir|madam|hiring)|hello there|hi there|i am writing to|i came across|"
                     r"i'?m (very )?passionate|i am (very )?passionate|greetings)", re.I)


@node("critic")
async def critic(state: dict, config: dict) -> dict:
    draft = state["draft"]
    max_words = int(settings.get("writer.max_words", 260))
    words = len(draft["cover_letter"].split())
    report = state.get("claim_report") or {}
    no_evidence = (state.get("fit") or {}).get("missing", [])
    user = (f"{job_block(state['job'])}\n\nRequirements with NO portfolio evidence (the draft must NOT claim them; "
            f"never ask the writer to add them): {json.dumps(no_evidence)}\nRequirements: "
            f"{json.dumps([r.get('text') for r in (state.get('job_spec') or {}).get('requirements', [])])}\n"
            f"Cover letter ({words} words):\n{draft['cover_letter']}\n\nScreening answers: "
            f"{json.dumps(draft.get('screening_answers', []))}\n\nVerifier report: "
            f"{json.dumps([{k: c.get(k) for k in ('text', 'status')} for c in report.get('claims', [])])}")
    crit, _ = await llm.call("critic", load_prompt("critic", max_words=max_words), user, Critique, temperature=0)
    # Never push the writer to claim what the portfolio cannot prove.
    crit.issues = [i for i in crit.issues if not (i.kind in ("missing_requirement", "screening") and any(
        m.lower() in i.detail.lower() for m in no_evidence))]
    if crit.verdict == "revise" and not crit.issues:
        crit.verdict = "pass"
    # Deterministic checks the model must not talk its way out of.
    if GENERIC.search(draft["cover_letter"]) and not any(i.kind == "generic_opening" for i in crit.issues):
        crit.issues.append(CritiqueIssue(kind="generic_opening", detail="Opens with a generic greeting.", paragraph=1))
        crit.verdict = "revise"
    if words > max_words * 1.15 and not any(i.kind == "length" for i in crit.issues):
        crit.issues.append(CritiqueIssue(kind="length", detail=f"{words} words, limit {max_words}."))
        crit.verdict = "revise"
    if report.get("unsupported_after", 0) > 0:
        crit.issues.append(CritiqueIssue(kind="grounding", detail="Unsupported claims remain after verification."))
        crit.verdict = "revise"
    revisions = int(state.get("revisions", 0))
    crit.round = revisions
    out = {"critiques": [crit.model_dump()]}
    if crit.verdict == "revise" and revisions < int(settings.get("writer.max_revisions", 2)):
        out["revisions"] = revisions + 1
        out["status"] = "revising"
    return out


def route_after_critic(state: dict) -> str:
    if state.get("status") in ("needs_attention", "marketplace_down"):
        return "halt"
    last = (state.get("critiques") or [{}])[-1]
    if last.get("verdict") == "revise" and state.get("status") == "revising":
        return "writer"
    return "compliance"
