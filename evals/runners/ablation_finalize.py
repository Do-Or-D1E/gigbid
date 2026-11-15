"""Finalises the RAG choice when the full ablation was cut short (the CPU cross-encoder was too
slow on the dev machine). Phase-1 numbers (all 16 combinations of the cheap components on all
dev jobs) are parsed from the ablation log; the shipped combination is re-run here for its full
breakdown, and V3 reranking is measured on a stratified subset (--rerank-limit per persona),
alone and on top of the shipped combination, against V0 and the shipped pipeline on the same subset.

    uv run python -m evals.runners.ablation_finalize --log cache/ablation.log --rerank-limit 25
"""
from __future__ import annotations

import argparse
import json
import re

from evals.runners import harness as H
from evals.runners.ablation import flags_for
from evals.runners.rag_eval import eval_variant, queries_for, summarise

LINE = re.compile(r"^(\S+)\s+nDCG@10=([\d.]+) cR@5=([\d.]+) MRR=([\d.]+) p95=([\d.]+)s")


async def run(parts: tuple[str, ...], qsets) -> dict:
    rows = []
    for persona, qs in qsets.items():
        rows += await eval_variant("v0_naive", persona, qs, flags=flags_for(parts) or {"name": "v0_naive"}, concurrency=8)
    return {"components": list(parts), "flags": flags_for(parts), **summarise(rows)}


async def main_async(args) -> dict:
    combos = {}
    for line in open(args.log, encoding="utf-8", errors="ignore"):
        m = LINE.match(line)
        if m:
            combos[m.group(1)] = {"components": [] if m.group(1) == "v0" else m.group(1).split("+"),
                                  "all": {"ndcg@10": float(m.group(2)), "capped_recall@5": float(m.group(3)),
                                          "mrr": float(m.group(4)), "p95_latency_s": float(m.group(5))},
                                  "source": "ablation log (all dev jobs)"}
    best_key = max(combos, key=lambda k: (round(combos[k]["all"]["ndcg@10"], 3), -combos[k]["all"]["p95_latency_s"]))
    full = {p: queries_for(p, H.load_dev(p)) for p in H.PERSONAS}
    parts = tuple(combos[best_key]["components"])
    combos[best_key] = {**await run(parts, full), "source": "re-run (all dev jobs)"}
    combos["v0"] = {**await run((), full), "source": "re-run (all dev jobs)"}
    sub = {p: queries_for(p, H.sample(H.load_dev(p), args.rerank_limit)) for p in H.PERSONAS}
    subset = {"v0": await run((), sub), best_key: await run(parts, sub), "rerank": await run(("rerank",), sub),
              f"{best_key}+rerank": await run(parts + ("rerank",), sub)}
    ablation = {}
    for comp in parts:
        rest = "+".join(c for c in parts if c != comp) or "v0"
        ablation[f"without {comp}"] = combos.get(rest)
    return {"combos": combos, "best": best_key, "ablation": ablation,
            "rerank_subset": {"jobs_per_persona_sampled": args.rerank_limit, "results": subset}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="cache/ablation.log")
    ap.add_argument("--rerank-limit", type=int, default=25)
    args = ap.parse_args(argv)
    H.setup_env(cache=True)
    out = H.run(main_async(args))
    H.write_result("rag_ablation.json", out)
    best = out["combos"][out["best"]]
    v0 = out["combos"]["v0"]["all"]
    rs = out["rerank_subset"]["results"]
    decision = {
        "shipped": {"name": out["best"], "flags": best["flags"]},
        "metric": "nDCG@10 on all dev jobs with gold evidence (graded relevance), tie-break p95 latency",
        "v0": {k: v0[k] for k in ("ndcg@10", "capped_recall@5", "recall@5", "mrr")},
        "best": {k: best["all"][k] for k in ("ndcg@10", "capped_recall@5", "recall@5", "mrr", "p95_latency_s")},
        "ablation": {k: {m: v["all"][m] for m in ("ndcg@10", "capped_recall@5", "mrr")} for k, v in out["ablation"].items() if v},
        "rerank_on_subset": {k: {m: v["all"][m] for m in ("ndcg@10", "capped_recall@5", "mrr", "p95_latency_s")}
                             for k, v in rs.items()},
        "decision_note": ("Ship the best cheap combination. The cross-encoder is judged on the subset: it is shipped only "
                          "if it adds nDCG@10 worth its CPU latency and package size in a serverless function."),
    }
    H.write_result("rag_decision.json", decision)
    print(json.dumps(decision, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
