"""Tests for AI Intake Engine — adaptive questionnaires, validation, scoring, red flags."""

from immigration_compliance.services.intake_engine_service import (
    IntakeEngineService,
    VISA_REGISTRY,
)


def test_registry_covers_all_target_countries():
    countries = {cfg["country"] for cfg in VISA_REGISTRY.values()}
    assert {"US", "UK", "CA", "AU", "DE", "NZ"} <= countries


def test_registry_covers_all_visa_families():
    families = {cfg["family"] for cfg in VISA_REGISTRY.values()}
    assert {"student", "work", "family", "pr"} <= families


def test_list_visa_types_filtered_by_country():
    svc = IntakeEngineService()
    us = svc.list_visa_types(country="US")
    assert len(us) >= 5
    assert all(v["country"] == "US" for v in us)


def test_list_visa_types_filtered_by_family():
    svc = IntakeEngineService()
    students = svc.list_visa_types(family="student")
    assert len(students) >= 4
    assert all(v["family"] == "student" for v in students)


def test_get_questionnaire_returns_complete_structure():
    svc = IntakeEngineService()
    q = svc.get_questionnaire("H-1B")
    assert q["visa_type"] == "H-1B"
    assert q["country"] == "US"
    assert q["total_questions"] == len(q["questions"])
    assert q["total_questions"] >= 5


def test_get_questionnaire_unknown_raises():
    svc = IntakeEngineService()
    try:
        svc.get_questionnaire("NOT-A-VISA")
        assert False, "should raise"
    except ValueError:
        pass


def test_validate_h1b_blocking_when_no_bachelors():
    svc = IntakeEngineService()
    res = svc.validate_answers("H-1B", {"has_bachelors_or_higher": False, "has_us_employer_offer": True, "lca_filed": True})
    assert res["ok"] is False
    assert any(b for b in res["blocking_issues"])


def test_validate_h1b_passes_with_eligible_answers():
    svc = IntakeEngineService()
    res = svc.validate_answers("H-1B", {
        "has_bachelors_or_higher": True,
        "has_us_employer_offer": True,
        "lca_filed": True,
        "wage_level": "III",
        "us_masters_or_higher": True,
        "selected_in_lottery": True,
        "prior_h1b_approval": False,
        "current_status_in_us": "F-1_OPT",
    })
    assert res["ok"] is True
    assert res["blocking_issues"] == []


def test_validate_o1_requires_min_3_criteria():
    svc = IntakeEngineService()
    # Only 2 criteria
    res = svc.validate_answers("O-1", {"criteria_awards": True, "criteria_membership": True})
    assert res["ok"] is False
    # 3 criteria
    res2 = svc.validate_answers("O-1", {"criteria_awards": True, "criteria_membership": True, "criteria_publications": True})
    assert res2["ok"] is True


def test_score_strength_excellent():
    svc = IntakeEngineService()
    s = svc.score_strength("H-1B", {
        "has_bachelors_or_higher": True,
        "lca_filed": True,
        "wage_level": "III",
        "us_masters_or_higher": True,
        "selected_in_lottery": True,
        "prior_us_visa_denial": False,
        "prior_immigration_violation": False,
    })
    assert 0 <= s["score"] <= 100
    assert s["tier"] in ("excellent", "strong", "moderate", "weak")
    assert "strengths" in s and "missing_factors" in s
    assert s["earned_points"] + sum(m["weight"] for m in s["missing_factors"]) == s["max_points"]


def test_document_checklist_categorizes():
    svc = IntakeEngineService()
    cl = svc.get_document_checklist("H-1B")
    assert cl["total"] >= 5
    categories = {item["category"] for item in cl["items"]}
    assert "identity" in categories or "supporting" in categories


def test_red_flag_h1b_low_wage_no_masters():
    svc = IntakeEngineService()
    flags = svc.detect_red_flags("H-1B", {
        "wage_level": "I",
        "us_masters_or_higher": False,
        "selected_in_lottery": True,
    })
    codes = [f["code"] for f in flags]
    assert "LOW_WAGE_NO_MASTERS" in codes


def test_red_flag_h1b_not_selected_lottery():
    svc = IntakeEngineService()
    flags = svc.detect_red_flags("H-1B", {"selected_in_lottery": False})
    assert any(f["code"] == "NOT_SELECTED_LOTTERY" and f["severity"] == "blocking" for f in flags)


def test_red_flag_o1_insufficient_criteria():
    svc = IntakeEngineService()
    flags = svc.detect_red_flags("O-1", {"criteria_awards": True})
    assert any(f["code"] == "INSUFFICIENT_CRITERIA" for f in flags)


def test_session_lifecycle():
    svc = IntakeEngineService()
    s = svc.start_session("user-1", "H-1B")
    assert s["applicant_id"] == "user-1"
    assert s["visa_type"] == "H-1B"
    s2 = svc.submit_answers(s["id"], {"has_bachelors_or_higher": True})
    assert s2["answers"]["has_bachelors_or_higher"] is True


def test_intake_summary_rollup():
    svc = IntakeEngineService()
    s = svc.start_session("user-1", "H-1B")
    svc.submit_answers(s["id"], {
        "has_bachelors_or_higher": True,
        "has_us_employer_offer": True,
        "lca_filed": True,
        "wage_level": "III",
        "us_masters_or_higher": True,
        "selected_in_lottery": True,
        "prior_us_visa_denial": False,
        "prior_immigration_violation": False,
        "current_status_in_us": "F-1_OPT",
    })
    summary = svc.get_intake_summary(s["id"])
    assert "validation" in summary and "documents" in summary and "strength" in summary
    assert summary["validation"]["ok"] is True
    assert summary["ready_to_file"] is True
