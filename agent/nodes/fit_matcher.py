"""Fit Matcher: maps every requirement to portfolio evidence through the Portfolio MCP
server (read), then scores fit with reasons. Runs in parallel with the Job Analyst, so it
derives its own requirement list from the listing's skills plus skill names tagged in the
post (no extra model call); vague posts fall back to the whole post as one query."""
from __future__ import annotations

import asyncio
import json

from agent import llm
from agent.handoffs import FitReport
from agent.nodes._base import gateway, job_block, node
from agent.prompts import load_prompt
from rag.ingest.skills import tag_skills


def requirements_for(job: dict, limit: int = 7) -> list[str]:
    reqs = list(dict.fromkeys([*(job.get("skills") or []), *tag_skills(job.get("description", ""))]))
    return reqs[:limit]


@node("fit_matcher")
async def fit_matcher(state: dict, config: dict) -> dict:
    job = state["job"]
    gw = gateway(config)
    reqs = requirements_for(job) or [job.get("title", "the job")]
    hidden = (state.get("profile") or {}).get("hidden_items") or None
    filters = {"exclude_items": hidden} if hidden else None
    results = await asyncio.gather(*(
        gw.call("search_evidence", {"requirement": f"{r}. {job.get('title', '')}"[:290], "k": 4,
                                    **({"filters": filters} if filters else {})})
        for r in reqs))
    evidence: dict[str, dict] = {}
    rows = []
    for req, res in zip(reqs, results):
        ids = []
        for it in res.get("items", []):
            evidence.setdefault(it["item_id"], {**it, "score": 1.0 / it.get("rank", 1)})
            ids.append(it["item_id"])
        rows.append({"requirement": req, "candidates": ids})
    ev_text = "\n".join(f'<evidence id="{e["item_id"]}" type="{e["type"]}" title="{e["title"]}">'
                        f'{e["snippet"][:450]}</evidence>' for e in evidence.values())
    user = (f"{job_block(job)}\n\nRequirements to check (from the listing): {json.dumps(reqs)}\n"
            f"Retrieved candidates per requirement: {json.dumps(rows)}\n\n{ev_text}")
    report, _ = await llm.call("fit_matcher", load_prompt("fit_matcher"), user, FitReport)
    known = set(evidence)
    for m in report.matches:
        m.evidence_ids = [i for i in m.evidence_ids if i in known]
        if not m.evidence_ids and m.strength != "none":
            m.strength = "none"
    return {"fit": report.model_dump(), "evidence": list(evidence.values())}
