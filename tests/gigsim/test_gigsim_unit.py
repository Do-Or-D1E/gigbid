"""Pure-logic tests (no database): policy, heuristic features, probabilities, decision plans."""

from __future__ import annotations

import json

import pytest
from gigsim_testkit import COVER_PLAIN, COVER_STRONG, FIXTURES

from gigsim import clients_sim as cs
from gigsim import clock as clk
from gigsim import policy

CLIENTS = {c["client_id"]: c for c in json.loads((FIXTURES / "seed" / "clients.json").read_text())}
TAXONOMY = cs.load_taxonomy(FIXTURES / "data")
JOB = {"job_id": "j1", "title": "PyTorch model training pipeline", "description": "Build a training pipeline.",
       "skills": ["Python", "PyTorch"], "budget_type": "fixed", "budget_max": 800}


def prop(cover=COVER_STRONG, bid=600, bid_type="fixed"):
    return {"cover_letter": cover, "screening_answers": [], "bid_amount": bid, "bid_type": bid_type}


@pytest.mark.parametrize("budget,cost", [(20, 2), (99.99, 2), (100, 4), (499, 4), (500, 6), (999, 6), (1000, 8), (50000, 8)])
def test_v1_fixed_cost_table(budget, cost):
    job = {"budget_type": "fixed", "budget_max": budget, "proposals_count": 100}
    assert policy.connects_cost(job, "1")["cost"] == cost


def test_hourly_and_v2_surcharge():
    assert policy.connects_cost({"budget_type": "hourly", "budget_max": 90, "proposals_count": 0}, "1")["cost"] == 6
    for budget, v1, v2 in [(50, 2, 3), (300, 4, 6), (700, 6, 9), (2000, 8, 12)]:
        job = {"budget_type": "fixed", "budget_max": budget, "proposals_count": 15}
        assert policy.connects_cost(job, "1")["cost"] == v1
        assert policy.connects_cost(job, "2")["cost"] == v2
        assert policy.connects_cost({**job, "proposals_count": 14}, "2")["cost"] == v1
    assert policy.connects_cost({"budget_type": "hourly", "proposals_count": 40}, "v2")["cost"] == 9
    # rounded up: 2 * 1.5 = 3 exactly; make sure ceil is used for odd bases via a fake base
    assert policy.connects_cost({"budget_type": "fixed", "budget_max": 10, "proposals_count": 15}, "2")["surcharge"] == 1


@pytest.mark.parametrize("text,bad", [
    ("see https://github.com/me/repo", False),
    ("see github.com/me/repo and www.github.com/x", False),
    ("see https://example.com", True),
    ("portfolio: www.mysite.io", True),
    ("https://github.com.evil.com/x", True),
    ("mail me@gmail.com", False),
    ("I use Node.js, ASP.NET and e.g. Vue.", False),
    ("no links here", False),
    ("http://bit.ly/abc", True),
])
def test_link_detection_v2(text, bad):
    assert bool(policy.find_disallowed_links([text], "2")) is bad
    assert policy.find_disallowed_links([text], "1") == []


def test_clock_helpers():
    assert clk.iso(clk.EPOCH_US) == "2026-11-01T09:00:00.000Z"
    assert clk.parse_iso("2026-11-01T09:00:00Z") == clk.EPOCH_US
    state = clk.new_clock_state(60, real_now=1000.0)
    assert clk.sim_now_us(state, 1000.0) == clk.EPOCH_US
    assert clk.sim_now_us(state, 1060.0) == clk.EPOCH_US + 3600 * 1_000_000 * 1  # 60 s * 60 = 1 sim hour
    assert clk.week_start_us(clk.EPOCH_US + 8 * 24 * clk.US_PER_HOUR) == clk.EPOCH_US + clk.US_PER_WEEK


def test_must_have_coverage_levels():
    good = CLIENTS["c_good"]
    f = cs.heuristic_features(prop(), JOB, good, TAXONOMY)
    assert f["must_have_detail"] == {"Python": "evidenced", "PyTorch": "evidenced"}
    mentioned = "I know Python and PyTorch very well and enjoy working with them every day of the week."
    f = cs.heuristic_features(prop(mentioned), JOB, good, TAXONOMY)
    assert set(f["must_have_detail"].values()) == {"mentioned"} and f["must_have_coverage"] == 0.4
    f = cs.heuristic_features(prop(COVER_PLAIN), JOB, good, TAXONOMY)
    assert f["must_have_coverage"] == 0.0
    alias = "I trained torch models in production and cut inference latency by 35% for 2M users in Python."
    f = cs.heuristic_features(prop(alias), JOB, good, TAXONOMY)
    assert f["must_have_detail"]["PyTorch"] == "evidenced"  # alias "torch" counts


def test_generic_opening_length_and_bid():
    good = CLIENTS["c_good"]
    generic = "Dear Sir/Madam, I am writing to apply for this position. " + COVER_PLAIN
    assert cs.heuristic_features(prop(generic), JOB, good, TAXONOMY)["generic_opening"] is True
    assert cs.heuristic_features(prop("I'm passionate about ML. " + COVER_PLAIN), JOB, good, TAXONOMY)["generic_opening"]
    assert cs.heuristic_features(prop(COVER_STRONG), JOB, good, TAXONOMY)["generic_opening"] is False
    long = cs.heuristic_features(prop(COVER_STRONG + " x" * 700), JOB, good, TAXONOMY)
    assert long["too_long"] is True and long["length_chars"] > 1200
    assert cs.heuristic_features(prop(bid=7000), JOB, good, TAXONOMY)["bid_over_ceiling"] is True
    assert cs.heuristic_features(prop(bid=5000), JOB, good, TAXONOMY)["bid_over_ceiling"] is False


