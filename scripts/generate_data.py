#!/usr/bin/env python
"""Deterministic, offline generator for the GigBid synthetic dataset (no LLM calls, no network).

Usage (from the repo root):
    uv run python scripts/generate_data.py                      # everything, seed 4016
    uv run python scripts/generate_data.py --seed 4016          # same
    uv run python scripts/generate_data.py --holdout --seed 777 --out evals/holdout
See docs/DATA_CONTRACT.md for the output schema.
"""
from __future__ import annotations

import argparse
import collections
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.datagen import jobs as J  # noqa: E402
from scripts.datagen import personas as PS  # noqa: E402
from scripts.datagen import policy as POL  # noqa: E402
from scripts.datagen.render_pdf import render_cv_pdf  # noqa: E402
from scripts.datagen.taxonomy import build_taxonomy  # noqa: E402
from scripts.datagen.util import write_json, write_jsonl, write_text  # noqa: E402

PIDS = J.PIDS
DEFAULT_SEED = 4016


def _write_persona(root: Path, P: dict, with_pdf: bool) -> None:
    pid = P["pid"]
    base = root / "data" / "personas" / pid
    prof = P["profile"]
    keys = ["persona_id", "name", "headline", "skills", "hourly_rate_usd", "min_project_usd", "weekly_connects_budget",
            "timezone", "availability_hours"]
    write_json(base / "profile.json", {k: prof[k] for k in keys})
    write_text(base / "cv.md", P["cv_md"])
    if with_pdf:
        (base).mkdir(parents=True, exist_ok=True)
        render_cv_pdf(P["cv_md"], base / "cv.pdf")
    for c in P["case_studies"]:
        write_text(base / "case_studies" / f"{c['item_id']}.md", PS.case_study_md(P, c))
    for r in P["repos"]:
        rb = base / "repos" / r["slug"]
        write_text(rb / "README.md", r["readme"])
        write_json(rb / "meta.json", dict(item_id=r["item_id"], project_id=r["project_id"], slug=r["slug"], date=r["date"],
                                          language=r["language"]))
        for fname, text in r["files"].items():
            write_text(rb / "src" / fname, text)
    write_jsonl(base / "reviews.jsonl", [{k: v for k, v in r.items() if k != "skills"} for r in P["reviews"]])
    write_jsonl(base / "proposals.jsonl", [{k: v for k, v in p.items() if not k.startswith("_")} for p in P["proposals"]])
    write_json(base / "gold" / "projects.json", P["gold_projects"])
    write_json(base / "gold" / "items.json", P["gold_items"])


def build_personas(seed: int) -> dict:
    return {pid: PS.build_persona(pid, seed) for pid in PIDS}


def _merge_real(stream: list, clients: list) -> tuple[list, list]:
    """Append REAL Upwork postings (data/real, from scripts/import_kaggle.py) to GigSim's live stream.
    They carry real: true plus source/license fields; their clients' hidden preferences are synthetic."""
    import hashlib
    import json as _json

    repo = Path(__file__).resolve().parents[1]
    jobs_path, clients_path = repo / "data" / "real" / "upwork_postings.jsonl", repo / "data" / "real" / "real_clients.json"
    if not jobs_path.exists() or not clients_path.exists():
        return stream, clients
    real = sorted((_json.loads(line) for line in jobs_path.read_text(encoding="utf-8").split("\n") if line.strip()),
                  key=lambda j: j["job_id"])
    out = list(stream)
    for i, job in enumerate(real):
        job = dict(job)
        job["release_order"] = len(stream) + i
        job["dup_of"] = None
        job["release_at_offset_hours"] = round((int(hashlib.sha256(job["job_id"].encode()).hexdigest()[:6], 16) % 33600) / 100, 2)
        job["posted_at"] = job.get("posted_at") or "2026-11-01T09:00:00Z"
        out.append(job)
    known = {c["client_id"] for c in clients}
    extra = [c for c in _json.loads(clients_path.read_text(encoding="utf-8")) if c["client_id"] not in known]
    return out, list(clients) + extra


