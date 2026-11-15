"""GigSim API tests (embedded Postgres, heuristic client mode, frozen simulated clock)."""

from __future__ import annotations

import pytest

from gigsim_testkit import COVER_PLAIN, COVER_STRONG


def load_cheap_jobs(api, n, client_id="c_good", title="PyTorch model training pipeline"):
    jobs = [
        {"job_id": f"jc_{i:03d}", "title": f"{title} {i}", "description": f"Need {title}.",
         "category": "AI/ML", "skills": ["Python", "PyTorch"], "budget_type": "fixed", "budget_min": 20,
         "budget_max": 50, "client_id": client_id, "posted_at": "2026-10-30T10:00:00Z", "proposals_count": 1,
         "screening_questions": [], "featured": False}
        for i in range(n)
    ]
    r = api.admin("/v1/admin/load_jobs", {"jobs": jobs})
    assert r.status_code == 200, r.text
    return [j["job_id"] for j in jobs]


def find_proposal(api, stages, n=40, **kw):
    """Submit proposals on cheap jobs (2 Connects each) until one lands in one of `stages`."""
    api.config(rate_limit_per_min=0)
    for job_id in load_cheap_jobs(api, n, **kw):
        prop = api.submit_new(job_id)
        dec = api.decision(prop["proposal_id"])
        if dec["stage"] in stages:
            return prop, dec
    pytest.fail(f"no proposal reached stages {stages} in {n} tries")


# ---------------------------------------------------------------------------------------------
# health / auth / rate limit / errors
# ---------------------------------------------------------------------------------------------


def test_health_needs_no_auth(api):
    r = api.get("/v1/health", who=None)
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_auth(api):
    assert api.get("/v1/policy", who=None).status_code == 401
    assert api.get("/v1/policy", who="not-a-token").status_code == 401
    assert api.get("/v1/policy", who="ai_ml").status_code == 200
    assert api.get("/v1/policy", who="admin").status_code == 200
    # admin endpoints
    assert api.get("/v1/admin/llm_usage", who=None).status_code == 401
    assert api.get("/v1/admin/llm_usage", who="ai_ml").status_code == 403
    assert api.get("/v1/admin/llm_usage", who="admin").status_code == 200
    # freelancer-only endpoint with the admin token
    assert api.get("/v1/me/connects", who="admin").status_code == 403
    for who in ("ai_ml", "fullstack", "data_analyst"):
        assert api.get("/v1/me", who=who).json()["account_id"] == who


def test_rate_limit_429(api):
    api.config(rate_limit_per_min=3)
    for _ in range(3):
        assert api.get("/v1/policy").status_code == 200
    r = api.get("/v1/policy")
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limited" and body["retry_after"] >= 1
    assert int(r.headers["Retry-After"]) == body["retry_after"]
    assert api.get("/v1/policy", who="fullstack").status_code == 200  # per-token window
    assert api.get("/v1/policy", who="admin").status_code == 200  # admin exempt
    assert api.get("/v1/admin/llm_usage", who="admin").status_code == 200


def test_error_injection_forced_and_deterministic(api):
    api.config(error_rate=1.0)
    r = api.get("/v1/policy")
    assert r.status_code == 503 and r.json() == {"error": "upstream_unavailable"}
    assert api.get("/v1/admin/llm_usage", who="admin").status_code == 200  # admin never injected
    api.config(error_rate=0.0)
    assert api.get("/v1/policy").status_code == 200

    def run():
        api.admin("/v1/admin/reset")
        api.config(error_rate=0.5)
        return [api.get("/v1/policy").status_code for _ in range(30)]

    first, second = run(), run()
    assert first == second
    assert 503 in first and 200 in first


# ---------------------------------------------------------------------------------------------
# jobs, clients, stats
# ---------------------------------------------------------------------------------------------


def test_job_visibility_follows_sim_clock(api):
    ids = {j["job_id"] for j in api.get("/v1/jobs", limit=100).json()["jobs"]}
    assert "j_now" in ids and "j_later" not in ids
    assert api.get("/v1/jobs/j_later").status_code == 404
    api.advance(47)
    assert api.get("/v1/jobs/j_later").status_code == 404
    api.advance(2)
    assert api.get("/v1/jobs/j_later").status_code == 200
    ids = {j["job_id"] for j in api.get("/v1/jobs", limit=100).json()["jobs"]}
    assert "j_later" in ids


