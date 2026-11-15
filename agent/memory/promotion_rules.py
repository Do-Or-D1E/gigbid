"""Explicit promotion rules for long-term memory (R7).

Style memory: each user edit to a draft is reduced to coarse features (cut the first
sentence, removed a word, made it shorter, dropped exclamation marks, added a sign-off).
A feature is PROMOTED to a style rule only when it appears in at least `promote_after`
of the user's last `window` edits (config: 2 of 5). One-off edits never become rules.

Outcome memory: insights per job category are computed from final proposal outcomes in
the pipeline (replied/interview/hired vs lost) and the features of the proposals that
were sent. An insight is promoted only with at least `min_outcomes` outcomes in that
category. Raw tool output is never written to memory."""
from __future__ import annotations

import re
from collections import Counter

_WORD = re.compile(r"[A-Za-z][A-Za-z'-]{4,}")
_STOP = set("""about above after again against being below between could doing during further having
other ourselves should their theirs themselves there these those through under until where which while
would your yours yourself project projects client clients experience""".split())


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0].strip()


def edit_features(original: str, edited: str) -> list[str]:
    feats: list[str] = []
    o, e = original.strip(), edited.strip()
    if not o or not e or o == e:
        return feats
    first = _first_sentence(o)
    if first and first not in e and len(first.split()) >= 4:
        feats.append("cut_first_sentence")
    o_words = {w.lower() for w in _WORD.findall(o)}
    e_words = {w.lower() for w in _WORD.findall(e)}
    removed = sorted(w for w in o_words - e_words if w not in _STOP)
    feats += [f"ban:{w}" for w in removed[:12]]
    if len(e.split()) < 0.85 * len(o.split()):
        feats.append("shorter")
    if "!" in o and "!" not in e:
        feats.append("no_exclamations")
    o_last, e_last = o.splitlines()[-1].strip(), e.splitlines()[-1].strip()
    if e_last != o_last and len(e_last.split()) <= 6 and e_last not in o:
        feats.append(f"signoff:{e_last}")
    return feats


def rule_text(feature: str) -> str:
    if feature == "cut_first_sentence":
        return "Drop the opening pleasantry: start with the client's problem in the first sentence."
    if feature.startswith("ban:"):
        return f"Never use the word '{feature[4:]}'."
    if feature == "shorter":
        return "Keep proposals shorter than the default: about 20% fewer words."
    if feature == "no_exclamations":
        return "Do not use exclamation marks."
    if feature.startswith("signoff:"):
        return f"End with the sign-off '{feature[8:]}'."
    return feature


def promote_style(window_edits: list[list[str]], promote_after: int) -> dict[str, int]:
    """Features that meet the rule, with their support count."""
    counts = Counter(f for feats in window_edits for f in set(feats))
    return {f: n for f, n in counts.items() if n >= promote_after}


def outcome_insights(rows: list[dict], min_outcomes: int) -> list[str]:
    """rows: [{outcome: replied|interview|hired|lost, evidence_count, words, cut_opening}]"""
    done = [r for r in rows if r.get("outcome") in ("replied", "interview", "hired", "lost")]
    if len(done) < min_outcomes:
        return []
    def rate(group: list[dict]) -> tuple[int, int]:
        good = sum(1 for r in group if r["outcome"] != "lost")
        return good, len(group)
    insights = []
    g, n = rate(done)
    insights.append(f"{g} of {n} proposals in this category got a reply or better.")
    many = [r for r in done if r.get("evidence_count", 0) >= 2]
    few = [r for r in done if r.get("evidence_count", 0) < 2]
    if many and few:
        (g1, n1), (g2, n2) = rate(many), rate(few)
        insights.append(f"Citing 2+ portfolio items: {g1}/{n1} replied; fewer: {g2}/{n2}.")
    short = [r for r in done if r.get("words", 999) <= 180]
    long_ = [r for r in done if r.get("words", 0) > 180]
    if short and long_:
        (g1, n1), (g2, n2) = rate(short), rate(long_)
        insights.append(f"Proposals of 180 words or fewer: {g1}/{n1} replied; longer: {g2}/{n2}.")
    return insights