def build_all(out_root, seed: int = DEFAULT_SEED, with_pdf: bool = True) -> dict:
    """Write the complete dataset under out_root (same relative layout as the repo)."""
    root = Path(out_root)
    personas = build_personas(seed)
    taxonomy = build_taxonomy({pid: set(personas[pid]["skills"]) for pid in PIDS})
    write_json(root / "data" / "taxonomy.json", taxonomy)
    for pid in PIDS:
        _write_persona(root, personas[pid], with_pdf)

    W = J.build_world(personas, seed)
    reg = W.registry
    write_jsonl(root / "data" / "jobs" / "historical.jsonl", W.hist)
    dev = {}
    for pid in PIDS:
        dev[pid] = J.build_dev(W, pid, seed, reg)
        write_jsonl(root / "evals" / "datasets" / f"dev_{pid}.jsonl", dev[pid])
    stream = J.build_stream(W, seed, reg)
    clients = reg.export()
    stream, clients = _merge_real(stream, clients)
    write_jsonl(root / "gigsim" / "seed" / "stream_jobs.jsonl", stream)
    write_json(root / "gigsim" / "seed" / "clients.json", clients)

    for name, text in (("policy_v1.md", POL.policy_v1_md()), ("policy_v2.md", POL.policy_v2_md()),
                       ("policy_v1.yaml", POL.policy_v1_yaml()), ("policy_v2.yaml", POL.policy_v2_yaml())):
        write_text(root / "data" / "policy_pack" / name, text)

    stats = make_stats(personas, W, dev, stream, clients)
    write_json(root / "data" / "STATS.json", stats)
    return stats


def build_holdout(out_dir, seed: int, persona_seed: int = DEFAULT_SEED) -> dict:
    """Fresh dev-style job sets (and their clients) for a hidden-test stand-in.

    Personas, taxonomy and historical prices stay those of persona_seed so the gold labels refer to the real portfolio items.
    """
    out = Path(out_dir)
    personas = build_personas(persona_seed)
    W = J.build_world(personas, persona_seed)
    reg = J.Registry(random.Random(f"{seed}:holdout-clients"), "hcl")
    reg.make_pool(80, J.dt.date(2026, 1, 1))
    reg.finalize({})
    counts = {}
    for pid in PIDS:
        rows = J.build_dev(W, pid, seed, reg, prefix="hold")
        write_jsonl(out / f"dev_{pid}.jsonl", rows)
        counts[pid] = len(rows)
    write_json(out / "clients.json", reg.export())
    return counts


def make_stats(personas, W, dev, stream, clients) -> dict:
    st = {"seed_note": "generated by scripts/generate_data.py", "personas": {}, "dev": {}, "historical": {}, "stream": {},
          "clients": {"total": len(clients)}}
    for pid in PIDS:
        P = personas[pid]
        by_type = collections.Counter(v["type"] for v in P["gold_items"].values())
        st["personas"][pid] = dict(
            projects=len(P["projects"]), skills=len(P["skills"]), items_by_type=dict(sorted(by_type.items())),
            proposals_by_outcome=dict(sorted(collections.Counter(p["outcome"] for p in P["proposals"]).items())),
            reviews_by_rating={str(k): v for k, v in sorted(collections.Counter(r["rating"] for r in P["reviews"]).items())})
        rows = dev[pid]
        tags = collections.Counter(t for r in rows for t in r["gold"]["job_type"])
        st["dev"][pid] = dict(
            n=len(rows), by_action=dict(sorted(collections.Counter(r["gold"]["action"] for r in rows).items())),
            by_job_type=dict(sorted(tags.items())),
            scams=sum(1 for r in rows if r["gold"]["is_scam"]), injections=sum(1 for r in rows if r["gold"]["has_injection"]),
            injection_goals=dict(sorted(collections.Counter(r["gold"]["injection_goal"] for r in rows
                                                            if r["gold"]["has_injection"]).items())),
            duplicates=sum(1 for r in rows if r["gold"]["dup_of"]))
    st["historical"] = dict(total=len(W.hist),
                            by_category=dict(sorted(collections.Counter(r["category"] for r in W.hist).items())),
                            by_budget_type=dict(sorted(collections.Counter(r["budget_type"] for r in W.hist).items())))
    st["stream"] = dict(total=len(stream), duplicates=sum(1 for r in stream if r["dup_of"]),
                        by_category=dict(sorted(collections.Counter(r["category"] for r in stream).items())))
    return st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--holdout", action="store_true", help="write only fresh dev-style job sets and clients")
    ap.add_argument("--out", default=None, help="output directory (default: repo root, or evals/holdout with --holdout)")
    ap.add_argument("--persona-seed", type=int, default=DEFAULT_SEED,
                    help="with --holdout: seed of the persona portfolio the jobs are labelled against")
    a = ap.parse_args(argv)
    if a.holdout:
        out = Path(a.out) if a.out else REPO / "evals" / "holdout"
        if not out.is_absolute():
            out = REPO / out
        counts = build_holdout(out, a.seed, a.persona_seed)
        print(f"holdout written to {out}: {counts}")
        return 0
    out = Path(a.out) if a.out else REPO
    stats = build_all(out, a.seed)
    print(f"wrote dataset to {out}")
    for pid in PIDS:
        print(pid, stats["personas"][pid]["items_by_type"], "dev:", stats["dev"][pid]["n"])
    print("historical:", stats["historical"]["total"], "stream:", stats["stream"]["total"], "clients:", stats["clients"]["total"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
