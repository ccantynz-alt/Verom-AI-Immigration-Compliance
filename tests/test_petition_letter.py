"""Tests for the Petition Letter Generator."""

from immigration_compliance.services.petition_letter_service import (
    PetitionLetterService,
    PETITION_SPECS,
    CITATION_VERIFIED,
    INSUFFICIENT_EVIDENCE,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService


def _make():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    cw = CaseWorkspaceService(intake_engine=ie, document_intake=di)
    pl = PetitionLetterService(case_workspace=cw, intake_engine=ie, document_intake=di)
    return ie, di, cw, pl


def test_petition_specs_cover_major_kinds():
    assert {"O-1A", "EB-1A", "EB-2-NIW", "H-1B", "L-1A"} <= set(PETITION_SPECS.keys())


def test_list_supported_petitions():
    pets = PetitionLetterService.list_supported_petitions()
    ids = {p["id"] for p in pets}
    assert "O-1A" in ids
    for p in pets:
        assert p["statutory_basis"] and p["regulatory_basis"]


def test_o1a_draft_has_all_sections():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {
        "criteria_awards": True, "criteria_membership": True, "criteria_press": True,
        "first_name": "Wei", "last_name": "Chen",
    })
    di.upload("user-1", sess["id"], "passport.pdf", size_bytes=2_000_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "O-1A")
    section_ids = [s["id"] for s in draft["sections"]]
    assert "header" in section_ids
    assert "introduction" in section_ids
    assert "beneficiary_background" in section_ids
    assert "legal_standard" in section_ids
    assert "criteria_overview" in section_ids
    assert "conclusion" in section_ids


def test_o1a_draft_satisfied_criteria_included():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {
        "criteria_awards": True, "criteria_membership": False, "criteria_press": True,
    })
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "O-1A")
    section_ids = [s["id"] for s in draft["sections"]]
    # Awards (satisfied) is included; Membership (not satisfied) is excluded by default
    assert "criteria_awards" in section_ids
    assert "criteria_membership" not in section_ids


def test_force_include_weak_sections():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"criteria_awards": False})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    forced = pl.generate(ws["id"], "O-1A", force_include_weak_sections=True)
    section_ids = [s["id"] for s in forced["sections"]]
    assert "criteria_awards" in section_ids
    awards_section = next(s for s in forced["sections"] if s["id"] == "criteria_awards")
    assert awards_section["status"] == "INSUFFICIENT_EVIDENCE"


def test_eb2niw_uses_dhanasar_prongs():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "I-485")
    ie.submit_answers(sess["id"], {"prong_1": True, "prong_2": True, "prong_3": False})
    ws = cw.create_workspace("user-1", "I-485", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "EB-2-NIW")
    section_ids = [s["id"] for s in draft["sections"]]
    assert "prong_1" in section_ids and "prong_2" in section_ids and "prong_3" in section_ids
    prong_3 = next(s for s in draft["sections"] if s["id"] == "prong_3")
    assert prong_3["status"] == "INSUFFICIENT_EVIDENCE"


def test_h1b_draft_includes_specialty_occupation():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {
        "has_bachelors_or_higher": True, "us_masters_or_higher": True, "wage_level": "III",
    })
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "H-1B")
    section_ids = [s["id"] for s in draft["sections"]]
    assert "specialty_occupation" in section_ids
    assert "qualifications" in section_ids


def test_h1b_wage_level_i_triggers_pending_citation():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"has_bachelors_or_higher": True, "wage_level": "I"})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "H-1B")
    spec_section = next(s for s in draft["sections"] if s["id"] == "specialty_occupation")
    # Wage Level I → adds a pending citation
    assert spec_section["pending_cites"] >= 1


def test_l1a_draft_lists_elements():
    ie, di, cw, pl = _make()
    # L-1 isn't in the intake registry; workspace can still be created without intake session
    ws = cw.create_workspace("user-1", "L-1", "US")
    draft = pl.generate(ws["id"], "L-1A")
    section_ids = [s["id"] for s in draft["sections"]]
    assert any(s.startswith("element_") for s in section_ids)


def test_unknown_petition_kind_rejected():
    ie, di, cw, pl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    try:
        pl.generate(ws["id"], "FAKE-PETITION")
        assert False
    except ValueError:
        pass


def test_legal_standard_uses_verified_citations():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"criteria_awards": True, "criteria_press": True, "criteria_publications": True})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "O-1A")
    legal = next(s for s in draft["sections"] if s["id"] == "legal_standard")
    assert CITATION_VERIFIED in legal["body"]


def test_render_text_concatenates_sections():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"criteria_awards": True})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "O-1A")
    text = PetitionLetterService.render_text(draft)
    assert "INTRODUCTION" in text
    assert "CONCLUSION" in text


def test_render_review_text_includes_status_lines():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"criteria_awards": True})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "O-1A")
    review = PetitionLetterService.render_review_text(draft)
    assert "cites:" in review
    assert "Sections:" in review


def test_eb1a_draft_uses_kazarian_framework():
    ie, di, cw, pl = _make()
    sess = ie.start_session("user-1", "I-485")
    ie.submit_answers(sess["id"], {"criteria_awards": True, "criteria_press": True, "criteria_publications": True})
    ws = cw.create_workspace("user-1", "I-485", "US", intake_session_id=sess["id"])
    draft = pl.generate(ws["id"], "EB-1A")
    legal = next(s for s in draft["sections"] if s["id"] == "legal_standard")
    assert "Kazarian" in legal["body"]


def test_draft_persisted_and_listable():
    ie, di, cw, pl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    draft = pl.generate(ws["id"], "O-1A")
    assert pl.get_draft(draft["id"])["id"] == draft["id"]
    assert len(pl.list_drafts(workspace_id=ws["id"])) == 1


def test_attorney_profile_in_header():
    ie, di, cw, pl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    draft = pl.generate(ws["id"], "O-1A", attorney_profile={"name": "Jennifer Park", "firm": "Park Immigration"})
    header = next(s for s in draft["sections"] if s["id"] == "header")
    assert "Jennifer Park" in header["body"]
    assert "Park Immigration" in header["body"]