def test_job_detail_is_verbatim_and_hides_labels(api):
    job = api.get("/v1/jobs/j_now").json()
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in job["description"]
    for hidden in ("dup_of", "release_order", "release_at_offset_hours"):
        assert hidden not in job
    assert job["client_id"] == "c_good" and job["budget_type"] == "fixed"


def test_job_search_filters(api):
    r = api.get("/v1/jobs", query="pytorch").json()
    assert {j["job_id"] for j in r["jobs"]} == {"j_now", "j_big"}
    assert api.get("/v1/jobs", query="tableau").json()["total"] == 0  # j_later not yet visible
    assert {j["job_id"] for j in api.get("/v1/jobs", category="scripting").json()["jobs"]} == {"j_cheap"}
    assert {j["job_id"] for j in api.get("/v1/jobs", skills="llm,sql").json()["jobs"]} == {"j_hourly"}
    assert api.get("/v1/jobs", posted_after="2026-11-01T00:00:00Z").json()["jobs"] == []
    page = api.get("/v1/jobs", limit=2, offset=1).json()
    assert len(page["jobs"]) == 2 and page["total"] == 5


def test_client_profile_hides_hidden_fields(api):
    c = api.get("/v1/clients/c_good").json()
    assert "hidden" not in c
    assert c["hire_rate"] == 0.8
    assert {j["job_id"] for j in c["recent_jobs"]} >= {"j_now", "j_big"}
    assert api.get("/v1/clients/nope").status_code == 404


def test_pricing_stats(api):
    r = api.get("/v1/stats/pricing", category="AI/ML").json()
    assert r["fixed"] == {"count": 5, "p25": 200.0, "p50": 300.0, "p75": 400.0, "mean": 300.0}
    assert r["hourly"]["count"] == 3 and r["hourly"]["p50"] == 40.0
    r = api.get("/v1/stats/pricing", skills="SQL").json()
    assert r["fixed"]["count"] == 1 and r["hourly"]["count"] == 0 and r["hourly"]["p50"] is None


def test_admin_load_jobs(api):
    job = {"job_id": "dev_1", "title": "Dev set job", "description": "Needs Rust", "category": "Systems",
           "skills": ["Rust"], "budget_type": "fixed", "budget_min": 100, "budget_max": 300,
           "client_id": "dev_client", "posted_at": "2026-10-31T00:00:00Z", "proposals_count": 0}
    client = {"client_id": "dev_client", "name": "Dev Client", "hires": 1, "jobs_posted": 2,
              "hidden": {"must_have_skills": ["Rust"], "budget_ceiling_usd": 400, "responsiveness": 1.0,
                         "dislikes_generic_openings": False, "prefers_short": False, "is_scammer": False}}
    assert api.get("/v1/jobs/dev_1").status_code == 404
    r = api.admin("/v1/admin/load_jobs", {"jobs": [job], "clients": [client]})
    assert r.json() == {"jobs_loaded": 1, "clients_loaded": 1}
    assert api.get("/v1/jobs/dev_1").json()["title"] == "Dev set job"
    c = api.get("/v1/clients/dev_client").json()
    assert c["name"] == "Dev Client" and "hidden" not in c
    prop = api.submit_new("dev_1")
    assert prop["status"] == "submitted"
    assert api.post("/v1/admin/load_jobs", {"jobs": [{"title": "no id"}]}, who="admin").status_code == 422
    assert api.post("/v1/admin/load_jobs", {"jobs": []}, who="ai_ml").status_code == 403


# ---------------------------------------------------------------------------------------------
# proposals, Connects, idempotency
# ---------------------------------------------------------------------------------------------


def test_connects_initial_and_spend(api):
    c = api.get("/v1/me/connects").json()
    assert c["balance"] == 80 and c["weekly_allowance"] == 80 and c["spent"] == []
    prop = api.submit_new("j_now")  # fixed, budget_max 800 -> 6
    assert prop["connects_spent"] == 6 and prop["status"] == "submitted"
    c = api.get("/v1/me/connects").json()
    assert c["balance"] == 74
    assert c["spent"][0]["amount"] == 6 and c["spent"][0]["job_id"] == "j_now"
    assert api.balance("fullstack") == 80  # per-account


