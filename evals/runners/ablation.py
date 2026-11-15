"""R&D question B: choose the shipped retrieval pipeline by measurement, then ablate it one
component at a time. Only LLM-free components are combined here (hybrid, outcome-aware,
multi-vector, reranking, decomposition); the LLM variants (V6, V7, V8) are compared on a
subset in rag_eval and reported next to these numbers.

    uv run python -m evals.runners.ablation
Writes evals/results/rag_ablation.json and evals/results/rag_decision.json (read by
rag/retriever.py when config says variant: best)."""
from __future__ import annotations

import asyncio
import itertools
import json

from evals.runners import harness as H
from evals.runners.metrics import mean
from evals.runners.rag_eval import eval_variant, queries_for, summarise

COMPONENTS = {
    "hybrid": {"hybrid": True},
    "outcome": {"outcome": True},
    "multivector": {"flavour": "multivector", "project_group": True},
    "rerank": {"rerank": True, "candidates": 30},
    "decompose": {"decompose": True},
}


def flags_for(parts: tuple[str, ...]) -> dict:
    out: dict = {}
    for p in parts:
        out.update(COMPONENTS[p])
    return out


async def run_combo(parts: tuple[str, ...], qsets) -> dict:
    rows = []
    for persona, qs in qsets.items():
        rows += await eval_variant("v0_naive", persona, qs, flags=flags_for(parts) or {"name": "v0_naive"},
                                   concurrency=8)
    s = summarise(rows)
    return {"components": list(parts), "flags": flags_for(parts), **s}


async def main_async() -> dict:
    qsets = {p: queries_for(p, H.load_dev(p)) for p in H.PERSONAS}
    # Phase 1: every subset of the cheap components (fast, no cross-encoder).
    cheap = ["hybrid", "outcome", "multivector", "decompose"]
    combos: list[tuple[str, ...]] = [c for r in range(0, len(cheap) + 1) for c in itertools.combinations(cheap, r)]
    results = {}
    for c in combos:
        key = "+".join(c) or "v0"
        results[key] = await run_combo(c, qsets)
        a = results[key]["all"]
        print(f"{key:40} nDCG@10={a['ndcg@10']} cR@5={a['capped_recall@5']} MRR={a['mrr']} p95={a['p95_latency_s']}s",
              flush=True)
    # Phase 2: the cross-encoder is CPU-heavy, so it is tried alone (V3) and on top of the phase-1 winner.
    top = max(results, key=lambda k: round(results[k]["all"]["ndcg@10"], 3))
    for c in [("rerank",), tuple(results[top]["components"]) + ("rerank",)]:
        key = "+".join(c)
        if key not in results:
            results[key] = await run_combo(c, qsets)
            a = results[key]["all"]
            print(f"{key:40} nDCG@10={a['ndcg@10']} cR@5={a['capped_recall@5']} MRR={a['mrr']} p95={a['p95_latency_s']}s",
                  flush=True)
    # Choose by nDCG@10 (graded relevance, whole top 10), tie-break on lower p95 latency.
    best_key = max(results, key=lambda k: (round(results[k]["all"]["ndcg@10"], 3), -results[k]["all"]["p95_latency_s"]))
    best = results[best_key]
    ablation = {}
    for comp in best["components"]:
        rest = tuple(c for c in best["components"] if c != comp)
        k = "+".join(rest) or "v0"
        ablation[f"without {comp}"] = results.get(k) or await run_combo(rest, qsets)
    return {"combos": results, "best": best_key, "ablation": ablation}


def main() -> int:
    H.setup_env(cache=True)
    out = H.run(main_async())
    best = out["combos"][out["best"]]
    flags = {k: v for k, v in best["flags"].items()}
    H.write_result("rag_ablation.json", out)
    v0 = out["combos"]["v0"]["all"]
    decision = {
        "shipped": {"name": out["best"], "flags": flags},
        "metric": "nDCG@10 on all dev jobs with gold evidence (graded relevance), tie-break p95 latency",
        "v0": {k: v0[k] for k in ("ndcg@10", "capped_recall@5", "recall@5", "mrr")},
        "best": {k: best["all"][k] for k in ("ndcg@10", "capped_recall@5", "recall@5", "mrr", "p95_latency_s")},
        "ablation": {k: {m: v["all"][m] for m in ("ndcg@10", "capped_recall@5", "mrr")} for k, v in out["ablation"].items()},
    }
    H.write_result("rag_decision.json", decision)
    print(json.dumps(decision, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
