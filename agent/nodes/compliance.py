"""Compliance Guard: enforces the active policy pack. A deterministic pass (contact
details, guarantees, disallowed links, rule hints) runs first and cannot be overruled; the
model then handles what patterns cannot see (invented claims, off-platform intent). No MCP
access. It can block, with the reason shown in the UI."""
from __future__ import annotations

import json
import re

from agent import guardrails, llm, policy
from agent.handoffs import ComplianceVerdict, Violation
from agent.nodes._base import node
from agent.prompts import load_prompt


def scrub(text: str) -> tuple[str, list[Violation]]:
    """Remove contact details, guarantees and disallowed links deterministically."""
    found: list[Violation] = []
    for v in policy.check(text):
        if v["severity"] == "block" and "link" not in v["rule_id"]:
            found.append(Violation(rule_id=v["rule_id"], excerpt=v["excerpt"], action="blocked"))
            continue
        excerpt = v["excerpt"]
        target = excerpt.strip()
        if target and target in text:
            if "link" in v["rule_id"] or target.startswith("http") or target.startswith("www."):
                text = text.replace(target, "[link removed]")
            elif guardrails.guarantees(target):
                text = re.sub(re.escape(target), "aim for", text)
            else:
                text = text.replace(target, "[removed]")
            found.append(Violation(rule_id=v["rule_id"], excerpt=excerpt, action="removed"))
    text = re.sub(r"\s*\[(?:removed|link removed)\]", "", text)
    return text.strip(), found


async def check_text(text: str, context: str, claims: list[dict] | None = None) -> ComplianceVerdict:
    cleaned, det = scrub(text)
    rules = policy.rules_text()
    verified = ""
    if claims is not None:
        verified = ("\n\nClaim verifier results (claims already checked against the freelancer's portfolio; "
                    "'supported' means verified, so not fabricated):\n" +
                    "\n".join(f"- [{c.get('status')}] {c.get('text', '')[:160]}" for c in claims))
    user = f"<draft>\n{cleaned}\n</draft>\n\nContext: {context}{verified}\n\nActive policy rules:\n{rules}"
    verdict, _ = await llm.call("compliance", load_prompt("compliance"), user, ComplianceVerdict, temperature=0)
    if verdict.verdict == "fixed" and verdict.cleaned_cover_letter:
        cleaned2, det2 = scrub(verdict.cleaned_cover_letter)
        cleaned, det = cleaned2, det + det2
    verdict.violations = det + [v for v in verdict.violations if v.rule_id not in {d.rule_id for d in det}]
    if any(v.action == "blocked" for v in det):
        verdict.verdict = "block"
        verdict.reason = verdict.reason or "Policy violation that editing cannot fix"
    elif det and verdict.verdict == "pass":
        verdict.verdict = "fixed"
    if verdict.verdict != "block":
        verdict.cleaned_cover_letter = cleaned
    return verdict


@node("compliance")
async def compliance(state: dict, config: dict) -> dict:
    draft = dict(state["draft"])
    risk = state.get("risk") or {}
    context = json.dumps({"job_title": state["job"].get("title"), "risk_flags": [f.get("kind") for f in
                                                                                 risk.get("flags", [])]})
    verdict = await check_text(draft["cover_letter"], context, (state.get("claim_report") or {}).get("claims", []))
    answers = []
    for a in draft.get("screening_answers", []):
        cleaned, _ = scrub(a["answer"])
        answers.append({**a, "answer": cleaned})
    draft["screening_answers"] = answers
    if verdict.verdict == "block":
        return {"compliance": verdict.model_dump(), "status": "blocked",
                "attention": f"Compliance Guard blocked this draft: {verdict.reason}"}
    draft["cover_letter"] = verdict.cleaned_cover_letter or draft["cover_letter"]
    return {"compliance": verdict.model_dump(), "draft": draft, "status": "compliant"}