def test_draft_is_free_and_validated(api):
    d = api.draft("j_now")
    assert d.status_code == 201 and d.json()["status"] == "draft"
    assert api.balance() == 80
    assert api.draft("j_now", cover="too short").status_code == 422
    assert api.draft("j_now", bid=0).status_code == 422
    assert api.draft("j_now", bid_type="weekly").status_code == 422
    assert api.draft("missing_job").status_code == 404
    assert api.draft("j_later").status_code == 404  # not yet released
    assert api.get(f"/v1/proposals/{d.json()['proposal_id']}").json()["status"] == "draft"
    assert api.get(f"/v1/proposals/{d.json()['proposal_id']}", who="fullstack").status_code == 404


def test_missing_idempotency_key(api):
    r = api.post("/v1/proposals", {"job_id": "j_now", "cover_letter": COVER_STRONG, "bid_amount": 10,
                                   "bid_type": "fixed"}, key=None)
    assert r.status_code == 400 and r.json()["error"] == "missing_idempotency_key"


def test_idempotent_replay_does_not_double_spend(api):
    body = {"job_id": "j_now", "cover_letter": COVER_STRONG, "screening_answers": [], "bid_amount": 600,
            "bid_type": "fixed"}
    r1 = api.post("/v1/proposals", body, key="draft-1")
    r2 = api.post("/v1/proposals", body, key="draft-1")
    assert r1.status_code == r2.status_code == 201
    assert r1.json() == r2.json()
    assert r2.headers["Idempotent-Replay"] == "true" and "Idempotent-Replay" not in r1.headers
    assert len(api.get("/v1/proposals").json()["proposals"]) == 1
    pid = r1.json()["proposal_id"]
    s1 = api.submit(pid, key="sub-1")
    s2 = api.submit(pid, key="sub-1")
    assert s1.status_code == s2.status_code == 200
    assert s2.headers["Idempotent-Replay"] == "true"
    assert s1.json() == s2.json()
    assert api.balance() == 74  # spent exactly once
    assert len(api.get("/v1/me/connects").json()["spent"]) == 1


def test_idempotency_conflict(api):
    body = {"job_id": "j_now", "cover_letter": COVER_STRONG, "screening_answers": [], "bid_amount": 600,
            "bid_type": "fixed"}
    assert api.post("/v1/proposals", body, key="k1").status_code == 201
    r = api.post("/v1/proposals", {**body, "bid_amount": 601}, key="k1")
    assert r.status_code == 409 and r.json() == {"error": "idempotency_conflict"}
    # keys are scoped per account
    assert api.post("/v1/proposals", body, who="fullstack", key="k1").status_code == 201


def test_second_submit_for_same_job_conflicts(api):
    api.submit_new("j_now")
    d = api.draft("j_now", cover=COVER_PLAIN)
    assert d.status_code == 201
    r = api.submit(d.json()["proposal_id"])
    assert r.status_code == 409 and r.json()["error"] == "already_submitted"
    assert api.balance() == 74
    # a different account may bid on the same job
    assert api.submit_new("j_now", who="fullstack")["status"] == "submitted"


def test_insufficient_connects_402_then_weekly_reset(api):
    jobs = [{"job_id": f"big_{i}", "title": f"Big job {i}", "description": "x", "category": "AI/ML",
             "skills": ["Python"], "budget_type": "fixed", "budget_min": 2000, "budget_max": 5000,
             "client_id": "c_low", "posted_at": "2026-10-30T10:00:00Z", "proposals_count": 1}
            for i in range(11)]
    api.admin("/v1/admin/load_jobs", {"jobs": jobs})
    for i in range(10):
        assert api.submit_new(f"big_{i}")["connects_spent"] == 8
    assert api.balance() == 0
    d = api.draft("big_10").json()
    r = api.submit(d["proposal_id"])
    assert r.status_code == 402
    assert r.json() == {"error": "insufficient_connects", "required": 8, "balance": 0}
    assert api.get(f"/v1/proposals/{d['proposal_id']}").json()["status"] == "draft"
    api.advance(24 * 7)  # next sim week
    c = api.get("/v1/me/connects").json()
    assert c["balance"] == 80 and c["spent"] == []
    assert api.submit(d["proposal_id"]).status_code == 200


