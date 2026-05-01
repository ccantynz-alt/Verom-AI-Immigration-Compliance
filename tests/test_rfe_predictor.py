"""Tests for RFE Predictor — pre-filing risk analysis."""

from immigration_compliance.services.rfe_predictor_service import (
    RFEPredictorService,
    RFE_TRIGGERS,
)


def test_trigger_library_has_major_visa_types():
    assert {"H-1B", "O-1", "I-485", "F-1", "I-130"} <= set(RFE_TRIGGERS.keys())


def test_predict_returns_complete_structure():
    svc = RFEPredictorService()
    r = svc.predict("H-1B", {})
    assert "risk_score" in r and "risk_tier" in r
    assert r["risk_tier"] in ("low", "moderate", "high", "very_high")
    assert isinstance(r["fired_triggers"], list)
    assert isinstance(r["mitigation_steps"], list)


def test_predict_h1b_low_wage_fires_specialty_trigger():
    svc = RFEPredictorService()
    r = svc.predict("H-1B", {"wage_level": "I"})
    codes = [t["code"] for t in r["fired_triggers"]]
    assert "SPECIALTY_OCCUPATION_LEVEL_I" in codes
    assert r["risk_score"] > 0


def test_predict_h1b_third_party_placement_fires_relationship_trigger():
    svc = RFEPredictorService()
    r = svc.predict("H-1B", {"third_party_placement": True})
    codes = [t["code"] for t in r["fired_triggers"]]
    assert "EMPLOYER_EMPLOYEE_RELATIONSHIP" in codes


def test_predict_h1b_combined_triggers_increase_risk():
    svc = RFEPredictorService()
    one = svc.predict("H-1B", {"wage_level": "I"})
    many = svc.predict("H-1B", {
        "wage_level": "I",
        "degree_field_matches_role": False,
        "third_party_placement": True,
    })
    assert many["risk_score"] >= one["risk_score"]
    assert many["total_triggers"] >= one["total_triggers"]


def test_predict_includes_post_mitigation_estimate():
    svc = RFEPredictorService()
    r = svc.predict("H-1B", {"wage_level": "I"})
    assert "post_mitigation_risk_pct" in r
    assert r["post_mitigation_risk_pct"] <= r["risk_score"]
    assert r["risk_reduction_pct"] >= 0


def test_predict_o1_marginal_criteria():
    svc = RFEPredictorService()
    r = svc.predict("O-1", {"criteria_count": 3})
    codes = [t["code"] for t in r["fired_triggers"]]
    assert "INSUFFICIENT_CRITERIA_EVIDENCE" in codes


def test_predict_unknown_visa_type_returns_zero_risk():
    svc = RFEPredictorService()
    r = svc.predict("NOT-A-VISA", {})
    assert r["risk_score"] == 0
    assert r["fired_triggers"] == []


def test_industry_baselines_returned():
    svc = RFEPredictorService()
    b = svc.get_industry_baselines()
    assert "H-1B" in b and "O-1" in b


def test_list_known_triggers():
    svc = RFEPredictorService()
    triggers = svc.list_known_triggers("H-1B")
    assert len(triggers) >= 3
    for t in triggers:
        assert "code" in t and "title" in t and "citation" in t
