"""Tests for the petition completeness scorer."""

from immigration_compliance.services.completeness_scorer_service import (
    CompletenessScorerService,
    FACTOR_SETS,
    evaluate_factor,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService


def _make():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    cw = CaseWorkspaceService(intake_engine=ie, document_intake=di)
    sc = CompletenessScorerService(case_workspace=cw, intake_engine=ie, document_intake=di)
    return ie, di, cw, sc


def test_factor_sets_cover_major_petitions():
    expected = {"H-1B", "O-1", "EB-1A", "I-485", "I-130"}
    assert expected <= set(FACTOR_SETS.keys())


def test_strong_h1b_scores_high():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {
        "has_bachelors_or_higher": True, "us_masters_or_higher": True,
        "lca_filed": True, "wage_level": "III", "selected_in_lottery": True,
        "petitioner_name": "Acme", "petitioner_fein": "12-3456789", "petitioner_employees": 500,
        "third_party_placement": False,
    })
    di.upload("user-1", sess["id"], "lca.pdf", size_bytes=500_000, resolution_dpi=300)
    di.upload("user-1", sess["id"], "employment_letter.pdf", size_bytes=500_000, resolution_dpi=300)
    di.upload("user-1", sess["id"], "degree.pdf", size_bytes=500_000, resolution_dpi=300)
    di.upload("user-1", sess["id"], "transcript.pdf", size_bytes=500_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "H-1B")
    assert report["overall_score"] >= 80
    assert report["overall_tier"] in ("near_ready", "ready")


def test_weak_h1b_has_blockers_and_remediation():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"wage_level": "I"})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "H-1B")
    assert report["overall_score"] < 60
    assert len(report["blockers"]) >= 1
    # Remediation steps surface for low-scoring factors
    weak_factors = [f for f in report["factors"] if f["score"] < 75]
    assert any(f["remediation"] for f in weak_factors)


def test_o1_no_advisory_opinion_flagged():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"criteria_awards": True, "criteria_press": True, "criteria_publications": True})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "O-1")
    advisory_factor = next(f for f in report["factors"] if f["id"] == "advisory_opinion_present")
    assert advisory_factor["score"] == 0


def test_o1_with_advisory_opinion_passes():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"has_advisory_opinion": True})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "O-1")
    advisory_factor = next(f for f in report["factors"] if f["id"] == "advisory_opinion_present")
    assert advisory_factor["score"] == 100


def test_i485_blocks_when_priority_date_not_current():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "I-485")
    ie.submit_answers(sess["id"], {"priority_date_current": False, "underlying_petition_approved": True})
    ws = cw.create_workspace("user-1", "I-485", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "I-485")
    pd_factor = next(f for f in report["factors"] if f["id"] == "priority_date_current")
    assert pd_factor["score"] == 0
    assert any(b["factor_id"] == "priority_date_current" for b in report["blockers"])


def test_i130_relationship_evidence_factor():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "I-130")
    ie.submit_answers(sess["id"], {"petitioner_status": "US_citizen"})
    di.upload("user-1", sess["id"], "marriage_certificate.pdf", size_bytes=500_000, resolution_dpi=300)
    di.upload("user-1", sess["id"], "tax_return.pdf", size_bytes=500_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "I-130", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "I-130")
    rel_factor = next(f for f in report["factors"] if f["id"] == "relationship_evidence")
    assert rel_factor["score"] >= 50


def test_unknown_petition_kind_rejected():
    ie, di, cw, sc = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    try:
        sc.score(ws["id"], "FAKE-KIND")
        assert False
    except ValueError:
        pass


def test_overall_score_in_valid_range():
    ie, di, cw, sc = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    report = sc.score(ws["id"], "H-1B")
    assert 0 <= report["overall_score"] <= 100


def test_each_factor_has_evidence_and_tier():
    ie, di, cw, sc = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    report = sc.score(ws["id"], "H-1B")
    for f in report["factors"]:
        assert "evidence" in f
        assert isinstance(f["evidence"], list)
        assert f["tier"] in ("ready", "near_ready", "needs_work", "weak", "blocking")


def test_eb1a_kazarian_factor():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "I-485")
    ie.submit_answers(sess["id"], {
        "criteria_awards": True, "criteria_press": True, "criteria_publications": True, "criteria_judging": True,
    })
    di.upload("user-1", sess["id"], "support_letter.pdf", size_bytes=500_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "I-485", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "EB-1A")
    kaz = next(f for f in report["factors"] if f["id"] == "kazarian_two_step_passed")
    assert kaz["score"] >= 60


def test_h1b_third_party_placement_flagged():
    ie, di, cw, sc = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"third_party_placement": True})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    report = sc.score(ws["id"], "H-1B")
    eer = next(f for f in report["factors"] if f["id"] == "employer_employee_relation")
    assert eer["score"] < 80  # third-party with no docs → low


def test_evaluate_factor_directly():
    """Direct unit test on one factor."""
    snap = {"workspace": {"attorney_id": "atty-1"}}
    score, evidence = evaluate_factor("signed_g28_present", snap, {}, [])
    assert score == 100
    assert "attorney" in evidence[0].lower()


def test_listing_reports_filtered_by_workspace():
    ie, di, cw, sc = _make()
    ws1 = cw.create_workspace("user-1", "H-1B", "US")
    ws2 = cw.create_workspace("user-1", "O-1", "US")
    sc.score(ws1["id"], "H-1B")
    sc.score(ws2["id"], "O-1")
    sc.score(ws1["id"], "H-1B")
    assert len(sc.list_reports()) == 3
    assert len(sc.list_reports(workspace_id=ws1["id"])) == 2


def test_factor_set_listing_includes_weights():
    petitions = CompletenessScorerService.list_supported_petitions()
    assert all(p["total_weight"] > 0 for p in petitions)


def test_get_factor_set_returns_full_spec():
    fs = CompletenessScorerService.get_factor_set("H-1B")
    assert fs is not None
    assert len(fs) >= 9
    assert all("id" in f and "weight" in f for f in fs)