# ---------------------------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------------------------


def test_policy_endpoint_and_admin_switch(api):
    p1 = api.get("/v1/policy").json()
    assert p1["version"] == "1" and p1["weekly_allowance"] == 80 and p1["rules_text"]
    assert p1["connects_table"]["hourly"] == 6
    api.config(policy_version="2")
    p2 = api.get("/v1/policy").json()
    assert p2["version"] == "2" and p2["effective_date"].startswith("2026-11-02")
    assert p2["connects_table"]["high_competition_surcharge"]["min_proposals_count"] == 15
    assert api.admin("/v1/admin/config", {"policy_version": "9"}).status_code == 422


def test_policy_v1_vs_v2_cost(api):
    # j_big: fixed 5000, proposals_count 20; j_now: fixed 800, 3 proposals; j_hourly: hourly, 20 proposals
    q1 = {j: api.get("/v1/connects/quote", job_id=j).json() for j in ("j_big", "j_now", "j_hourly", "j_cheap")}
    assert [q1[j]["cost"] for j in ("j_big", "j_now", "j_hourly", "j_cheap")] == [8, 6, 6, 2]
    api.config(policy_version="2")
    q2 = {j: api.get("/v1/connects/quote", job_id=j).json() for j in ("j_big", "j_now", "j_hourly", "j_cheap")}
    assert [q2[j]["cost"] for j in ("j_big", "j_now", "j_hourly", "j_cheap")] == [12, 6, 9, 2]
    assert q2["j_big"]["policy_version"] == "2" and q2["j_big"]["surcharge"] == 4
    # submit charges the v2 price
    assert api.submit_new("j_big")["connects_spent"] == 12
    assert api.balance() == 68


def test_policy_v2_link_restriction_422_no_spend(api):
    bad = COVER_STRONG + " See my portfolio at https://myportfolio.example.com/ml for details."
    # v1: links are fine
    assert api.submit_new("j_now", cover=bad)["status"] == "submitted"
    api.config(policy_version="2")
    r = api.draft("j_big", cover=bad)
    assert r.status_code == 422 and r.json() == {"error": "policy_violation", "rule": "link_restriction"}
    ok = COVER_STRONG + " Code: https://github.com/someone/pytorch-pipeline and github.com/other/repo."
    assert api.draft("j_big", cover=ok).status_code == 201
    before = api.balance()
    # draft made under v1, submitted under v2: still rejected at submit time, nothing spent
    api.config(policy_version="1")
    d = api.draft("j_hourly", cover=bad, bid_type="hourly", bid=50).json()
    api.config(policy_version="2")
    r = api.submit(d["proposal_id"])
    assert r.status_code == 422 and r.json() == {"error": "policy_violation", "rule": "link_restriction"}
    assert api.balance() == before
    assert api.get(f"/v1/proposals/{d['proposal_id']}").json()["status"] == "draft"
    # screening answers count too
    r = api.post("/v1/proposals", {"job_id": "j_hourly", "cover_letter": COVER_STRONG, "bid_amount": 50,
                                   "bid_type": "hourly", "screening_answers": ["visit www.mysite.io"]})
    assert r.status_code == 422 and r.json()["rule"] == "link_restriction"


# ---------------------------------------------------------------------------------------------
# simulated clients: decisions, events, messages
# ---------------------------------------------------------------------------------------------


def test_decision_reproducible_across_resets(api):
    def run():
        api.admin("/v1/admin/reset")
        prop = api.submit_new("j_now")
        return prop["proposal_id"], api.decision(prop["proposal_id"])

    pid1, d1 = run()
    pid2, d2 = run()
    assert pid1 == pid2 == "prop_000001"
    assert d1 == d2
    assert set(d1) >= {"features", "probabilities", "stage", "schedule", "u", "mode"}
    p = d1["probabilities"]
    assert p["p_interview"] == pytest.approx(0.55 * p["p_reply"])
    assert p["p_hire"] == pytest.approx(0.5 * p["p_interview"])
    assert d1["features"]["source"] == "heuristic"
    # decision is admin-only
    assert api.get(f"/v1/admin/proposals/{pid1}/decision", who="ai_ml").status_code == 403
    assert api.get("/v1/admin/proposals/prop_999999/decision", who="admin").status_code == 404


