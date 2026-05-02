"""Tests for the magical onboarding orchestrator."""

from immigration_compliance.services.onboarding_service import (
    OnboardingService,
    APPLICANT_STEPS,
    ATTORNEY_STEPS,
)


def test_start_applicant_creates_session():
    svc = OnboardingService()
    s = svc.start_applicant_onboarding("user-1")
    assert s["role"] == "applicant"
    assert len(s["steps"]) == len(APPLICANT_STEPS)
    assert s["progress_pct"] == 0


def test_start_attorney_creates_session():
    svc = OnboardingService()
    s = svc.start_attorney_onboarding("atty-1")
    assert s["role"] == "attorney"
    assert len(s["steps"]) == len(ATTORNEY_STEPS)


def test_start_returns_existing_session_for_same_user():
    svc = OnboardingService()
    s1 = svc.start_applicant_onboarding("user-1")
    s2 = svc.start_applicant_onboarding("user-1")
    assert s1["id"] == s2["id"]


def test_submit_step_updates_progress():
    svc = OnboardingService()
    s = svc.start_applicant_onboarding("user-1")
    s2 = svc.submit_step(s["id"], "goal_selection", {"family": "work"})
    completed = [step for step in s2["steps"] if step["status"] == "completed"]
    assert len(completed) == 1
    assert s2["progress_pct"] > 0


def test_submit_invalid_step_raises():
    svc = OnboardingService()
    s = svc.start_applicant_onboarding("user-1")
    try:
        svc.submit_step(s["id"], "not_a_step", {})
        assert False, "should raise"
    except ValueError:
        pass


def test_completion_when_all_steps_done():
    svc = OnboardingService()
    s = svc.start_attorney_onboarding("atty-1")
    for step_name in ATTORNEY_STEPS[:-1]:  # all but final auto-complete
        svc.submit_step(s["id"], step_name, {})
    final = svc.get_session(s["id"])
    assert final["completed"] is True
    assert final["progress_pct"] == 100


def test_reset_step_decreases_progress():
    svc = OnboardingService()
    s = svc.start_applicant_onboarding("user-1")
    svc.submit_step(s["id"], "goal_selection", {"family": "student"})
    pct_after = svc.get_session(s["id"])["progress_pct"]
    svc.reset_step(s["id"], "goal_selection")
    pct_reset = svc.get_session(s["id"])["progress_pct"]
    assert pct_reset < pct_after


def test_get_session_for_user_filters_by_role():
    svc = OnboardingService()
    svc.start_applicant_onboarding("user-1")
    svc.start_attorney_onboarding("user-1")
    s_app = svc.get_session_for_user("user-1", "applicant")
    s_att = svc.get_session_for_user("user-1", "attorney")
    assert s_app["role"] == "applicant"
    assert s_att["role"] == "attorney"
    assert s_app["id"] != s_att["id"]
