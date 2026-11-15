"""Risk Assessor: client quality from marketplace history plus scam, free-work,
off-platform and injection flags. Marketplace (read) access only."""
from __future__ import annotations

import json

from agent import llm
from agent.handoffs import RiskFlag, RiskReport
from agent.mcp_client import MarketplaceDown, ToolCallError
from agent.nodes._base import gateway, job_block, node
from agent.prompts import load_prompt


@node("risk_assessor")
async def risk_assessor(state: dict, config: dict) -> dict:
    job = state["job"]
    client: dict = {}
    if job.get("client_id"):
        try:
            client = await gateway(config).call("get_client_history", {"client_id": job["client_id"]})
        except MarketplaceDown:
            raise
        except ToolCallError as exc:
            client = {"error": str(exc)[:200]}
    hits = state.get("injection_hits") or []
    pre = f"\n\nPattern screen found these suspicious passages: {json.dumps(hits)}" if hits else ""
    user = (f"{job_block(job)}\n\n<client_history>\n{json.dumps(client, default=str)[:3000]}\n</client_history>{pre}")
    report, _ = await llm.call("risk_assessor", load_prompt("risk_assessor"), user, RiskReport)
    # The pattern screen is authoritative for injection flags even if the model misses them.
    if hits and not any(f.kind == "injection" for f in report.flags):
        report.flags.append(RiskFlag(kind="injection", evidence=hits[0][:160], severity="medium"))
        report.injected_instructions = list(dict.fromkeys(report.injected_instructions + hits))
    return {"risk": report.model_dump(), "client": client}
