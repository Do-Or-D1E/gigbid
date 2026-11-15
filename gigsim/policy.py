"""Marketplace policy: Connects pricing and proposal rules (v1, v2)."""

from __future__ import annotations

import math
import re
from pathlib import Path

import yaml

WEEKLY_ALLOWANCE = 80
POLICY_EFFECTIVE = {"1": "2026-01-01", "2": "2026-11-02"}

RULES_TEXT = {
    "1": [
        "Submitting a proposal costs Connects: fixed-price jobs cost 2 (budget < $100), 4 (< $500), "
        "6 (< $1000) or 8 (>= $1000) Connects; hourly jobs cost 6.",
        f"Every freelancer account receives {WEEKLY_ALLOWANCE} Connects per week.",
        "Drafts are free; Connects are spent when a proposal is submitted.",
    ],
    "2": [
        "Platform policy update effective 2026-11-02 (adds to all v1 rules).",
        "Submitting a proposal costs Connects: fixed-price jobs cost 2 (budget < $100), 4 (< $500), "
        "6 (< $1000) or 8 (>= $1000) Connects; hourly jobs cost 6.",
        "High-competition surcharge: jobs that already have 15 or more proposals cost 50% more "
        "Connects, rounded up.",
        "Link restriction: proposals (cover letter and screening answers) may not contain any URL "
        "other than github.com links. Violating proposals are rejected with HTTP 422 "
        "(rule link_restriction) and no Connects are spent.",
        f"Every freelancer account receives {WEEKLY_ALLOWANCE} Connects per week.",
    ],
}


def normalize_version(v) -> str:
    s = str(v).strip().lower().lstrip("v")
    if s not in ("1", "2"):
        raise ValueError(f"unknown policy version {v!r} (expected 1 or 2)")
    return s


def base_cost(job: dict) -> int:
    if str(job.get("budget_type", "fixed")).lower() == "hourly":
        return 6
    budget = job.get("budget_max")
    if budget is None:
        budget = job.get("budget_min") or 0
    budget = float(budget)
    if budget < 100:
        return 2
    if budget < 500:
        return 4
    if budget < 1000:
        return 6
    return 8


def connects_cost(job: dict, version: str) -> dict:
    """Return {"cost", "base", "surcharge", "reasons"} for a job under a policy version."""
    version = normalize_version(version)
    base = base_cost(job)
    cost = base
    reasons = [f"base cost for {job.get('budget_type', 'fixed')} job: {base}"]
    if version == "2" and int(job.get("proposals_count") or 0) >= 15:
        cost = math.ceil(base * 1.5)
        reasons.append(f"v2 high-competition surcharge (proposals_count >= 15): {base} x 1.5 rounded up = {cost}")
    return {"cost": cost, "base": base, "surcharge": cost - base, "reasons": reasons}


# --- link restriction -------------------------------------------------------------------------

_TLDS = (
    "com|org|io|dev|co|ai|app|me|xyz|info|biz|ly|to|link|site|online|store|tech|us|uk|ca|in|pk|ru|cn"
)
_URL_RE = re.compile(
    r"(?:https?://|ftp://)[^\s<>\"')\]]+"
    r"|www\.[^\s<>\"')\]]+"
    r"|(?<![@\w.-])(?:[a-z0-9-]+\.)+(?:" + _TLDS + r")\b(?:/[^\s<>\"')\]]*)?",
    re.IGNORECASE,
)


def _host(url: str) -> str:
    u = re.sub(r"^[a-z]+://", "", url, flags=re.IGNORECASE)
    u = re.split(r"[/?#]", u, maxsplit=1)[0]
    u = u.split("@")[-1].split(":")[0]
    return u.lower().rstrip(".")


def find_disallowed_links(texts: list[str], version: str) -> list[str]:
    """URLs not allowed under the policy version (v2: anything except github.com)."""
    if normalize_version(version) != "2":
        return []
    bad: list[str] = []
    for text in texts:
        for m in _URL_RE.finditer(text or ""):
            url = m.group(0).rstrip(".,;:!?")
            if _host(url) not in ("github.com", "www.github.com"):
                bad.append(url)
    return bad


# --- public description -----------------------------------------------------------------------

def describe(version: str, data_dir: Path | None = None) -> dict:
    version = normalize_version(version)
    out = {
        "version": version,
        "effective_date": POLICY_EFFECTIVE[version],
        "rules_text": list(RULES_TEXT[version]),
        "connects_table": {
            "fixed": [
                {"budget_max_lt": 100, "connects": 2},
                {"budget_max_lt": 500, "connects": 4},
                {"budget_max_lt": 1000, "connects": 6},
                {"budget_max_gte": 1000, "connects": 8},
            ],
            "hourly": 6,
            "high_competition_surcharge": (
                {"min_proposals_count": 15, "multiplier": 1.5, "rounding": "up"} if version == "2" else None
            ),
        },
        "weekly_allowance": WEEKLY_ALLOWANCE,
        "link_restriction": version == "2",
        "allowed_link_hosts": ["github.com"] if version == "2" else None,
    }
    if data_dir is not None:
        pack = Path(data_dir) / "policy_pack" / f"policy_v{version}.yaml"
        if pack.exists():
            try:
                doc = yaml.safe_load(pack.read_text(encoding="utf-8")) or {}
                if isinstance(doc, dict):
                    eff = doc.get("effective_date") or doc.get("effective")
                    if eff:
                        out["effective_date"] = str(eff)
            except (OSError, yaml.YAMLError):
                pass
    return out
