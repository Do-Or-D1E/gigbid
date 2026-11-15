"""CI smoke eval (eval.yml): 30 dev jobs through the analysis half of the bid graph plus three
full drafts, and the shipped retriever's nDCG@10. Fails (exit 1) past evals/thresholds.yaml.

    uv run python -m evals.runners.smoke_eval --n 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

import yaml

from evals.runners import harness as H
from evals.runners.metrics import mean, ndcg_at_k, prf


async def main_async(n: int) -> dict:
    from agent.nodes.fit_matcher import requirements_for
    from rag.retriever import RetrievalQuery, get_pipeline

    rows = {p: H.sample([r for r in H.load_dev(p) if not r["gold"].get("dup_of")], n) for p in H.PERSONAS}
    pipe = get_pipeline()
    nd = []
    for p, rs in rows.items():
        for r in rs:
            if r["gold"]["relevant_items"]:
                q = RetrievalQuery(owner=p, title=r["job"]["title"], description=r["job"]["description"],
                                   requirements=requirements_for(r["job"]))
                res = await pipe.retrieve(q, k=10)
                nd.append(ndcg_at_k(res.ranked_ids, r["gold"]["relevant_items"], 10))
    out = []
    async with H.Stack() as st:
        await st.load_jobs([r for rs in rows.values() for r in rs])
        sem = asyncio.Semaphore(3)
        drafts_left = {"n": 3}

        async def one(p, r):
            async with sem:
                full = r["gold"]["action"] == "bid" and drafts_left["n"] > 0
                if full:
                    drafts_left["n"] -= 1
                final, m = await st.run_bid(p, r["job"], until=None if full else "decide")
            return {"gold": r["gold"]["action"], "pred": (final.get("decision") or {}).get("action"),
                    "gold_scam": r["gold"]["is_scam"], "pred_scam": bool((final.get("risk") or {}).get("is_scam")),
                    "unsupported": (final.get("claim_report") or {}).get("unsupported_after") if full else None,
                    "error": m["error"]}
        out = await asyncio.gather(*(one(p, r) for p, rs in rows.items() for r in rs))
    ok = [o for o in out if not o["error"]]
    return {"n": len(out), "errors": len(out) - len(ok),
            "bid_skip_f1": prf([o["pred"] == "bid" for o in ok], [o["gold"] == "bid" for o in ok])["f1"],
            "scam_recall": prf([o["pred_scam"] for o in ok], [o["gold_scam"] for o in ok])["recall"],
            "unsupported_per_proposal": mean(o["unsupported"] for o in ok if o["unsupported"] is not None) or 0.0,
            "rag_ndcg10": mean(nd)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args(argv)
    H.setup_env(cache=True)
    res = H.run(main_async(args.n))
    th = yaml.safe_load((H.ROOT / "evals" / "thresholds.yaml").read_text(encoding="utf-8"))
    fails = []
    if res["bid_skip_f1"] < th["min_bid_skip_f1"]:
        fails.append(f"bid_skip_f1 {res['bid_skip_f1']} < {th['min_bid_skip_f1']}")
    if res["unsupported_per_proposal"] > th["max_unsupported_per_proposal"]:
        fails.append(f"unsupported {res['unsupported_per_proposal']} > {th['max_unsupported_per_proposal']}")
    if (res["rag_ndcg10"] or 0) < th["min_rag_ndcg10"]:
        fails.append(f"rag_ndcg10 {res['rag_ndcg10']} < {th['min_rag_ndcg10']}")
    if res["scam_recall"] < th["min_scam_recall"]:
        fails.append(f"scam_recall {res['scam_recall']} < {th['min_scam_recall']}")
    res["failures"] = fails
    H.write_result("smoke_eval.json", res)
    print(json.dumps(res, indent=1))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
