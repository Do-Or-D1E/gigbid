"""Regenerates every results table in README.md and the report from evals/results/*.json.

    uv run python -m evals.runners.make_tables      # writes evals/results/tables.md and updates README blocks
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "evals" / "results"


def j(name: str) -> dict | None:
    p = RES / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def f(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def rag_table() -> str:
    abl = j("rag_ablation.json") or {}
    ret = (j("rag_retrieval.json") or {}).get("results", {})
    combos = abl.get("combos", {})
    rows = ["| Variant | What changes | Recall@5 | Capped R@5 | MRR | nDCG@10 |", "|---|---|---|---|---|---|"]
    named = [("V0 naive dense", "v0", "v0_naive"), ("V1 decomposition", "decompose", "v1_decompose"),
             ("V2 hybrid BM25+dense", "hybrid", "v2_hybrid"), ("V3 cross-encoder rerank", "rerank", "v3_rerank"),
             ("V4 outcome-aware", "outcome", "v4_outcome"), ("V5 multi-vector projects", "multivector", "v5_multivector"),
             ("V6 contextual chunks", None, "v6_contextual"), ("V7 HyDE", None, "v7_hyde"),
             ("V8 corrective loop", None, "v8_corrective")]
    for label, ckey, rkey in named:
        a = (combos.get(ckey) or {}).get("all") if ckey else None
        a = a or (ret.get(rkey) or {}).get("all")
        if not a:
            continue
        rows.append(f"| {label} | {rkey} | {f(a.get('recall@5'))} | {f(a.get('capped_recall@5'))} | {f(a.get('mrr'))} | "
                    f"{f(a.get('ndcg@10'))} |")
    best = abl.get("best")
    if best and best in combos:
        a = combos[best]["all"]
        rows.append(f"| **Shipped: {best}** | combination | {f(a.get('recall@5'))} | {f(a.get('capped_recall@5'))} | "
                    f"{f(a.get('mrr'))} | {f(a.get('ndcg@10'))} |")
    return "\n".join(rows)


def ablation_table() -> str:
    d = j("rag_decision.json") or {}
    if "ablation" not in d:
        return "_ablation pending_"
    rows = ["| Pipeline | nDCG@10 | Capped R@5 | MRR |", "|---|---|---|---|",
            f"| {d['shipped']['name']} (shipped) | {f(d['best']['ndcg@10'])} | {f(d['best']['capped_recall@5'])} | {f(d['best']['mrr'])} |"]
    for k, v in d["ablation"].items():
        rows.append(f"| {k} | {f(v['ndcg@10'])} | {f(v['capped_recall@5'])} | {f(v['mrr'])} |")
    return "\n".join(rows)


def headline_table() -> str:
    ab = j("ab_rag.json")
    judge_a = j("ab_rag_A_judge_summary.json") or {}
    judge_b = j("ab_rag_B_judge_summary.json") or {}
    d = j("rag_decision.json") or {}
    abl = (j("rag_ablation.json") or {}).get("combos", {})
    v0r, bestr = (abl.get("v0") or {}).get("all", {}), (abl.get(d.get("shipped", {}).get("name", "")) or {}).get("all", {})
    rows = ["| Variant | Evidence Recall@5 | nDCG@10 | Unsupported claims per proposal | Judge score (1-5) | "
            "GigSim reply rate | Mean reply probability | p95 latency (s) | Cost per proposal (USD, list) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for label, r, arm, jd in (("V0", v0r, "A", judge_a), ("Shipped best", bestr, "B", judge_b)):
        s = (ab or {}).get(arm, {})
        rows.append(f"| {label} | {f(r.get('recall@5'))} | {f(r.get('ndcg@10'))} | {f(s.get('unsupported_per_proposal'), 2)} | "
                    f"{f(jd.get('judge_overall_mean'), 2)} | {f(s.get('reply_rate'), 2)} | {f(s.get('mean_p_reply'), 3)} | "
                    f"{f(s.get('p95_latency_s'), 1)} | {f(s.get('list_usd_per_proposal'), 4)} |")
    return "\n".join(rows)


def decisions_table() -> str:
    rows = ["| Run | Profile | Jobs | Bid/skip F1 | Accuracy | Scam P / R | Price in fair band | Unsupported (first draft -> final) "
            "| p95 s / job analysed | p95 s / proposal | USD / job (list) | USD / proposal (list) |", "|---|" * 1 + "---|" * 11]
    for tag in ("main", "open", "open_qwen"):
        d = j(f"decisions_{tag}.json")
        if not d:
            continue
        s = d["summary"]
        rows.append(f"| {tag} | {d['profile']} | {s['n']} | {f(s['bid_skip']['f1'])} | {f(s['bid_skip']['accuracy'])} | "
                    f"{f(s['scam']['precision'], 2)} / {f(s['scam']['recall'], 2)} | {f(s['price_in_band'], 2)} | "
                    f"{f(s['unsupported_per_proposal_first_draft'], 2)} -> {f(s['unsupported_per_proposal_final'], 2)} | "
                    f"{f(s['latency_s']['p95_job_analysed'], 1)} | {f(s['latency_s']['p95_proposal'], 1)} | "
                    f"{f(s['cost_usd_list']['per_job_analysed'], 4)} | {f(s['cost_usd_list']['per_proposal'], 4)} |")
    return "\n".join(rows)


def injection_table() -> str:
    on, off = j("decisions_inj_on.json"), j("decisions_inj_off.json")
    if not (on and off):
        return "_injection runs pending_"
    def by_goal(tag):
        p = RES / f"decisions_{tag}_per_job.jsonl"
        out: dict = {}
        for line in p.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                if r.get("injection_success") is not None:
                    out.setdefault(r["injection_goal"], []).append(bool(r["injection_success"]))
        return out
    a, b = by_goal("inj_off"), by_goal("inj_on")
    rows = ["| Injection goal | Attacks | Success, defences off | Success, defences on |", "|---|---|---|---|"]
    for g in sorted(set(a) | set(b)):
        rows.append(f"| {g} | {len(b.get(g, []))} | {sum(a.get(g, []))}/{len(a.get(g, []))} | {sum(b.get(g, []))}/{len(b.get(g, []))} |")
    rows.append(f"| **all** | {on['summary']['n_injection']} | {f(off['summary']['injection_attack_success_rate'], 2)} | "
                f"{f(on['summary']['injection_attack_success_rate'], 2)} |")
    return "\n".join(rows)


def multiagent_table() -> str:
    d = j("multiagent_compare.json")
    if not d:
        return "_comparison pending_"
    rep = j("multiagent_replies.json") or {}
    rows = ["| System | Jobs | Bid/skip accuracy | F1 | Scam recall | Unsupported / proposal | Proposals with policy "
            "violations | Mean reply probability | Tokens / job | p95 latency (s) |", "|---|" + "---|" * 9]
    names = {"react": "(a) single ReAct agent", "supervisor": "(b) langgraph-supervisor", "graph": "(c) hand-built graph"}
    for k, s in d["systems"].items():
        rows.append(f"| {names.get(k, k)} | {s['n']} | {f(s['bid_skip_accuracy'])} | {f(s['bid_skip_f1'])} | "
                    f"{f(s['scam_recall'], 2)} | {f(s['unsupported_per_proposal'], 2)} | {s['proposals_with_violations']} | "
                    f"{f((rep.get(k) or {}).get('mean_p_reply'), 3)} | {f(s['tokens_per_job'], 0)} | {f(s['p95_latency_s'], 1)} |")
    return "\n".join(rows)


def tools_table() -> str:
    d = j("tool_granularity_paid.json") or j("tool_granularity_open_qwen.json")
    if not d:
        return "_tool study pending_"
    rows = [f"Model: {d['model']}, {d['n_tasks']} tasks.", "",
            "| Tool design | Tools | Tool-selection accuracy | Argument accuracy | Tokens per task |", "|---|---|---|---|---|"]
    for k, s in d["summary"].items():
        rows.append(f"| {k} | {s['tools']} | {f(s['tool_selection_accuracy'])} | {f(s['argument_accuracy'])} | "
                    f"{f(s['tokens_per_task'], 0)} |")
    return "\n".join(rows)


def ab_table() -> str:
    d = j("ab_writer.json")
    if not d:
        return "_A/B pending_"
    t = d["paired_t_on_p_reply"]
    return "\n".join(["| Arm | Pairs | Mean reply probability | Reply rate | Words | Unsupported |", "|---|---|---|---|---|---|",
                      f"| A evidence-first | {d['n_pairs']} | {f(d['A']['mean_p_reply'])} | {f(d['A']['reply_rate'], 2)} | "
                      f"{f(d['A']['mean_words'], 0)} | {f(d['A']['unsupported_per_proposal'], 2)} |",
                      f"| B short + question | {d['n_pairs']} | {f(d['B']['mean_p_reply'])} | {f(d['B']['reply_rate'], 2)} | "
                      f"{f(d['B']['mean_words'], 0)} | {f(d['B']['unsupported_per_proposal'], 2)} |", "",
                      f"Paired difference A-B in reply probability: {f(t.get('mean_diff_A_minus_B'), 4)}, "
                      f"t = {f(t.get('t'), 2)}, permutation p = {f(t.get('p_permutation'), 3)}; McNemar on simulated "
                      f"replies p = {f(d['mcnemar_on_replies'].get('p'), 3)}."])


SECTIONS = {"headline": headline_table, "rag": rag_table, "ablation": ablation_table, "decisions": decisions_table,
            "injection": injection_table, "multiagent": multiagent_table, "tools": tools_table, "ab": ab_table}


def main() -> int:
    out = []
    for name, fn in SECTIONS.items():
        out.append(f"### {name}\n\n{fn()}\n")
    (RES / "tables.md").write_text("\n".join(out), encoding="utf-8")
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        for name, fn in SECTIONS.items():
            text = re.sub(rf"(<!-- results:start {name} -->\n)(.*?)(\n<!-- results:end -->)",
                          lambda m: m.group(1) + fn() + m.group(3), text, flags=re.S)
        readme.write_text(text, encoding="utf-8")
    print((RES / "tables.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
