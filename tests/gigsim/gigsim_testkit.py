"""Shared helpers for GigSim tests (imported as `gigsim_testkit`)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from gigsim.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
ADMIN = "gigsim-admin-test"
TOKENS = {"ai_ml": "gs-ai_ml-dev", "fullstack": "gs-fullstack-dev", "data_analyst": "gs-data_analyst-dev"}

COVER_STRONG = (
    "Hi Acme Analytics, I read your PyTorch model training pipeline post closely. I built a PyTorch pipeline "
    "for a retail client that cut training time by 40% and shipped it with Python tooling and CI. "
    "I can start this week and deliver a first milestone in 5 days."
)
COVER_PLAIN = (
    "Hello, I can help with this job. I have worked on similar tasks before and I am available to start "
    "soon, so please let me know if you want to talk about the details of the work."
)


def make_settings(uri: str, **kw) -> Settings:
    base = dict(
        database_url=uri, admin_token=ADMIN, rate_limit_per_min=10_000, error_rate=0.0, time_scale=0.0,
        policy_version="1", client_mode="heuristic", seed_dir=FIXTURES / "seed", data_dir=FIXTURES / "data",
    )
    base.update(kw)
    return Settings(**base)


class Api:
    def __init__(self, client: TestClient):
        self.c = client

    @staticmethod
    def headers(who: str | None, key: str | None = None) -> dict:
        h = {}
        if who == "admin":
            h["Authorization"] = f"Bearer {ADMIN}"
        elif who:
            h["Authorization"] = f"Bearer {TOKENS.get(who, who)}"
        if key:
            h["Idempotency-Key"] = key
        return h

    def get(self, path, who="ai_ml", **params):
        return self.c.get(path, headers=self.headers(who), params=params or None)

    def post(self, path, json=None, who="ai_ml", key="auto"):
        if key == "auto":
            key = None if who == "admin" else uuid.uuid4().hex
        return self.c.post(path, json=json if json is not None else {}, headers=self.headers(who, key))

    # admin helpers
    def admin(self, path, json=None):
        return self.post(path, json, who="admin", key=None)

    def config(self, **kw):
        r = self.admin("/v1/admin/config", kw)
        assert r.status_code == 200, r.text
        return r.json()

    def advance(self, hours):
        r = self.admin("/v1/admin/clock/advance", {"hours": hours})
        assert r.status_code == 200, r.text
        return r.json()

    def draft(self, job_id, who="ai_ml", cover=COVER_STRONG, bid=600, bid_type="fixed", key="auto"):
        return self.post(
            "/v1/proposals",
            {"job_id": job_id, "cover_letter": cover, "screening_answers": ["I have 5 years of experience."],
             "bid_amount": bid, "bid_type": bid_type},
            who=who, key=key,
        )

    def submit(self, proposal_id, who="ai_ml", key="auto"):
        return self.post(f"/v1/proposals/{proposal_id}/submit", {}, who=who, key=key)

    def submit_new(self, job_id, who="ai_ml", **kw):
        d = self.draft(job_id, who=who, **kw)
        assert d.status_code == 201, d.text
        s = self.submit(d.json()["proposal_id"], who=who)
        assert s.status_code == 200, s.text
        return s.json()

    def decision(self, proposal_id):
        r = self.get(f"/v1/admin/proposals/{proposal_id}/decision", who="admin")
        assert r.status_code == 200, r.text
        return r.json()["decision"]

    def balance(self, who="ai_ml"):
        return self.get("/v1/me/connects", who=who).json()["balance"]
