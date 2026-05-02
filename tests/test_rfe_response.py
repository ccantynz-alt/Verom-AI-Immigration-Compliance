"""Tests for the RFE Response Drafter."""

from immigration_compliance.services.rfe_response_service import (
    RFEResponseService,
    CATEGORY_RULES,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService


def _make():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    cw = CaseWorkspaceService(intake_engine=ie, document_intake=di)
    rs = RFEResponseService(case_workspace=cw, intake_engine=ie, document_intake=di)
    return ie, di, cw, rs


def test_categories_cover_major_rfe_types():
    expected = {
        "specialty_occupation", "employer_employee_relationship",
        "degree_field_mismatch", "criteria_evidence_insufficient",
        "i864_deficiency", "missing_form_or_field", "bona_fide_marriage",
        "status_violation", "public_charge", "financial_evidence",
        "generic_evidence_request",
    }
    assert expected <= set(CATEGORY_RULES.keys())


def test_parse_notice_detects_specialty_occupation():
    text = "USCIS has determined the position is not a specialty occupation."
    detected = RFEResponseService.parse_notice(text)
    cats = [d["category"] for d in detected]
    assert "specialty_occupation" in cats


def test_parse_notice_detects_employer_employee_relationship():
    text = "The employer-employee relationship has not been demonstrated at the third-party worksite."
    detected = RFEResponseService.parse_notice(text)
    cats = [d["category"] for d in detected]
    assert "employer_employee_relationship" in cats


def test_parse_notice_detects_multiple_categories():
    text = (
        "The position is not a specialty occupation. Additionally, the employer-employee "
        "relationship has not been demonstrated. The beneficiary degree is unrelated to the position."
    )
    detected = RFEResponseService.parse_notice(text)
    cats = {d["category"] for d in detected}
    assert "specialty_occupation" in cats
    assert "employer_employee_relationship" in cats
    assert "degree_field_mismatch" in cats


def test_parse_notice_no_match_returns_empty():
    text = "This is some unrelated text about weather."
    detected = RFEResponseService.parse_notice(text)
    assert detected == []


def test_draft_response_creates_sections():
    ie, di, cw, rs = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"has_bachelors_or_higher": True})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    cw.record_filing(ws["id"], "WAC123", "2026-08-01")
    notice = "USCIS has determined the position is not a specialty occupation."
    draft = rs.draft_response(ws["id"], notice, rfe_received_date="2026-11-01")
    section_ids = [s["id"] for s in draft["sections"]]
    assert "cover" in section_ids
    assert "specialty_occupation" in section_ids
    assert "closing" in section_ids


def test_draft_computes_response_due_date():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    draft = rs.draft_response(ws["id"], "additional evidence requested", rfe_received_date="2026-11-01")
    assert draft["rfe_response_due_date"] is not None
    # 87 days after Nov 1 → Jan 27 next year
    assert draft["rfe_response_due_date"].startswith("2027-")


def test_draft_includes_no_match_section_when_nothing_detected():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    draft = rs.draft_response(ws["id"], "Random text with no patterns matched")
    section_ids = [s["id"] for s in draft["sections"]]
    assert "no_issues_detected" in section_ids


def test_draft_matches_exhibits():
    ie, di, cw, rs = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"has_bachelors_or_higher": True, "wage_level": "I"})
    di.upload("user-1", sess["id"], "lca.pdf", size_bytes=500_000, resolution_dpi=300)
    di.upload("user-1", sess["id"], "employment_letter.pdf", size_bytes=500_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    notice = "The position is not a specialty occupation."
    draft = rs.draft_response(ws["id"], notice)
    spec = next(s for s in draft["sections"] if s["id"] == "specialty_occupation")
    assert len(spec["matched_exhibits"]) >= 2


def test_wage_level_i_addendum_added_to_specialty_occupation():
    ie, di, cw, rs = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"wage_level": "I"})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    notice = "Position is not a specialty occupation."
    draft = rs.draft_response(ws["id"], notice)
    spec = next(s for s in draft["sections"] if s["id"] == "specialty_occupation")
    assert "Wage Level I" in spec["body"]


def test_citation_counts_in_stats():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    notice = "Position is not a specialty occupation. Bona fide marriage in question."
    draft = rs.draft_response(ws["id"], notice)
    assert draft["stats"]["verified_cites"] >= 1


def test_render_text_returns_full_letter():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.record_filing(ws["id"], "WAC1", "2026-08-01")
    draft = rs.draft_response(ws["id"], "Position is not a specialty occupation.", attorney_profile={"name": "Test"})
    text = RFEResponseService.render_text(draft)
    assert "RESPONSE" in text or "specialty occupation" in text.lower()
    assert "Test" in text  # attorney name


def test_render_review_text_includes_metadata():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    draft = rs.draft_response(ws["id"], "Position is not a specialty occupation.", rfe_received_date="2026-11-01")
    review = RFEResponseService.render_review_text(draft)
    assert "Categories detected" in review
    assert "RFE Response Draft" in review


def test_evidence_gap_status_when_no_matched_exhibits():
    ie, di, cw, rs = _make()
    sess = ie.start_session("user-1", "H-1B")
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    # No documents uploaded
    notice = "The position is not a specialty occupation."
    draft = rs.draft_response(ws["id"], notice)
    spec = next(s for s in draft["sections"] if s["id"] == "specialty_occupation")
    assert spec["status"] == "EVIDENCE_GAP"


def test_draft_persisted_and_listable():
    ie, di, cw, rs = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    draft = rs.draft_response(ws["id"], "Position is not a specialty occupation.")
    assert rs.get_draft(draft["id"])["id"] == draft["id"]
    assert len(rs.list_drafts(workspace_id=ws["id"])) == 1


def test_categories_listing_exposes_patterns():
    cats = RFEResponseService.list_categories()
    spec = next(c for c in cats if c["id"] == "specialty_occupation")
    assert spec["patterns"]
    assert "specialty occupation" in spec["patterns"][0]


def test_status_violation_detected():
    detected = RFEResponseService.parse_notice("Beneficiary went out of status; unauthorized employment occurred.")
    cats = [d["category"] for d in detected]
    assert "status_violation" in cats


def test_i864_deficiency_detected():
    detected = RFEResponseService.parse_notice("Sponsor income on the I-864 is below 125% poverty.")
    cats = [d["category"] for d in detected]
    assert "i864_deficiency" in cats