def test_specificity_and_personalization_ranges():
    good = CLIENTS["c_good"]
    strong = cs.heuristic_features(prop(COVER_STRONG), JOB, good, TAXONOMY)
    plain = cs.heuristic_features(prop(COVER_PLAIN), JOB, good, TAXONOMY)
    for f in (strong, plain):
        assert 0 <= f["specificity"] <= 10 and 0 <= f["personalization"] <= 10
    assert strong["specificity"] > plain["specificity"] and strong["personalization"] > plain["personalization"]


def feats(**kw):
    base = dict(must_have_coverage=0.0, specificity=0.0, personalization=0.0, generic_opening=False,
                too_long=False, bid_over_ceiling=False)
    return {**base, **kw}


def client(**hidden):
    return {"hidden": {"responsiveness": 1.0, "dislikes_generic_openings": False, "prefers_short": False, **hidden}}


def test_probability_formula():
    p = cs.probabilities(feats(must_have_coverage=1, specificity=10, personalization=10), client())
    assert p["p_reply"] == pytest.approx(0.08 + 0.10 + 0.20 + 0.15)
    assert p["p_interview"] == pytest.approx(0.55 * p["p_reply"]) and p["p_hire"] == pytest.approx(0.5 * p["p_interview"])
    f = feats(must_have_coverage=1, specificity=10, personalization=10, generic_opening=True, too_long=True)
    p = cs.probabilities(f, client(dislikes_generic_openings=True, prefers_short=True))
    assert p["p_reply"] == pytest.approx(0.53 - 0.12 - 0.08)
    # penalties only apply when the client has the matching preference
    assert cs.probabilities(f, client())["p_reply"] == pytest.approx(0.53)
    p = cs.probabilities(feats(must_have_coverage=1, specificity=10, personalization=10, bid_over_ceiling=True),
                         client(responsiveness=0.5))
    assert p["p_reply"] == pytest.approx(0.53 * 0.3 * 0.5)
    low = cs.probabilities(feats(generic_opening=True), client(dislikes_generic_openings=True))
    assert low["p_reply"] == pytest.approx(0.01)  # clipped to the floor
    assert cs.probabilities(feats(must_have_coverage=1, specificity=10, personalization=10), client(responsiveness=0))["p_reply"] == 0


def test_build_plan_is_reproducible_and_depends_on_proposal_id():
    good = CLIENTS["c_good"]
    f = cs.heuristic_features(prop(), JOB, good, TAXONOMY)
    a = cs.build_plan("prop_000001", prop(), JOB, good, f, "Sam", "heuristic")
    b = cs.build_plan("prop_000001", prop(), JOB, good, f, "Sam", "heuristic")
    assert a == b
    others = {cs.build_plan(f"prop_{i:06d}", prop(), JOB, good, f, "Sam", "heuristic")["decision"]["stage"]
              for i in range(2, 60)}
    assert len(others) > 1  # different ids draw different outcomes


def test_scam_plan_replies_within_an_hour():
    scam = CLIENTS["c_scam"]
    for i in range(20):
        f = cs.heuristic_features(prop(COVER_PLAIN), JOB, scam, TAXONOMY)
        plan = cs.build_plan(f"prop_{i:06d}", prop(COVER_PLAIN), JOB, scam, f, "Sam", "heuristic")
        msgs = [e for e in plan["events"] if e["message"]]
        assert len(msgs) == 1 and msgs[0]["message"]["intent"] == "scam_signal"
        assert 0.1 <= msgs[0]["offset_h"] <= 1.0
        assert msgs[0]["message"]["meta"]["signals"]


def test_event_timing_windows():
    good = CLIENTS["c_good"]
    f = cs.heuristic_features(prop(), JOB, good, TAXONOMY)
    for i in range(60):
        plan = cs.build_plan(f"prop_{i:06d}", prop(), JOB, good, f, "Sam", "heuristic")
        for e in plan["events"]:
            if e["type"] == "proposal_viewed":
                assert 0.5 * 0.6 <= e["offset_h"] <= 6.0
            if e["type"] == "client_message":
                assert 2.0 <= e["offset_h"] <= 24.0
            if e["type"] == "lost" and plan["decision"]["stage"] == "ignored":
                assert e["offset_h"] == 72.0


def test_extract_times():
    assert cs.extract_times("Tue 14:00 UTC or Wed 10:00 UTC") == ["Tue", "Wed", "10:00", "14:00"] or \
        len(cs.extract_times("Tue 14:00 UTC or Wed 10:00 UTC")) == 4
    assert cs.extract_times("Thursday at 3pm works") != []
    assert cs.extract_times("2026-11-04 at 9am") != []
    assert cs.extract_times("Sounds great, happy to talk!") == []


def test_llm_cost():
    assert cs.llm_cost("gpt-4o-mini", 1_000_000, 0) == pytest.approx(0.15)
    assert cs.llm_cost("gpt-4o-mini", 0, 1_000_000) == pytest.approx(0.60)
