"""Skill tagging for chunk metadata. Uses only canonical names and aliases from the
taxonomy (exact mentions). Implied skills are deliberately NOT tagged here: finding those
is the retriever's job, and tagging them from the generator's phrase list would leak gold."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

TAXONOMY = Path(__file__).resolve().parents[2] / "data" / "taxonomy.json"


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, re.Pattern]]:
    if not TAXONOMY.exists():
        return []
    tax = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    pats = []
    for skill, info in tax.items():
        names = {skill, *info.get("aliases", [])}
        alts = "|".join(sorted((re.escape(n) for n in names if len(n) >= 2), key=len, reverse=True))
        if alts:
            pats.append((skill, re.compile(rf"(?<![\w.]){alts}(?![\w])", re.IGNORECASE)))
    return pats


def tag_skills(text: str) -> list[str]:
    found = [skill for skill, pat in _patterns() if pat.search(text)]
    return sorted(set(found))


def canonical(name: str) -> str:
    """Map a free-text skill to its canonical taxonomy name when possible."""
    for skill, pat in _patterns():
        if pat.fullmatch(name.strip()) or pat.search(name):
            return skill
    return name.strip()
