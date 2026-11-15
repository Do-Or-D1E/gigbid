"""Pricing Strategist: bid from market statistics, client spend and the user's floor, and
decide whether the Connects cost is worth it. The Connects cost always comes from the
marketplace's live quote (policy-aware), never from a formula in code, which is why the
2 Nov policy update did not need a pricing change."""
from __future__ import annotations

import json
import math

from agent import llm, settings
from agent.handoffs import PriceQuote
from agent.nodes._base import gateway, node
from agent.prompts import load_prompt


@node("pricing")
async def pricing(state: dict, config: dict) -> dict:
    gw = gateway(config)
    job, spec, profile = state["job"], state.get("job_spec") or {}, state.get("profile") or {}
    stats = await gw.call("get_pricing_stats", {"category": job.get("category"), "skills": (job.get("skills") or [])[:5]})
    quote = await gw.call("quote_connects", {"job_id": job["job_id"]})
    balance = await gw.call("get_connects_balance", {})
    btype = job.get("budget_type") if job.get("budget_type") in ("fixed", "hourly") else "fixed"
    floor = float(profile.get("hourly_rate_usd" if btype == "hourly" else "min_project_usd", 0) or 0)
    floor *= float(settings.get("pricing.floor_multiplier", 1.0))
    facts = {
        "budget_type": btype, "budget_min": job.get("budget_min"), "budget_max": job.get("budget_max"),
        "market": stats, "client": {k: (state.get("client") or {}).get(k) for k in ("total_spent_usd", "hires",
                                                                                   "avg_rating_given")},
        "freelancer_floor": floor, "fit_score": (state.get("fit") or {}).get("fit_score"),
        "connects_cost": quote.get("connects_cost"), "proposals_count": job.get("proposals_count"),
    }
    q, _ = await llm.call("pricing", load_prompt("pricing"), json.dumps(facts, default=str), PriceQuote)
    # Deterministic guards on top of the model's proposal.
    q.bid_type = btype
    q.floor = floor
    q.amount = round(max(q.amount, floor), 2)
    q.connects_cost = int(quote.get("connects_cost", 0))
    q.connects_usd = round(q.connects_cost * float(settings.get("marketplace.connect_usd", 0.15)), 2)
    band = stats.get(btype) if isinstance(stats.get(btype), dict) else stats
    q.market_p25, q.market_p50, q.market_p75 = band.get("p25"), band.get("p50"), band.get("p75")
    hours = 20 if btype == "hourly" else 1
    q.expected_value_usd = round(q.win_probability * q.amount * hours, 2)
    min_ratio = float(settings.get("pricing.min_expected_value_ratio", 3.0))
    weekly_left = int(balance.get("balance", 0))
    budget_left = int(profile.get("weekly_connects_budget", weekly_left) or weekly_left)
    reasons = []
    if q.expected_value_usd < min_ratio * max(q.connects_usd, 0.01):
        reasons.append(f"expected value ${q.expected_value_usd} under {min_ratio}x the Connects cost")
    if q.connects_cost > min(weekly_left, budget_left):
        reasons.append(f"needs {q.connects_cost} Connects, only {min(weekly_left, budget_left)} left this week")
    q.worth_it = not reasons
    if reasons:
        q.rationale = (q.rationale + " Not worth it: " + "; ".join(reasons)).strip()
    out: dict = {"price": q.model_dump()}
    if not q.worth_it:
        out["status"] = "watch"
        out["decision"] = {**(state.get("decision") or {}), "action": "watch",
                           "reasons": [*(state.get("decision") or {}).get("reasons", []), *reasons]}
    return out


def ceil_connects(cost: float) -> int:
    return int(math.ceil(cost))
