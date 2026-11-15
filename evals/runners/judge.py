"""Rubric LLM judge and its calibration against human labels (R&D B, proposal quality).

    uv run python -m evals.runners.judge score --files decisions_main_per_job.jsonl decisions_v0_per_job.jsonl
    uv run python -m evals.runners.judge sheet          # 30 anonymised proposals for human labelling
    uv run python -m evals.runners.judge kappa          # needs evals/datasets/judge_labels_human.csv

The human labels must come from the student (open evals/label_tool.html in a browser, label,
save the CSV into evals/datasets/). The judge is only reported as calibrated once kappa exists.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random

from pydantic import BaseModel, Field

from evals.runners import harness as H
from evals.runners.metrics import cohen_kappa, mean


class Score(BaseModel):
    specificity: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    personalisation: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    honesty: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)
    rationale: str = ""


def load(name: str) -> list[dict]:
    p = H.RESULTS / name
    return [json.loads(line) for line in p.read_text(encoding="utf-8").split("\n") if line.strip()]


def jobs_index() -> dict[str, dict]:
    out = {}
    for p in H.PERSONAS:
        for r in H.load_dev(p):
            out[r["job"]["job_id"]] = r["job"]
    return out


async def judge_one(job: dict, letter: str, answers) -> Score:
    from agent import llm
    from agent.guardrails import untrusted
    from agent.prompts import load_prompt

    user = (untrusted("job_post", f"{job['title']}\n{job['description']}") + "\n\n<proposal>\n" + letter +
            "\n\nScreening answers: " + json.dumps(answers or []) + "\n</proposal>")
    out, _ = await llm.call("judge", load_prompt("judge"), user, Score, temperature=0)
    return out


async def score(files: list[str]) -> None:
    jobs = jobs_index()
    for f in files:
        rows = load(f)
        sem = asyncio.Semaphore(6)

        async def one(r):
            if not r.get("cover_letter"):
                return r
            async with sem:
                s = await judge_one(jobs[r["job_id"]], r["cover_letter"], r.get("screening_answers"))
            return {**r, "judge": s.model_dump()}
        scored = await asyncio.gather(*(one(r) for r in rows))
        H.write_result(f.replace("_per_job.jsonl", "_judged.jsonl"), scored)
        vals = [r["judge"]["overall"] for r in scored if r.get("judge")]
        summ = {"file": f, "n": len(vals), "judge_overall_mean": mean(vals),
                "criteria_means": {k: mean(r["judge"][k] for r in scored if r.get("judge"))
                                   for k in ("specificity", "relevance", "personalisation", "clarity", "honesty")}}
        H.write_result(f.replace("_per_job.jsonl", "_judge_summary.json"), summ)
        print(json.dumps(summ))


def sheet(n: int = 30) -> None:
    jobs = jobs_index()
    pool = []
    for f in sorted(H.RESULTS.glob("decisions_*_per_job.jsonl")):
        pool += [r for r in load(f.name) if r.get("cover_letter")]
    random.Random(4016).shuffle(pool)
    items = []
    for i, r in enumerate(pool[:n]):
        j = jobs[r["job_id"]]
        items.append({"item": f"P{i + 1:02d}", "job_id": r["job_id"], "job_title": j["title"],
                      "job_description": j["description"][:1500], "proposal": r["cover_letter"],
                      "screening_answers": r.get("screening_answers") or []})
    (H.ROOT / "evals" / "datasets" / "judge_calibration_items.json").write_text(json.dumps(items, indent=1),
                                                                                encoding="utf-8")
    print(f"wrote {len(items)} items; open evals/label_tool.html and load evals/datasets/judge_calibration_items.json")


async def kappa() -> None:
    path = H.ROOT / "evals" / "datasets" / "judge_labels_human.csv"
    items = json.loads((H.ROOT / "evals" / "datasets" / "judge_calibration_items.json").read_text(encoding="utf-8"))
    human = {row["item"]: int(row["overall"]) for row in csv.DictReader(path.open(encoding="utf-8"))}
    jobs = jobs_index()
    pairs = []
    for it in items:
        if it["item"] not in human:
            continue
        s = await judge_one(jobs[it["job_id"]], it["proposal"], it["screening_answers"])
        pairs.append({"item": it["item"], "human": human[it["item"]], "judge": s.overall, "judge_rationale": s.rationale})
    def band(x: int) -> str:
        return "poor" if x <= 2 else ("ok" if x == 3 else "good")
    res = {"n": len(pairs), "kappa_exact_1to5": cohen_kappa([p["human"] for p in pairs], [p["judge"] for p in pairs]),
           "kappa_banded_3class": cohen_kappa([band(p["human"]) for p in pairs], [band(p["judge"]) for p in pairs]),
           "exact_agreement": round(sum(p["human"] == p["judge"] for p in pairs) / max(1, len(pairs)), 3),
           "disagreements": [p for p in pairs if abs(p["human"] - p["judge"]) >= 2], "pairs": pairs}
    H.write_result("judge_calibration.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "pairs"}, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "sheet", "kappa"])
    ap.add_argument("--files", nargs="*", default=["decisions_main_per_job.jsonl"])
    ap.add_argument("--profile", default=None)
    args = ap.parse_args(argv)
    H.setup_env(cache=True, profile=args.profile)
    if args.cmd == "score":
        H.run(score(args.files))
    elif args.cmd == "sheet":
        sheet()
    else:
        H.run(kappa())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