def test_strong_vs_plain_proposal_features(api):
    a = api.submit_new("j_now", cover=COVER_STRONG)
    b = api.submit_new("j_big", cover=COVER_PLAIN)
    fa, fb = api.decision(a["proposal_id"])["features"], api.decision(b["proposal_id"])["features"]
    assert fa["must_have_coverage"] == 1.0 and fb["must_have_coverage"] == 0.0
    assert fa["specificity"] > fb["specificity"] and fa["personalization"] > fb["personalization"]


def test_events_delivered_after_clock_advance_and_scam_signal(api):
    prop = api.submit_new("j_scam", cover=COVER_PLAIN, bid=100)
    pid = prop["proposal_id"]
    assert api.get("/v1/events").json()["events"] == []  # nothing delivered yet
    assert api.get("/v1/threads").json()["threads"] == []
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "submitted"
    api.advance(2)  # scam clients reply within 1 hour
    ev = api.get("/v1/events").json()
    types = [e["type"] for e in ev["events"]]
    assert types == ["proposal_viewed", "client_message"]
    msg_ev = ev["events"][1]
    assert msg_ev["payload"]["intent"] == "scam_signal" and msg_ev["payload"]["signals"]
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "replied"
    # cursor semantics
    assert api.get("/v1/events", since=ev["next_cursor"]).json()["events"] == []
    after_first = api.get("/v1/events", since=ev["events"][0]["event_id"]).json()["events"]
    assert [e["type"] for e in after_first] == ["client_message"]
    # other accounts do not see them
    assert api.get("/v1/events", who="fullstack").json()["events"] == []
    # thread + message
    threads = api.get("/v1/threads").json()["threads"]
    assert len(threads) == 1 and threads[0]["client_name"] == "Quick Cash Ltd"
    msgs = api.get(f"/v1/threads/{threads[0]['thread_id']}/messages").json()["messages"]
    assert len(msgs) == 1 and msgs[0]["sender"] == "client" and msgs[0]["intent"] == "scam_signal"
    low = msgs[0]["text"].lower()
    assert "telegram" in low or "whatsapp" in low or "fee" in low or "test" in low or "deposit" in low


def test_event_cursor_loses_nothing_when_delays_interleave(api):
    api.submit_new("j_scam", cover=COVER_PLAIN, bid=100)
    api.submit_new("j_now")
    api.submit_new("j_big", who="ai_ml")
    collected, cursor = [], None
    for hours in (0.5, 1, 3, 20, 100):
        api.advance(hours)
        r = api.get("/v1/events", **({"since": cursor} if cursor else {})).json()
        collected += r["events"]
        cursor = r["next_cursor"]
    full = api.get("/v1/events", limit=500).json()["events"]
    assert [e["event_id"] for e in collected] == [e["event_id"] for e in full]
    at = [e["at"] for e in full]
    assert at == sorted(at)


def test_ignored_proposal_is_lost_after_72h(api):
    # c_low has responsiveness 0 -> p_reply == 0 -> never replies
    prop = api.submit_new("j_cheap", cover=COVER_PLAIN, bid=40)
    pid = prop["proposal_id"]
    assert api.decision(pid)["stage"] == "ignored"
    api.advance(71)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] in ("submitted", "viewed")
    api.advance(2)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "lost"
    assert api.get("/v1/events").json()["events"][-1]["type"] == "lost"
    assert api.get("/v1/proposals", status="lost").json()["count"] == 1
    assert api.get("/v1/proposals", status="draft").json()["count"] == 0


