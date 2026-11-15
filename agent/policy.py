"""Policy pack access. The active version comes from config (`policy.version`), so the
2 Nov platform update is absorbed by a config change plus the new yaml, not code.

Rules carry `detection_hints` (regexes or phrases). `check()` runs the deterministic part
of the Compliance Guard; the LLM part handles what patterns cannot (overclaiming, tone)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from agent import guardrails, settings


def pack_dir() -> Path:
    return settings.ROOT / settings.get("policy.pack_dir", "data/policy_pack")


@lru_cache(maxsize=4)
def load(version: int | None = None) -> dict[str, Any]:
    version = version or int(settings.get("policy.version", 1))
    path = pack_dir() / f"policy_v{version}.yaml"
    if not path.exists():
        return {"version": version, "rules": [], "connects": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = data.get("rules", data if isinstance(data, list) else [])
    return {**(data if isinstance(data, dict) else {}), "version": version, "rules": rules}


def rules_text(version: int | None = None) -> str:
    pol = load(version)
    return "\n".join(f"- [{r.get('id')}] ({r.get('severity', 'fix')}) {r.get('title', '')}: {r.get('description', '')}"
                     for r in pol["rules"])


def _hint_patterns(rule: dict) -> list[re.Pattern]:
    pats = []
    for hint in rule.get("detection_hints", []) or []:
        try:
            pats.append(re.compile(hint, re.I))
        except re.error:
            pats.append(re.compile(re.escape(hint), re.I))
    return pats


def check(text: str, version: int | None = None) -> list[dict[str, str]]:
    """Deterministic violations: contact details, guarantees, disallowed links, rule hints."""
    found: list[dict[str, str]] = []
    pol = load(version)
    ids = {r.get("id") for r in pol["rules"]}

    def add(rule_id: str, excerpt: str, severity: str = "fix") -> None:
        found.append({"rule_id": rule_id, "excerpt": excerpt[:160], "severity": severity})

    for c in guardrails.contact_details(text):
        add(_pick(ids, ("no_contact_details", "contact_details", "no_off_platform")), c)
    for g in guardrails.guarantees(text):
        add(_pick(ids, ("no_guarantees", "guarantees")), g)
    link_rule = next((r for r in pol["rules"] if "link" in str(r.get("id", ""))), None)
    if link_rule:
        for u in guardrails.urls(text):
            if "github.com" not in u.lower():
                add(link_rule["id"], u, link_rule.get("severity", "block"))
    for rule in pol["rules"]:
        if rule.get("id") in {f["rule_id"] for f in found}:
            continue
        if "link" in str(rule.get("id", "")):
            continue
        for pat in _hint_patterns(rule):
            m = pat.search(text)
            if m:
                add(rule["id"], text[max(0, m.start() - 30): m.end() + 30], rule.get("severity", "fix"))
                break
    return found


def _pick(ids: set, candidates: tuple[str, ...]) -> str:
    for c in candidates:
        if c in ids:
            return c
    return candidates[0]
