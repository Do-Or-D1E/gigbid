"""Signature extension X2: proposal experiments. Two writer strategies are run as an A/B test
in GigSim on the same bid-worthy dev jobs (paired design):
  A  writer.md            evidence-first, personalised, up to 260 words (the default)
  B  writer_question.md   short (<=120 words), opens with a specific question, one or two items
Everything else (analysis, retrieval, pricing, verification, compliance) is identical.
GigSim is reset between arms so each arm can submit to every job once. Primary metric:
GigSim's reply probability per proposal (paired t-test and a sign-flip permutation test);
secondary: simulated reply outcome (exact McNemar test).

    uv run python -m evals.runners.ab_test --n 8 --profile paid
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random

from evals.runners import harness as H
from evals.runners.metrics import mean


def paired_t(a: list[float], b: list[float]) -> dict:
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    if n < 3:
        return {"n": n}
    md = sum(d) / n
    sd = math.sqrt(sum((x - md) ** 2 for x in d) / (n - 1))
    t = md / (sd / math.sqrt(n)) if sd > 0 else float("inf")
    # two-sided p from the t distribution via a sign-flip permutation test (exact enough, no scipy)
    rng = random.Random(4016)
    obs = abs(md)
    hits = sum(1 for _ in range(20000) if abs(sum(x * rng.choice((-1, 1)) for x in d) / n) >= obs - 1e-12)
    return {"n": n, "mean_diff_A_minus_B": round(md, 5), "t": round(t, 3), "p_permutation": round(hits / 20000, 4)}


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    b01 = sum(1 for x, y in zip(a, b) if x and not y)
    b10 = sum(1 for x, y in zip(a, b) if y and not x)
    n = b01 + b10
    if n == 0:
        return {"discordant": 0, "p": 1.0}
    k = min(b01, b10)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"A_only": b01, "B_only": b10, "p": round(p, 4)}


async def arm(rows: dict, prompt: str, tag: str) -> dict[str, dict]:
    from langgraph.types import Command

    from agent.mcp_client import McpGateway
    from evals.runners.decision_eval import ensure_connects, outcome

    os.environ["GIGBID_WRITER_PROMPT"] = prompt
    out: dict[str, dict] = {}
    async with H.Stack(submit=True) as st:
        await st.gigsim("POST", "/admin/reset")
        await st.load_jobs([r for rs in rows.values() for r in rs])
        sem, lock = asyncio.Semaphore(5), asyncio.Lock()

        async def one(p, r):
            async with sem:
                final, m = await st.run_bid(p, r["job"])
                if final.get("status") != "awaiting_approval":
                    return r["job"]["job_id"], {"status": final.get("status"), "error": m["error"]}
                async with lock:
                    await ensure_connects(st, p)
                    async with McpGateway(f"ab-{tag}-{p}", p, trace_id=f"ab-{tag}") as gw:
                        cfg = {**m["config"], "configurable": {**m["config"]["configurable"], "gateway": gw}}
                        async for _ in st.bid.astream(Command(resume={"action": "approve", "user_id": "ab"}), cfg,
                                                      stream_mode="updates"):
                            pass
                        final = (await st.bid.aget_state(cfg)).values
                    res = await outcome(st, final)
                draft = final.get("draft") or {}
                return r["job"]["job_id"], {"status": final.get("status"), "p_reply": res.get("p_reply"),
                                            "replied": res.get("replied"), "words": len(draft.get("cover_letter", "").split()),
                                            "unsupported": (final.get("claim_report") or {}).get("unsupported_after"),
                                            "list_usd": m["list_usd"], "cover_letter": draft.get("cover_letter")}
        for jid, res in await asyncio.gather(*(one(p, r) for p, rs in rows.items() for r in rs)):
            out[jid] = res
            print(tag, jid, res.get("status"), res.get("p_reply"), flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="bid jobs per persona")
    ap.add_argument("--profile", default=None)
    args = ap.parse_args(argv)
    H.setup_env(cache=True, profile=args.profile)
    rows = {p: H.sample([r for r in H.load_dev(p) if r["gold"]["action"] == "bid" and not r["gold"].get("dup_of")
                         and not r["gold"].get("has_injection")], args.n, seed=7) for p in H.PERSONAS}
    a = H.run(arm(rows, "writer", "A"))
    b = H.run(arm(rows, "writer_question", "B"))
    both = [j for j in a if a[j].get("p_reply") is not None and b.get(j, {}).get("p_reply") is not None]
    pa, pb = [a[j]["p_reply"] for j in both], [b[j]["p_reply"] for j in both]
    res = {
        "design": "paired, same jobs, GigSim reset between arms; A=writer.md, B=writer_question.md",
        "n_pairs": len(both),
        "A": {"mean_p_reply": mean(pa), "reply_rate": round(sum(bool(a[j]["replied"]) for j in both) / max(1, len(both)), 4),
              "mean_words": mean(a[j]["words"] for j in both), "unsupported": mean(a[j]["unsupported"] for j in both)},
        "B": {"mean_p_reply": mean(pb), "reply_rate": round(sum(bool(b[j]["replied"]) for j in both) / max(1, len(both)), 4),
              "mean_words": mean(b[j]["words"] for j in both), "unsupported": mean(b[j]["unsupported"] for j in both)},
        "paired_t_on_p_reply": paired_t(pa, pb),
        "mcnemar_on_replies": mcnemar_exact([bool(a[j]["replied"]) for j in both], [bool(b[j]["replied"]) for j in both]),
        **H.spend_report(),
    }
    H.write_result("ab_test.json", res)
    H.write_result("ab_test_per_job.jsonl", [{"job_id": j, "A": a[j], "B": b.get(j)} for j in sorted(a)])
    print(json.dumps({k: v for k, v in res.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
