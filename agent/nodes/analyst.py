"""Job Analyst: structured JobSpec from the post. No MCP access."""
from __future__ import annotations

from agent import llm
from agent.handoffs import JobSpec
from agent.nodes._base import job_block, node
from agent.prompts import load_prompt


@node("analyst")
async def analyst(state: dict, config: dict) -> dict:
    job = state["job"]
    spec, _ = await llm.call("analyst", load_prompt("analyst"), job_block(job), JobSpec)
    spec.job_id = job["job_id"]
    spec.title = job.get("title", "")
    if spec.budget_max is None and job.get("budget_max") is not None:
        spec.budget_type = job.get("budget_type", spec.budget_type)
        spec.budget_min, spec.budget_max = job.get("budget_min"), job.get("budget_max")
    if not spec.screening_questions and job.get("screening_questions"):
        spec.screening_questions = list(job["screening_questions"])
    return {"job_spec": spec.model_dump()}
