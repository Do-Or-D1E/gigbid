"""Scout: runs saved searches on schedule, deduplicates, queues new jobs (worker side), and
hands one job into the bid graph (`scout_intake`), screening it for injected text."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from agent import guardrails
from agent.nodes._base import gateway, node


def dedupe_key(job: dict[str, Any]) -> str:
    """Near-duplicate key: same client and the same title/description shingles."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    words = re.findall(r"[a-z0-9]+", text)
    shingles = sorted({" ".join(words[i:i + 3]) for i in range(0, max(1, len(words) - 2))})[:40]
    basis = f"{job.get('client_id', '')}|{'|'.join(shingles)}"
    return hashlib.sha256(basis.encode()).hexdigest()[:20]


def similarity(a: dict, b: dict) -> float:
    def sh(job: dict) -> set[str]:
        words = re.findall(r"[a-z0-9]+", f"{job.get('title', '')} {job.get('description', '')}".lower())
        return {" ".join(words[i:i + 3]) for i in range(0, max(1, len(words) - 2))}
    x, y = sh(a), sh(b)
    return len(x & y) / max(1, len(x | y))


async def run_saved_search(gw, search: dict, known: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (new_jobs, duplicates). `known` are jobs already in the user's inbox."""
    found = await gw.call("search_jobs", {"query": search.get("query", ""), "limit": 30,
                                          **{k: v for k, v in (search.get("filters") or {}).items()
                                             if k in ("category", "skills")}})
    jobs = found.get("jobs", []) if isinstance(found, dict) else found
    known_ids = {k["job_id"] for k in known}
    new, dups = [], []
    for j in jobs:
        if j["job_id"] in known_ids:
            continue
        is_dup = any(similarity(j, k) > 0.6 and j.get("client_id") == k.get("client_id") for k in known + new)
        (dups if is_dup else new).append(j)
    return new, dups


@node("scout")
async def scout_intake(state: dict, config: dict) -> dict:
    job = state.get("job")
    if not job or "description" not in job:
        job = await gateway(config).call("get_job", {"job_id": state["job_id"]})
    hits = guardrails.detect_injection(f"{job.get('title', '')}\n{job.get('description', '')}")
    return {"job": job, "injection_hits": hits, "status": "analysing", "revisions": 0}
