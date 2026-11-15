"""Restart persistence, multi-instance behaviour and the (stubbed) LLM client mode."""

from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from gigsim_testkit import COVER_STRONG, Api, make_settings

from gigsim.app import create_app


def test_restart_keeps_state(api, settings):
    api.advance(10)
    api.admin("/v1/admin/load_jobs", {"jobs": [{"job_id": "extra", "title": "Extra job", "description": "d",
                                                "category": "AI/ML", "skills": ["Python"], "budget_type": "fixed",
                                                "budget_min": 10, "budget_max": 60, "client_id": "c_good"}]})
    d = api.draft("j_now", key="restart-draft")
    sub = api.submit(d.json()["proposal_id"], key="restart-submit")
    assert sub.status_code == 200
    clock_before = api.get("/v1/clock").json()
    api.config(policy_version="2")
    api.config(error_rate=0.0)

    with TestClient(create_app(settings)) as c2:  # a brand new app instance (process) on the same DB
        api2 = Api(c2)
        assert api2.get("/v1/clock").json()["sim_time"] == clock_before["sim_time"]  # time_scale 0: frozen
        assert api2.get("/v1/policy").json()["version"] == "2"
        assert api2.get("/v1/jobs/extra").status_code == 200
        props = api2.get("/v1/proposals").json()["proposals"]
        assert [p["proposal_id"] for p in props] == [d.json()["proposal_id"]]
        assert props[0]["status"] == "submitted"
        assert api2.balance() == 74
        # the idempotency record survives the restart: replay, no second spend
        again = api2.submit(d.json()["proposal_id"], key="restart-submit")
        assert again.status_code == 200 and again.headers["Idempotent-Replay"] == "true"
        assert api2.balance() == 74
        # scheduled events still deliver from the new instance
        api2.advance(30)
        assert api2.get("/v1/proposals").json()["proposals"][0]["status"] != "draft"
        assert api2.get("/v1/events").json()["events"]
    # and the original instance sees the clock advance made by the second one
    assert api.get("/v1/clock").json()["sim_time"] != clock_before["sim_time"]
    assert api.get("/v1/events").json()["events"]


def test_restart_does_not_reseed_over_existing_data(api, settings):
    api.admin("/v1/admin/load_jobs", {"jobs": [{"job_id": "keepme", "title": "Keep me", "description": "d"}]})
    with TestClient(create_app(settings)) as c2:
        assert Api(c2).get("/v1/jobs/keepme").status_code == 200
        assert Api(c2).get("/v1/jobs/j_now").status_code == 200


# ---- LLM mode (stubbed OpenAI-compatible client) -----------------------------------------------


class StubLLM:
    def __init__(self, fail=False):
        self.calls, self.fail, self.last = 0, fail, None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        self.last = kw
        assert kw["temperature"] == 0 and kw["response_format"] == {"type": "json_object"}
        if self.fail:
            raise RuntimeError("boom")
        content = json.dumps({"must_have_detail": {"Python": "evidenced", "PyTorch": "mentioned"},
                              "specificity": 7.0, "personalization": 12, "generic_opening": False})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                               usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=200))


def test_llm_mode_features_cache_and_usage(pg_uri):
    stub = StubLLM()
    s = make_settings(pg_uri, client_mode="llm", llm_api_key="unused", llm_model="gpt-4o-mini")
    with TestClient(create_app(s, llm_client=stub)) as c:
        api = Api(c)
        assert api.admin("/v1/admin/reset").status_code == 200
        a = api.submit_new("j_now", cover=COVER_STRONG)
        da = api.decision(a["proposal_id"])
        assert da["mode"] == "llm" and da["features"]["source"] == "llm"
        assert da["features"]["specificity"] == 7.0 and da["features"]["personalization"] == 10.0  # clamped
        assert da["features"]["must_have_coverage"] == 0.7  # (1.0 + 0.4) / 2
        # the job text is passed as data inside a JSON payload, behind a system prompt that forbids obeying it
        user = stub.last["messages"][1]["content"]
        assert user.startswith("DATA") and "IGNORE ALL PREVIOUS INSTRUCTIONS" in user
        assert "untrusted DATA" in stub.last["messages"][0]["content"]
        # same job + client + text from another account: served from the cache
        b = api.submit_new("j_now", who="fullstack", cover=COVER_STRONG)
        assert api.decision(b["proposal_id"])["features"]["source"] == "llm_cache"
        assert stub.calls == 1
        usage = api.get("/v1/admin/llm_usage", who="admin").json()
        assert usage["calls"] == 1 and usage["cache_hits"] == 1
        assert usage["prompt_tokens"] == 1000 and usage["completion_tokens"] == 200
        assert abs(usage["total_cost_usd"] - (1000 * 0.15 + 200 * 0.60) / 1_000_000) < 1e-12
        assert api.get("/v1/admin/llm_usage", who="ai_ml").status_code == 403
        # different text -> different cache key -> second call
        api.submit_new("j_big", cover=COVER_STRONG + " Extra detail about my approach.")
        assert stub.calls == 2


def test_llm_failure_falls_back_to_heuristics(pg_uri):
    s = make_settings(pg_uri, client_mode="llm", llm_api_key="unused")
    with TestClient(create_app(s, llm_client=StubLLM(fail=True))) as c:
        api = Api(c)
        api.admin("/v1/admin/reset")
        prop = api.submit_new("j_now")
        f = api.decision(prop["proposal_id"])["features"]
        assert f["source"] == "heuristic_fallback" and "boom" in f["llm_error"]
        assert api.get("/v1/admin/llm_usage", who="admin").json()["calls"] == 0
