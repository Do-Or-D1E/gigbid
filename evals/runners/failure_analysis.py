"""Failure analysis (report section 8): every failed dev job in the main run, grouped into the
brief's taxonomy. Categories are assigned mechanically from the per-job record:
  wrong skip         gold bid, predicted skip/watch
  wrong bid          gold skip, predicted bid (includes missed scams)
  mispriced          gold and predicted bid, price outside the gold fair band
  unsupported claim  final draft still carries unsupported claims
  compliance miss    final draft blocked by the Compliance Guard
  injection          an injected instruction succeeded
  tool error         the run errored
Writes evals/results/failure_analysis.json with each case and its likely failing node.

    uv run python -m evals.runners.failure_analysis --tag main
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from evals.runners import harness as H


def node_for(cat: str, r: dict) -> str:
    if cat == "wrong skip":
        if (r.get("risk_score") or 0) >= 0.55:
            return "risk_assessor (risk too high)"
        if (r.get("fit_score") or 0) < 0.55:
            return "fit_matcher (fit too low)"
        return "decide (thresholds)"
    if cat == "wrong bid":
        return "risk_assessor (missed scam)" if r.get("gold_scam") else "fit_matcher (fit too high)"
    if cat == "mispriced":
        return "pricing"
    if cat in ("unsupported claim", "compliance miss"):
        return "writer / verifier"
    if cat == "injection":
        return "writer / compliance"
    return "tooling"


def classify(r: dict) -> list[str]:
    cats = []
    if r.get("error"):
        cats.append("tool error")
    if r["gold_action"] == "bid" and r["pred_action"] != "bid":
        cats.append("wrong skip")
    if r["gold_action"] == "skip" and r["pred_action"] == "bid":
        cats.append("wrong bid")
    if r.get("price_in_band") is False and r["gold_action"] == "bid" and r["pred_action"] == "bid":
        cats.append("mispriced")
    if (r.get("unsupported_final") or 0) > 0:
        cats.append("unsupported claim")
    if r.get("compliance") == "block" or r.get("status") == "blocked":
        cats.append("compliance miss")
    if r.get("injection_success"):
        cats.append("injection")
    return cats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    args = ap.parse_args(argv)
    path = H.RESULTS / f"decisions_{args.tag}_per_job.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]
    cases = []
    for r in rows:
        for cat in classify(r):
            cases.append({"job_id": r["job_id"], "persona": r["persona"], "category": cat, "node": node_for(cat, r),
                          "job_type": r["job_type"], "gold": r["gold_action"], "pred": r["pred_action"],
                          "fit": r.get("fit_score"), "risk": r.get("risk_score"), "price": r.get("price"),
                          "band": r.get("fair_band"), "attention": r.get("attention")})
    out = {"run": args.tag, "jobs": len(rows), "failed_jobs": len({c["job_id"] for c in cases}),
           "by_category": dict(Counter(c["category"] for c in cases)),
           "by_node": dict(Counter(c["node"] for c in cases)), "cases": cases}
    H.write_result(f"failure_analysis_{args.tag}.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "cases"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
