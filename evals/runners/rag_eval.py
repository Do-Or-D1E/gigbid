"""R&D question B, retrieval part: evidence Recall@5, MRR and nDCG@10 for every RAG variant
on the dev set, broken down by persona and job type.

Queries are built exactly as the Fit Matcher builds them in the graph (listing skills plus
skill names tagged in the post), so the numbers describe the deployed retriever.

    uv run python -m evals.runners.rag_eval --variants v0_naive v1_decompose v2_hybrid ...
    uv run python -m evals.runners.rag_eval --variants v7_hyde v8_corrective --limit 40   # LLM variants on a subset
"""
from __future__ import annotations

import argparse
import asyncio
import time
from collections import defaultdict

from evals.runners import harness as H
from evals.runners.metrics import capped_recall_at_k, mean, mrr, ndcg_at_k, recall_at_k


def queries_for(persona: str, rows: list[dict]):
    from agent.nodes.fit_matcher import requirements_for
    from rag.variants.base import RetrievalQuery

    out = []
    for r in rows:
        g, j = r["gold"], r["job"]
        if not g["relevant_items"] or g.get("dup_of"):
            continue
        out.append((r, RetrievalQuery(owner=persona, title=j["title"], description=j["description"],
                                      requirements=requirements_for(j), category=j.get("category", ""))))
    return out


async def eval_variant(name: str, persona: str, qs, *, flags: dict | None = None, embed: str | None = None,
                       concurrency: int = 4) -> list[dict]:
    from rag.retriever import variant_config
    from rag.variants.base import Pipeline

    cfg = variant_config(name)
    if flags:
        cfg = cfg.with_(**flags)
    pipe = Pipeline(cfg)
    if embed:
        from rag.index import store

        orig = store.get_index

        def patched(owner, flavour="plain", embed_model=None):
            return orig(owner, flavour, embed)
        store.get_index = patched
        import rag.variants.base as base
        base.get_index = patched
    sem = asyncio.Semaphore(concurrency)

    async def one(row, q):
        async with sem:
            t0 = time.perf_counter()
            try:
                res = await pipe.retrieve(q, k=10)
                ranked, err = res.ranked_ids, None
            except Exception as exc:  # noqa: BLE001
                ranked, err = [], f"{type(exc).__name__}: {exc}"[:200]
            dt = time.perf_counter() - t0
        rel = row["gold"]["relevant_items"]
        return {"job_id": row["job"]["job_id"], "persona": persona, "variant": cfg.name if not flags else name,
                "job_type": row["gold"]["job_type"], "n_relevant": len(rel), "ranked": ranked[:10],
                "recall@5": recall_at_k(ranked, rel, 5), "capped_recall@5": capped_recall_at_k(ranked, rel, 5), "mrr": mrr(ranked, rel), "ndcg@10": ndcg_at_k(ranked, rel, 10),
                "latency_s": round(dt, 4), "error": err}

    out = await asyncio.gather(*(one(r, q) for r, q in qs))
    if embed:
        from importlib import reload

        import rag.index.store
        import rag.variants.base
        reload(rag.index.store)
        reload(rag.variants.base)
    return out


def summarise(rows: list[dict]) -> dict:
    def agg(rs):
        return {"n": len(rs), "recall@5": mean(r["recall@5"] for r in rs),
                "capped_recall@5": mean(r["capped_recall@5"] for r in rs), "mrr": mean(r["mrr"] for r in rs),
                "ndcg@10": mean(r["ndcg@10"] for r in rs),
                "p95_latency_s": sorted(r["latency_s"] for r in rs)[int(0.95 * (len(rs) - 1))] if rs else None,
                "errors": sum(1 for r in rs if r["error"])}
    by_persona, by_type = defaultdict(list), defaultdict(list)
    for r in rows:
        by_persona[r["persona"]].append(r)
        for t in r["job_type"]:
            by_type[t].append(r)
    return {"all": agg(rows), "by_persona": {k: agg(v) for k, v in sorted(by_persona.items())},
            "by_job_type": {k: agg(v) for k, v in sorted(by_type.items())}}


async def main_async(args) -> dict:
    results: dict = {}
    per_job: list[dict] = []
    for persona in args.personas:
        rows = H.load_dev(persona)
        if args.limit:
            rows = H.sample(rows, args.limit)
        qs = queries_for(persona, rows)
        for v in args.variants:
            label = v + (f"@{args.embed.split('/')[-1]}" if args.embed else "")
            t0 = time.perf_counter()
            res = await eval_variant(v, persona, qs, embed=args.embed, concurrency=args.concurrency)
            for r in res:
                r["variant"] = label
            per_job += res
            print(f"{persona:13} {label:28} n={len(res):3} R@5={mean(r['recall@5'] for r in res)} "
                  f"cR@5={mean(r['capped_recall@5'] for r in res)} MRR={mean(r['mrr'] for r in res)} nDCG={mean(r['ndcg@10'] for r in res)} "
                  f"({time.perf_counter() - t0:.1f}s)", flush=True)
    for label in sorted({r["variant"] for r in per_job}):
        results[label] = summarise([r for r in per_job if r["variant"] == label])
    return {"results": results, "per_job": per_job}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", default=["v0_naive", "v1_decompose", "v2_hybrid", "v3_rerank", "v4_outcome",
                                                       "v5_multivector"])
    ap.add_argument("--personas", nargs="+", default=H.PERSONAS)
    ap.add_argument("--limit", type=int, default=0, help="stratified sample size per persona (0 = all)")
    ap.add_argument("--embed", default=None, help="override the embedding model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--out", default="rag_retrieval.json")
    args = ap.parse_args(argv)
    H.setup_env(cache=True)
    out = H.run(main_async(args))
    path = H.RESULTS / args.out
    merged = {}
    if path.exists():
        import json

        merged = json.loads(path.read_text(encoding="utf-8")).get("results", {})
    merged.update(out["results"])
    H.write_result(args.out, {"results": merged, "note": "relevance from gold relevant_items; queries as in fit_matcher",
                              "limit_per_persona": args.limit or "all"})
    H.write_result(args.out.replace(".json", "_per_job.jsonl"), out["per_job"]) if not args.limit else None
    print(H.spend_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
