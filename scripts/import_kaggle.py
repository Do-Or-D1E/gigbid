"""Import REAL Upwork data from public Kaggle datasets into GigBid (data/real/).

Sources (downloaded unmodified into ../kaggle_raw, never committed):
  A  asaniczka/upwork-job-postings-dataset-2024-50k-records   ODC-By 1.0     postings with description, budget, hourly range
  B  ahmedmyalo/upwork-freelance-jobs-60k                      Apache 2.0     postings with skills, level, applicants, client signals
  C  asaniczka/freelance-contracts-dataset-1-3-million-entries ODC-By 1.0     completed contracts: hourly rate, total paid
  D  sarveshchhetri/freelancer-success-earnings-and-churn-prediction (licence not stated on Kaggle) freelancer rates

Outputs (committed, small, every record tagged with `real: true`, `source` and `license`):
  data/real/price_calibration.json   per GigBid category: real fixed/hourly price percentiles + derived base prices
                                     (the synthetic generator reads the base prices, so synthetic markets follow real ones)
  data/real/upwork_postings.jsonl    a sample of real postings mapped to GigBid's Job schema (A and B)
  data/real/real_clients.json        clients for those postings: public history from B's real signals where present,
                                     hidden preferences SYNTHETIC (marked) because they cannot be observed
  data/real/freelancer_rates.json    aggregate rate statistics from C and D
  data/real/SOURCES.md               attribution and licences

Run:  uv run python scripts/import_kaggle.py --raw ../kaggle_raw
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import random
import re
import statistics
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "real"
csv.field_size_limit(10_000_000)

SOURCES = {
    "A": ("asaniczka/upwork-job-postings-dataset-2024-50k-records", "ODC-By-1.0",
          "https://www.kaggle.com/datasets/asaniczka/upwork-job-postings-dataset-2024-50k-records"),
    "B": ("ahmedmyalo/upwork-freelance-jobs-60k", "Apache-2.0",
          "https://www.kaggle.com/datasets/ahmedmyalo/upwork-freelance-jobs-60k"),
    "C": ("asaniczka/freelance-contracts-dataset-1-3-million-entries", "ODC-By-1.0",
          "https://www.kaggle.com/datasets/asaniczka/freelance-contracts-dataset-1-3-million-entries"),
    "D": ("sarveshchhetri/freelancer-success-earnings-and-churn-prediction", "not stated",
          "https://www.kaggle.com/datasets/sarveshchhetri/freelancer-success-earnings-and-churn-prediction"),
}

# GigBid category -> keywords matched against title + skills + Upwork category (lower case, word-ish match)
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("LLM & RAG Applications", ["llm", "gpt", "chatgpt", "openai", "langchain", "rag ", "retrieval-augmented", "chatbot",
                                "ai agent", "ai assistant", "prompt engineering", "large language model", "vector database"]),
    ("Computer Vision & OCR", ["computer vision", "opencv", "ocr", "image recognition", "object detection", "yolo",
                               "image classification", "image processing"]),
    ("NLP & Text Analytics", ["nlp", "natural language", "sentiment analysis", "text classification", "text mining",
                              "named entity"]),
    ("Forecasting & Anomaly Detection", ["forecast", "time series", "anomaly detection", "demand prediction"]),
    ("MLOps & Deployment", ["mlops", "model deployment", "sagemaker", "mlflow", "kubeflow"]),
    ("ML Model Development", ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit", "neural network",
                              "predictive model", "classification model", "xgboost", "data science"]),
    ("Real-time & Payments Features", ["stripe", "payment gateway", "websocket", "socket.io", "real-time", "paypal integration"]),
    ("E-commerce Development", ["shopify", "woocommerce", "e-commerce", "ecommerce", "online store", "magento"]),
    ("Web Testing & QA", ["qa ", "quality assurance", "test automation", "selenium", "cypress", "playwright",
                          "automated testing", "manual testing"]),
    ("Cloud & DevOps Setup", ["devops", "aws", "docker", "kubernetes", "ci/cd", "terraform", "azure", "google cloud"]),
    ("API & Backend Development", ["api development", "rest api", "backend", "back-end", "node.js", "django", "fastapi",
                                   "flask", "graphql", "express"]),
    ("Web App Development", ["full stack", "full-stack", "fullstack", "react", "next.js", "nextjs", "vue", "angular",
                             "web application", "web app", "saas", "frontend", "front-end", "typescript"]),
    ("Business Intelligence & Dashboards", ["power bi", "tableau", "looker", "dashboard", "business intelligence",
                                            "data visualization", "metabase"]),
    ("Data Pipelines & ETL", ["etl", "data pipeline", "data engineering", "airflow", "dbt", "snowflake", "bigquery",
                              "data warehouse", "data migration"]),
    ("Statistical & Experiment Analysis", ["statistic", "a/b test", "regression analysis", "spss", "stata", "hypothesis",
                                           "r programming", "econometric"]),
    ("Marketing & Web Analytics", ["google analytics", "ga4", "google tag manager", "marketing analytics", "attribution",
                                   "mixpanel", "web analytics"]),
    ("Spreadsheet Automation", ["excel", "google sheets", "vba", "apps script", "spreadsheet", "macro"]),
    ("Survey & Research Analysis", ["survey", "market research", "questionnaire", "qualtrics"]),
    ("Mobile App Development", ["mobile app", "android", "ios", "flutter", "react native", "swift", "kotlin"]),
    ("WordPress & CMS", ["wordpress", "elementor", "webflow", "wix", "squarespace", "cms"]),
    ("Graphic & Brand Design", ["logo", "graphic design", "brand identity", "illustrat", "photoshop", "canva", "figma"]),
    ("Video & Motion", ["video edit", "motion graphic", "animation", "after effects", "premiere", "youtube video"]),
    ("Writing & Translation", ["writ", "translat", "copywrit", "proofread", "blog", "content"]),
    ("Game Development", ["unity", "unreal", "game develop", "roblox", "godot"]),
    ("SEO & Digital Marketing", ["seo", "social media", "facebook ads", "google ads", "media buyer", "email marketing",
                                "lead generation", "digital marketing"]),
    ("Admin & Bookkeeping", ["virtual assistant", "data entry", "bookkeep", "quickbooks", "accounting", "admin support"]),
    ("Blockchain & Web3", ["blockchain", "solidity", "smart contract", "web3", "nft", "crypto"]),
    ("Enterprise Software", ["salesforce", "sap ", "erp", "dynamics 365", "servicenow", "odoo"]),
]
IN_DOMAIN = {c for c, _ in CATEGORY_RULES[:18]}


def categorise(text: str) -> str | None:
    t = f" {text.lower()} "
    for cat, kws in CATEGORY_RULES:
        if any(k in t for k in kws):
            return cat
    return None


def money(s: str) -> float | None:
    s = (s or "").replace(",", "").replace("$", "").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    v = sorted(vals)
    return round(v[min(len(v) - 1, int(q * (len(v) - 1)))], 2)


def band(vals: list[float]) -> dict:
    return {"n": len(vals), "p25": pct(vals, 0.25), "p50": pct(vals, 0.5), "p75": pct(vals, 0.75)}


def open_csv(zpath: Path, member_suffix: str):
    zf = zipfile.ZipFile(zpath)
    name = next(n for n in zf.namelist() if n.endswith(member_suffix))
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace"))


def clean_a(desc: str) -> tuple[str, str, list[str], str | None]:
    """Source A embeds 'Budget/Hourly Range/Posted On/Category/Skills/Country' in the description."""
    d = html.unescape(desc).replace("\xa0", " ").replace("�", "'")
    cat = re.search(r"Category:\s*(.+?)(?:Skills:|Country:|click to apply|$)", d)
    skills = re.search(r"Skills:\s*(.+?)(?:Skills:|Country:|click to apply|$)", d)
    body = re.split(r"(?:Budget:|Hourly Range:|Posted On:)", d)[0].strip()
    skill_list = [s.strip() for s in (skills.group(1) if skills else "").split(",") if s.strip()][:10]
    return body, (cat.group(1).strip() if cat else ""), skill_list, None


def applicants(s: str) -> int | None:
    s = (s or "").lower()
    m = re.search(r"(\d+)\s*to\s*(\d+)", s)
    if m:
        return (int(m.group(1)) + int(m.group(2))) // 2
    if "less than 5" in s:
        return 3
    m = re.search(r"(\d+)\+", s)
    return int(m.group(1)) + 5 if m else None


def connects_v1(btype: str, bmax: float | None) -> int:
    if btype == "hourly":
        return 6
    if not bmax or bmax < 100:
        return 2
    return 4 if bmax < 500 else (6 if bmax < 1000 else 8)


def rid(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT.parent / "kaggle_raw"))
    ap.add_argument("--per-category", type=int, default=14)
    args = ap.parse_args(argv)
    raw = Path(args.raw)
    zips = {k: next(raw.glob(f"{v[0].replace('/', '_')}*.zip"), None) for k, v in SOURCES.items()}
    missing = [k for k, z in zips.items() if z is None]
    if missing:
        print("missing downloads:", missing, file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(4016)
    fixed: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    hourly: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    candidates: dict[str, list[dict]] = defaultdict(list)
    clients: dict[str, dict] = {}

    # ---------------- A: 2024 postings
    for row in open_csv(zips["A"], ".csv"):
        body, upcat, skills, _ = clean_a(row.get("description", ""))
        cat = categorise(f"{row['title']} {upcat} {' '.join(skills)}")
        if not cat:
            continue
        is_hourly = row.get("is_hourly") == "True"
        if is_hourly:
            lo, hi = money(row.get("hourly_low")), money(row.get("hourly_high"))
            if lo and hi and hi < 500:
                hourly[cat]["A"].append((lo + hi) / 2)
        else:
            b = money(row.get("budget"))
            if b and b < 100000:
                fixed[cat]["A"].append(b)
        if 250 <= len(body) <= 4000:
            lo, hi = (money(row.get("hourly_low")), money(row.get("hourly_high"))) if is_hourly else (None, money(row.get("budget")))
            if hi:
                candidates[cat].append({"src": "A", "title": row["title"].strip(), "description": body[:1600],
                                        "skills": skills, "budget_type": "hourly" if is_hourly else "fixed",
                                        "budget_min": lo, "budget_max": hi, "posted_at": row.get("published_date"),
                                        "country": row.get("country") or None, "url": row.get("link", "").split("?")[0]})

    # ---------------- B: 60k postings with client signals
    for row in open_csv(zips["B"], "Final_Upwork_Dataset.csv"):
        title = (row.get("﻿Job Title") or row.get("Job Title") or "").strip()
        skills = [row.get(f"Category_{i}", "").strip() for i in range(1, 10) if row.get(f"Category_{i}", "").strip()]
        cat = categorise(f"{title} {' '.join(skills)} {row.get('Search_Keyword', '')}")
        if not cat:
            continue
        ptype = (row.get("Payment_type") or "").lower()
        if "hourly" in ptype:
            lo, hi = money(row.get("Start_rate")), money(row.get("End_rate"))
            if lo and hi and hi < 500:
                hourly[cat]["B"].append((lo + hi) / 2)
        else:
            lo, hi = None, money(row.get("Job_Cost"))
            if hi and hi < 100000:
                fixed[cat]["B"].append(hi)
        desc = html.unescape(row.get("Description") or "").strip()
        if hi and 120 <= len(desc) <= 4000:
            spent = money(row.get("Spent($)"))
            cid = "real-cl-" + rid("B", title, row.get("Client_Country", ""), str(spent))
            candidates[cat].append({"src": "B", "title": title, "description": desc[:1600], "skills": skills,
                                    "budget_type": "hourly" if "hourly" in ptype else "fixed", "budget_min": lo,
                                    "budget_max": hi, "posted_at": None, "experience_level":
                                    (row.get("EX_level_demand") or "").lower() or None,
                                    "proposals_count": applicants(row.get("Applicants_Num", "")),
                                    "country": row.get("Client_Country") or None, "url": row.get("Job_URL", ""),
                                    "client": {"client_id": cid,
                                               "payment_verified": "verified" in (row.get("Payment_Situation") or "").lower()
                                               and "unverified" not in (row.get("Payment_Situation") or "").lower(),
                                               "total_spent_usd": spent or 0.0,
                                               "avg_rating_given": money(row.get("Rating")),
                                               "reviews_count": int(money(row.get("Feedback_Num")) or 0),
                                               "hires": int(money(row.get("Freelancers_Num")) or 0),
                                               "enterprise": bool((row.get("Enterprise_Client") or "").strip()),
                                               "country": row.get("Client_Country") or None}})

    # ---------------- C: completed contracts (aggregate only, never redistributed)
    contract_rates: dict[str, list[float]] = defaultdict(list)
    contract_paid: dict[str, list[float]] = defaultdict(list)
    seen = 0
    for row in open_csv(zips["C"], "contracts.csv"):
        seen += 1
        cat = categorise(row.get("job_title", ""))
        if not cat:
            continue
        r, paid = money(row.get("hourly_rate")), money(row.get("total_paid"))
        if r and r < 500 and len(contract_rates[cat]) < 30000:
            contract_rates[cat].append(r)
            hourly[cat]["C"].append(r)
        if paid and len(contract_paid[cat]) < 30000:
            contract_paid[cat].append(paid)

    # ---------------- D: freelancer rates by primary skill
    d_rates: dict[str, list[float]] = defaultdict(list)
    for row in open_csv(zips["D"], ".csv"):
        r = money(row.get("hourly_rate_usd"))
        if r:
            d_rates[row.get("primary_skill", "?")].append(r)

    # ---------------- price calibration (generator base prices)
    sys.path.insert(0, str(ROOT))
    from scripts.datagen import archetypes as AR  # noqa: E402

    dur_mean = sum(f * w for _, f, w in AR.DURATIONS) / 100.0
    calib = {"sources": {k: {"dataset": v[0], "license": v[1], "url": v[2]} for k, v in SOURCES.items()},
             "method": ("Fixed base = real p75 fixed budget / (mean duration factor x mean experience factor); the "
                        "real median is dominated by micro-tasks (p25 is $15-50) while GigBid's personas target "
                        "mid-size projects, so the upper quartile is the closer match for a 'typical' job. Hourly base "
                        "= real median hourly rate (postings + completed contracts) / mean experience factor. Used "
                        "only where n >= 40; other categories keep the hand-set base."), "categories": {}}
    for cat, (hand_fixed, hand_hourly) in AR.CATEGORY_PRICE_HAND.items():
        f_all = [v for s in fixed[cat].values() for v in s]
        h_post = [v for s in ("A", "B") for v in hourly[cat].get(s, [])]
        h_all = h_post + contract_rates[cat]
        base_f = round(pct(f_all, 0.75) / dur_mean / AR.EXP_MEAN) if len(f_all) >= 40 else hand_fixed
        base_h = round(statistics.median(h_all) / AR.EXP_MEAN) if len(h_all) >= 40 else hand_hourly
        calib["categories"][cat] = {
            "fixed_budgets": {s: band(v) for s, v in fixed[cat].items()} | {"all": band(f_all)},
            "hourly_rates": {"postings": band(h_post), "contracts": band(contract_rates[cat]), "all": band(h_all)},
            "contract_total_paid": band(contract_paid[cat]),
            "hand_set_base": [hand_fixed, hand_hourly], "calibrated_base": [base_f, base_h],
            "calibrated": [len(f_all) >= 40, len(h_all) >= 40],
        }
    (OUT / "price_calibration.json").write_text(json.dumps(calib, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    # ---------------- sample of real postings mapped to the Job schema
    postings, real_clients = [], []
    for cat in sorted(candidates):
        pool = sorted(candidates[cat], key=lambda c: rid(c["src"], c["title"], c["description"][:200]))
        quota = args.per_category if cat in IN_DOMAIN else max(3, args.per_category // 4)
        for c in pool[:quota]:
            jid = "real-" + rid(c["src"], c["title"], c["description"][:200])
            client = c.get("client")
            if client is None:
                client = {"client_id": "real-cl-" + rid("A", jid), "payment_verified": None, "total_spent_usd": None,
                          "avg_rating_given": None, "reviews_count": None, "hires": None, "country": c.get("country")}
            src = SOURCES[c["src"]]
            hidden_rng = random.Random(jid)
            req_skills = c["skills"][:4]
            real_clients.append({
                "client_id": client["client_id"], "name": f"Client {client['client_id'][-6:]}",
                "country": client.get("country"), "industry": None,
                "member_since": None, "payment_verified": bool(client.get("payment_verified")),
                "total_spent_usd": client.get("total_spent_usd") or 0.0, "hires": client.get("hires") or 0,
                "jobs_posted": max(1, (client.get("hires") or 0)), "avg_rating_given": client.get("avg_rating_given"),
                "reviews_from_freelancers": [],
                "hidden": {"must_have_skills": req_skills[:2], "budget_ceiling_usd": c["budget_max"],
                           "dislikes_generic_openings": hidden_rng.random() < 0.6, "prefers_short": hidden_rng.random() < 0.45,
                           "responsiveness": round(hidden_rng.uniform(0.5, 0.95), 2), "is_scammer": False,
                           "synthetic": True},
                "real": True, "public_history_source": src[0] if c["src"] == "B" else None,
            })
            postings.append({
                "job_id": jid, "title": c["title"][:140], "description": c["description"], "category": cat,
                "skills": c["skills"][:10], "budget_type": c["budget_type"], "budget_min": c["budget_min"],
                "budget_max": c["budget_max"], "duration": None, "experience_level": c.get("experience_level"),
                "screening_questions": [], "client_id": client["client_id"], "posted_at": c.get("posted_at"),
                "proposals_count": c.get("proposals_count") or 0, "connects_cost": connects_v1(c["budget_type"], c["budget_max"]),
                "featured": False, "real": True, "source": src[0], "license": src[1], "source_url": c.get("url"),
            })
    rng.shuffle(postings)
    with open(OUT / "upwork_postings.jsonl", "w", encoding="utf-8") as fh:
        for p in sorted(postings, key=lambda p: p["job_id"]):
            fh.write(json.dumps(p, ensure_ascii=True, sort_keys=True) + "\n")
    uniq = {c["client_id"]: c for c in real_clients}
    (OUT / "real_clients.json").write_text(json.dumps(sorted(uniq.values(), key=lambda c: c["client_id"]), indent=1,
                                                      sort_keys=True) + "\n", encoding="utf-8")

    rates = {"contracts_rows_scanned": seen,
             "contracts_hourly_by_category": {k: band(v) for k, v in sorted(contract_rates.items())},
             "freelancer_rates_by_primary_skill_D": {k: band(v) for k, v in sorted(d_rates.items())},
             "note_D": "Dataset D does not state its licence or collection method; it is used only as a rough rate sanity check."}
    (OUT / "freelancer_rates.json").write_text(json.dumps(rates, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    lines = ["# Real data sources", "",
             "Every record derived from these datasets carries `real: true`, `source` and `license` fields.",
             "Raw downloads are not committed; only the processed sample and aggregate statistics are.", ""]
    for k, (name, lic, url) in SOURCES.items():
        lines.append(f"- **{k}** [{name}]({url}), licence: {lic}")
    lines += ["", "ODC-By requires attribution: data from A and C is (c) its Kaggle publisher, used under the Open Data "
              "Commons Attribution License v1.0. B is used under the Apache License 2.0 (NOTICE: original dataset by "
              "ahmedmyalo on Kaggle)."]
    (OUT / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"postings": len(postings), "clients": len(uniq), "contracts_scanned": seen,
                      "calibrated": sum(all(v["calibrated"]) for v in calib["categories"].values())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
