"""The 2 Nov "platform policy update" (change request), measured.

GigSim policy v2 adds (a) +50% Connects for jobs with >= 15 proposals and (b) rejects proposals
with links other than github.com. GigBid absorbs it through configuration only:
  * Pricing already reads the live, policy-aware Connects quote from the marketplace port;
  * the Compliance Guard reads the active policy pack (policy.version: 2 -> policy_v2.yaml).
This runner shows the effect on the same jobs and the same draft under v1 and v2, with no LLM:
Connects quotes, the deterministic compliance check, and GigSim's accept or reject on submit.

    uv run python -m evals.runners.change_request
"""
from __future__ import annotations

import json
import uuid

import httpx

from evals.runners import harness as H

LETTER = ("Your churn model needs a reproducible baseline and honest evaluation. I built a gradient boosting "
          "churn pipeline for a subscription client and documented precision and recall per segment. The code is at "
          "https://github.com/example/churn-baseline and a short write-up is at https://example-portfolio.dev/churn. "
          "I would start by auditing the labels and the leakage risks in your data.")
HDR = {"Authorization": "Bearer gs-ai_ml-dev"}


async def submit(job_id: str, text: str) -> dict:
    from gigsim.app import app as gs

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gs), base_url="http://g") as c:
        d = await c.post("/v1/proposals", headers={**HDR, "Idempotency-Key": uuid.uuid4().hex},
                         json={"job_id": job_id, "cover_letter": text, "bid_amount": 500, "bid_type": "fixed",
                               "screening_answers": []})
        if d.status_code >= 300:
            return {"status": d.status_code, **d.json()}
        s = await c.post(f"/v1/proposals/{d.json()['proposal_id']}/submit",
                         headers={**HDR, "Idempotency-Key": uuid.uuid4().hex}, json={})
        body = s.json()
        return {"status": s.status_code, "error": body.get("error"), "rule": body.get("rule"),
                "connects_spent": body.get("connects_spent")}


async def main_async() -> dict:
    from agent import policy
    from agent.nodes.compliance import scrub

    rows = [r for p in H.PERSONAS for r in H.load_dev(p) if not r["gold"].get("dup_of")]
    busy = [r for r in rows if (r["job"].get("proposals_count") or 0) >= 15][:6]
    calm = [r for r in rows if (r["job"].get("proposals_count") or 0) < 15 and r["job"]["budget_type"] == "fixed"][:4]
    out: dict = {"quotes": [], "compliance": {}, "gigsim_submit": {}}
    async with H.Stack() as st:
        await st.load_jobs(busy + calm)
        for i, version in enumerate((1, 2)):
            await st.gigsim("POST", "/admin/config", json={"policy_version": str(version)})
            await st.gigsim("POST", "/admin/clock/advance", json={"hours": 170})  # fresh weekly Connects
            for r in busy:
                q = await st.gigsim("GET", "/connects/quote", token="gs-ai_ml-dev", params={"job_id": r["job"]["job_id"]})
                out["quotes"].append({"policy": version, "job_id": r["job"]["job_id"],
                                      "proposals_count": r["job"].get("proposals_count"), "connects": q.get("cost")})
            found = policy.check(LETTER, version=version)
            out["compliance"][f"v{version}"] = found
            policy.load.cache_clear()
            out["gigsim_submit"][f"v{version}_raw_letter"] = await submit(calm[2 * i]["job"]["job_id"], LETTER)
            # What GigBid would actually send: the letter after the Compliance Guard's scrub for this version.
            from agent import settings

            settings.config()["policy"]["version"] = version
            cleaned, _ = scrub(LETTER)
            out["gigsim_submit"][f"v{version}_after_guard"] = await submit(calm[2 * i + 1]["job"]["job_id"], cleaned)
    for v in (1, 2):
        qs = [q["connects"] for q in out["quotes"] if q["policy"] == v]
        out[f"mean_connects_on_busy_jobs_v{v}"] = round(sum(qs) / max(1, len(qs)), 2)
    return out


def main() -> int:
    H.setup_env(cache=True)
    res = H.run(main_async())
    H.write_result("change_request.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "quotes"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
