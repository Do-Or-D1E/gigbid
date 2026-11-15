"""Bid-or-skip decision. Deterministic rules over the three structured reports with
thresholds from config, so the reason for every decision is inspectable and the viva
question "which node got it wrong" has a precise answer."""
from __future__ import annotations

from agent import settings
from agent.handoffs import BidDecision
from agent.nodes._base import node


def budget_ok(job: dict, spec: dict, profile: dict) -> tuple[bool, str]:
    btype = (spec.get("budget_type") if spec.get("budget_type") != "unknown" else None) or job.get("budget_type")
    bmax = spec.get("budget_max") or job.get("budget_max")
    if not bmax:
        return True, "no budget stated"
    if btype == "hourly":
        rate = float(profile.get("hourly_rate_usd", 0) or 0)
        return bmax >= 0.7 * rate, f"hourly budget up to ${bmax:g} vs rate ${rate:g}"
    floor = float(profile.get("min_project_usd", 0) or 0)
    return bmax >= floor, f"fixed budget up to ${bmax:g} vs minimum ${floor:g}"


def decide_action(state: dict) -> BidDecision:
    d = settings.get("decision")
    risk, fit, spec = state.get("risk") or {}, state.get("fit") or {}, state.get("job_spec") or {}
    profile = state.get("profile") or {}
    fit_score, coverage = float(fit.get("fit_score", 0)), float(fit.get("coverage", 0))
    risk_score = float(risk.get("risk_score", 0))
    reasons: list[str] = []
    if risk.get("is_scam") or risk_score >= d["block_risk"]:
        flags = ", ".join(sorted({f.get("kind") for f in risk.get("flags", [])})) or "high risk"
        return BidDecision(action="skip", reasons=[f"Risk: {flags} (risk {risk_score:.2f})"],
                           fit_score=fit_score, risk_score=risk_score)
    ok, why = budget_ok(state.get("job") or {}, spec, profile)
    if not ok:
        return BidDecision(action="skip", reasons=[f"Budget below your floor: {why}"],
                           fit_score=fit_score, risk_score=risk_score)
    reasons.append(f"Fit {fit_score:.2f}, coverage {coverage:.2f}, risk {risk_score:.2f}")
    if fit.get("missing"):
        reasons.append("No evidence for: " + ", ".join(fit["missing"][:4]))
    if fit_score >= d["min_fit_bid"] and coverage >= d["require_coverage"] and risk_score <= d["max_risk_bid"]:
        action = "bid"
    elif fit_score >= d["min_fit_watch"] and risk_score <= d["block_risk"]:
        action = "watch"
        reasons.append("Borderline fit: worth a look, not worth Connects by default")
    else:
        action = "skip"
        reasons.append("Fit too low for the requirements")
    auto = action == "skip" and profile.get("autonomy") == "auto_skip_low_fit"
    return BidDecision(action=action, reasons=reasons, fit_score=fit_score, risk_score=risk_score, auto=auto)


@node("decide")
async def decide(state: dict, config: dict) -> dict:
    decision = decide_action(state)
    status = {"bid": "pricing", "watch": "watch", "skip": "skipped"}[decision.action]
    return {"decision": decision.model_dump(), "status": status}