def test_scam_thread_message_flow_and_idempotency(api):
    pid = api.submit_new("j_scam", cover=COVER_PLAIN, bid=100)["proposal_id"]
    api.advance(2)
    tid = api.get("/v1/threads").json()["threads"][0]["thread_id"]
    body = {"text": "Why do you need a fee? Can we keep it on the platform?"}
    r1 = api.post(f"/v1/threads/{tid}/messages", body, key="m1")
    r2 = api.post(f"/v1/threads/{tid}/messages", body, key="m1")
    assert r1.status_code == 201 and r1.json() == r2.json()
    assert r2.headers["Idempotent-Replay"] == "true"
    assert api.post(f"/v1/threads/{tid}/messages", body, key=None).status_code == 400
    assert api.post(f"/v1/threads/{tid}/messages", {"text": "other"}, key="m1").status_code == 409
    assert api.post(f"/v1/threads/{tid}/messages", body, who="fullstack").status_code == 404
    assert api.post("/v1/threads/th_nope/messages", body).status_code == 404
    api.advance(2)
    msgs = api.get(f"/v1/threads/{tid}/messages").json()["messages"]
    assert [m["sender"] for m in msgs] == ["client", "freelancer", "client"]
    assert msgs[2]["intent"] == "scam_followup"
    assert api.get(f"/v1/proposals/{pid}").json()["thread_id"] == tid


def test_interview_request_and_nudge_when_no_times(api):
    prop, dec = find_proposal(api, {"interview"})
    pid = prop["proposal_id"]
    assert dec["final_outcome"] == "lost"
    api.advance(25)  # the client reply is scheduled within 24h
    p = api.get(f"/v1/proposals/{pid}").json()
    assert p["status"] == "interview" and p["thread_id"]
    tid = p["thread_id"]
    msgs = api.get(f"/v1/threads/{tid}/messages").json()["messages"]
    assert msgs[0]["intent"] == "interview_request" and "slot" in msgs[0]["text"].lower()
    types = [e["type"] for e in api.get("/v1/events", limit=500).json()["events"] if e["proposal_id"] == pid]
    assert "interview_requested" in types
    # a reply without concrete times: the client asks again and no outcome is scheduled
    r = api.post(f"/v1/threads/{tid}/messages", {"text": "Sounds great, happy to talk!"})
    assert r.status_code == 201 and r.json()["proposed_times"] == []
    api.advance(9)
    msgs = api.get(f"/v1/threads/{tid}/messages").json()["messages"]
    assert msgs[-1]["intent"] == "request_times"
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "interview"


@pytest.mark.parametrize("stage,final", [("interview", "lost"), ("hired", "hired")])
def test_interview_times_recorded_and_outcome(api, stage, final):
    prop, dec = find_proposal(api, {stage})
    pid = prop["proposal_id"]
    api.advance(25)
    tid = api.get(f"/v1/proposals/{pid}").json()["thread_id"]
    assert tid
    r = api.post(f"/v1/threads/{tid}/messages",
                 {"text": "Happy to chat. I can do Tue 14:00 UTC, Wed 10:00 UTC or Thursday 3pm UTC."})
    assert r.status_code == 201
    times = r.json()["proposed_times"]
    assert len(times) >= 3 and any("14:00" in t for t in times)
    api.advance(9)
    intents = [m["intent"] for m in api.get(f"/v1/threads/{tid}/messages").json()["messages"] if m["sender"] == "client"]
    assert "interview_confirmed" in intents
    api.advance(100)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == final
    intents = [m["intent"] for m in api.get(f"/v1/threads/{tid}/messages").json()["messages"] if m["sender"] == "client"]
    assert intents[-1] == ("offer" if final == "hired" else "rejection")
    assert final in [e["type"] for e in api.get("/v1/events", limit=500).json()["events"] if e["proposal_id"] == pid]
    # a late message after the outcome gets a closing reply, state does not change
    api.post(f"/v1/threads/{tid}/messages", {"text": "Thanks for the update!"})
    api.advance(10)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == final


def test_interview_without_reply_times_out_to_lost(api):
    prop, _ = find_proposal(api, {"interview", "hired"})
    pid = prop["proposal_id"]
    api.advance(25)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "interview"
    api.advance(130)
    assert api.get(f"/v1/proposals/{pid}").json()["status"] == "lost"


def test_validation_error_shape(api):
    r = api.post("/v1/threads/x/messages", {"text": ""})
    assert r.status_code == 422 and r.json()["error"] == "validation_error"
    assert api.get("/v1/does-not-exist").status_code == 404
    assert api.admin("/v1/admin/clock/advance", {"hours": -1}).status_code == 422
