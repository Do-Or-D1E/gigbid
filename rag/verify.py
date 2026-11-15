"""Claim verification (B3). After drafting, the proposal is split into atomic claims about
the freelancer, each checked against the evidence. Unsupported claims are removed or
rewritten before the Critic sees the draft, then the result is re-verified so the
unsupported-claim rate is reported both before and after.

Two layers: an LLM verifier labels claims, and a lexical guard overrides "supported" for
claims whose numbers do not appear in any evidence text (numbers are where models invent)."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agent import llm
from agent.handoffs import Claim, ClaimReport, EvidenceItem
from agent.prompts import load_prompt

PLAN = re.compile(r"^\s*(?:i|we)\s*(?:will|'ll|would|'d|can|could|plan|intend|am ready|am available|propose|"
                  r"suggest|aim|want|look forward|am happy|am keen|shall|'m ready|'m available|'m happy)\b|"
                  r"^\s*(?:my|our) (?:plan|approach|proposal|next step)", re.I)
_NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?\s?(?:%|x|k|ms|s|hours?|days?|weeks?|years?|\+)?", re.I)


class _Claims(BaseModel):
    claims: list[Claim] = Field(default_factory=list)


def evidence_block(evidence: list[EvidenceItem], limit: int = 700) -> str:
    rows = [f'<evidence id="{e.item_id}" type="{e.type}" title="{e.title}">\n{e.snippet[:limit]}\n</evidence>'
            for e in evidence]
    return "\n".join(rows)


def _numbers(text: str) -> set[str]:
    return {re.sub(r"\s+", "", m.group(0).lower().rstrip("+")) for m in _NUM.finditer(text)}


def lexical_guard(claims: list[Claim], evidence: list[EvidenceItem]) -> list[Claim]:
    corpus = " ".join(e.snippet for e in evidence).lower()
    corpus_nums = _numbers(corpus)
    known = {e.item_id for e in evidence}
    out = []
    for c in claims:
        if PLAN.search(c.text):
            continue  # a commitment about this job, not a claim about past experience
        c = c.model_copy()
        c.evidence_ids = [i for i in c.evidence_ids if i in known]
        nums = {n for n in _numbers(c.text) if not re.fullmatch(r"\d", n)}  # single digits are too noisy
        missing = {n for n in nums if n not in corpus_nums and n.rstrip("%xk") not in corpus}
        if c.status == "supported" and missing:
            c.status = "partly_supported"
            c.note = (c.note + f" | numbers not in evidence: {sorted(missing)}").strip(" |")
        if c.status != "unsupported" and not c.evidence_ids:
            c.status = "unsupported"
            c.note = (c.note + " | no valid evidence id").strip(" |")
        out.append(c)
    for i, c in enumerate(out):
        c.claim_id = f"c{i + 1}"
    return out


async def check_claims(text: str, evidence: list[EvidenceItem]) -> list[Claim]:
    user = f"<proposal>\n{text}\n</proposal>\n\n{evidence_block(evidence)}"
    out, _ = await llm.call("verifier", load_prompt("verifier"), user, _Claims, temperature=0)
    return lexical_guard(out.claims, evidence)


async def rewrite_unsupported(text: str, bad: list[Claim], evidence: list[EvidenceItem]) -> str:
    listing = "\n".join(f"- [{c.status}] {c.text} ({c.note})" for c in bad)
    user = (f"<cover_letter>\n{text}\n</cover_letter>\n\nClaims to fix:\n{listing}\n\n"
            f"{evidence_block(evidence, 400)}")
    out, _ = await llm.call("verifier", load_prompt("claim_rewriter"), user, temperature=0)
    revised = str(out).strip()
    revised = re.sub(r"^</?cover_letter>\s*|\s*</?cover_letter>$", "", revised).strip()
    return revised or text


_WORD = re.compile(r"[a-z0-9][a-z0-9+#.-]*", re.I)


def _content(s: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(s) if len(w) > 3}


def drop_sentences(text: str, bad: list[Claim], threshold: float = 0.5) -> str:
    """Deterministic last step: delete any sentence that still carries an unsupported claim."""
    paragraphs = text.split("\n\n")
    out = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para.strip())
        keep = []
        for s in sentences:
            words = _content(s)
            hit = any(words and len(words & _content(c.text)) / max(1, min(len(words), len(_content(c.text)))) >= threshold
                      for c in bad)
            if not hit:
                keep.append(s)
        if keep:
            out.append(" ".join(keep))
    return "\n\n".join(out).strip() or text


async def verify_and_fix(text: str, evidence: list[EvidenceItem]) -> tuple[str, ClaimReport]:
    claims = await check_claims(text, evidence)
    unsupported = [c for c in claims if c.status == "unsupported"]
    partly = [c for c in claims if c.status == "partly_supported"]
    report = ClaimReport(claims=claims, unsupported_before=len(unsupported))
    if not unsupported and not partly:
        report.unsupported_after = 0
        return text, report
    revised = await rewrite_unsupported(text, unsupported + partly, evidence)
    after = await check_claims(revised, evidence)
    still = [c for c in after if c.status == "unsupported"]
    if still:
        revised = drop_sentences(revised, still)
        after = await check_claims(revised, evidence)
    report.claims = after
    report.unsupported_after = len([c for c in after if c.status == "unsupported"])
    report.rewritten = True
    return revised, report
