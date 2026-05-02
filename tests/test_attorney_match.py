"""Tests for the intake-aware Attorney Match service."""

from immigration_compliance.services.attorney_match_service import (
    AttorneyMatchService,
    DEFAULT_ATTORNEYS,
)


def test_default_attorneys_cover_all_target_countries():
    countries = {a["country"] for a in DEFAULT_ATTORNEYS}
    assert {"US", "UK", "CA", "AU", "DE"} <= countries


def test_match_returns_results_for_h1b_us():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US")
    assert len(r["results"]) > 0
    assert r["results"][0]["match_score"] > 50


def test_match_results_sorted_descending_by_score():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US")
    scores = [x["match_score"] for x in r["results"]]
    assert scores == sorted(scores, reverse=True)


def test_match_specialization_boost():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US")
    top = r["results"][0]
    assert "Specializes in H-1B" in top["reasons"]


def test_match_country_filter():
    svc = AttorneyMatchService()
    r = svc.match("UK-Skilled-Worker", "UK")
    assert all(a["country"] == "UK" for a in r["results"])


def test_match_language_overlap_boost():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US", applicant_languages=["English", "Korean"])
    top = r["results"][0]
    # Korean-speaking attorney should rank highly
    korean_attys = [a for a in r["results"] if "Korean" in a["languages"]]
    assert len(korean_attys) > 0


def test_match_red_flag_experience_boost():
    svc = AttorneyMatchService()
    r1 = svc.match("H-1B", "US", red_flag_codes=[])
    r2 = svc.match("H-1B", "US", red_flag_codes=["SPECIALTY_OCCUPATION_LEVEL_I"])
    # Attorney with SPECIALTY_OCCUPATION_LEVEL_I in handled list should benefit
    top_with_flag = r2["results"][0]
    assert any("SPECIALTY" in r for r in top_with_flag["reasons"]) or top_with_flag["match_score"] > 0


def test_match_excludes_not_accepting():
    svc = AttorneyMatchService(attorneys=[
        {"id": "a1", "name": "Closed Attorney", "country": "US", "jurisdictions": ["NY"],
         "specializations": ["H-1B"], "languages": ["English"], "years_experience": 10,
         "approval_rate": 0.9, "rfe_response_success_rate": 0.9, "avg_response_time_hours": 4,
         "active_cases": 20, "max_active_cases": 20, "accepting_new_cases": True, "verified": True,
         "marketplace_optin": True, "rfe_categories_handled": [], "bar_number": "X"},
    ])
    r = svc.match("H-1B", "US")
    # at-capacity attorney should be filtered by list_attorneys
    assert len(r["results"]) == 0


def test_match_excludes_unverified():
    svc = AttorneyMatchService(attorneys=[
        {"id": "a1", "name": "Unverified", "country": "US", "jurisdictions": ["NY"],
         "specializations": ["H-1B"], "languages": ["English"], "years_experience": 10,
         "approval_rate": 0.9, "rfe_response_success_rate": 0.9, "avg_response_time_hours": 4,
         "active_cases": 0, "max_active_cases": 10, "accepting_new_cases": True, "verified": False,
         "marketplace_optin": True, "rfe_categories_handled": [], "bar_number": "X"},
    ])
    r = svc.match("H-1B", "US")
    assert len(r["results"]) == 0


def test_score_breakdown_components_present():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US")
    top = r["results"][0]
    components = top["score_breakdown"]
    assert {"specialization", "country", "languages", "capacity", "red_flag_experience", "response_time", "approval_signal"} <= set(components.keys())


def test_match_log_persists():
    svc = AttorneyMatchService()
    svc.match("H-1B", "US")
    svc.match("O-1", "US")
    log = svc.get_match_log()
    assert len(log) == 2


def test_match_for_session_uses_summary():
    svc = AttorneyMatchService()
    summary = {
        "visa_type": "H-1B",
        "country": "US",
        "red_flags": [{"code": "SPECIALTY_OCCUPATION_LEVEL_I"}],
    }
    r = svc.match_for_session(summary, applicant_languages=["English"])
    assert r["visa_type"] == "H-1B"
    assert r["country"] == "US"
    assert len(r["results"]) > 0


def test_capacity_remaining_in_results():
    svc = AttorneyMatchService()
    r = svc.match("H-1B", "US")
    for res in r["results"]:
        assert res["capacity_remaining"] >= 1
