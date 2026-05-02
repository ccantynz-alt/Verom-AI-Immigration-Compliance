"""Tests for the Support Letter Generator + bulk generation."""

from immigration_compliance.services.support_letter_service import (
    SupportLetterService,
    LETTER_TEMPLATES,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService


def _make():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    cw = CaseWorkspaceService(intake_engine=ie, document_intake=di)
    sl = SupportLetterService(case_workspace=cw, intake_engine=ie, document_intake=di)
    return ie, di, cw, sl


def test_letter_kinds_cover_major_types():
    expected = {
        "employer_support", "expert_opinion", "peer_recommendation",
        "reference_letter", "membership_attestation", "critical_role",
        "professor_endorsement",
    }
    assert expected <= set(LETTER_TEMPLATES.keys())


def test_list_letter_kinds_filters_by_visa():
    o1_kinds = SupportLetterService.list_letter_kinds(visa_type="O-1")
    h1b_kinds = SupportLetterService.list_letter_kinds(visa_type="H-1B")
    o1_ids = {k["id"] for k in o1_kinds}
    h1b_ids = {k["id"] for k in h1b_kinds}
    assert "expert_opinion" in o1_ids
    assert "expert_opinion" not in h1b_ids
    assert "employer_support" in h1b_ids


def test_employer_support_letter_includes_specialty_argument():
    ie, di, cw, sl = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {
        "first_name": "Wei", "last_name": "Chen",
        "petitioner_name": "TechCo", "position_title": "Senior Engineer",
        "wage_level": "III", "has_bachelors_or_higher": True,
    })
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    letter = sl.generate(ws["id"], "employer_support", author_profile={
        "name": "CEO", "industry": "tech", "field": "software engineering"
    })
    assert "TechCo" in letter["body"]
    assert "Senior Engineer" in letter["body"]
    assert "specialty occupation" in letter["body"].lower()


def test_expert_letter_with_criterion_focus():
    ie, di, cw, sl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {
        "first_name": "Wei", "last_name": "Chen",
        "criteria_awards": True, "criteria_publications": True,
    })
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    letter = sl.generate(ws["id"], "expert_opinion",
        author_profile={"name": "Dr. Smith", "field": "AI"},
        criterion_focus="criteria_awards",
    )
    assert letter["criterion_focus"] == "criteria_awards"
    assert "awards" in letter["body"].lower()


def test_eb1b_professor_endorsement_cites_eb1b_regulation():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "I-485", "US")
    letter = sl.generate(ws["id"], "professor_endorsement",
        author_profile={"name": "Dr. Chair", "institution": "MIT"})
    assert "204.5(i)" in letter["body"]


def test_bulk_generates_multiple_letters():
    ie, di, cw, sl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"first_name": "Wei", "last_name": "Chen"})
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    plan = [
        {"letter_kind": "expert_opinion", "author_profile": {"name": "Dr. Smith"}},
        {"letter_kind": "peer_recommendation", "author_profile": {"name": "Dr. Lee"}},
        {"letter_kind": "membership_attestation", "author_profile": {"name": "IEEE"}},
    ]
    bulk = sl.generate_bulk(ws["id"], plan)
    assert bulk["total_requested"] == 3
    assert bulk["succeeded"] == 3
    assert bulk["failed"] == 0


def test_bulk_records_failure_for_invalid_kind():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    plan = [
        {"letter_kind": "expert_opinion", "author_profile": {"name": "Dr."}},
        {"letter_kind": "fake_kind", "author_profile": {"name": "Z"}},
    ]
    bulk = sl.generate_bulk(ws["id"], plan)
    assert bulk["succeeded"] == 1
    assert bulk["failed"] == 1


def test_unknown_letter_kind_rejected():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    try:
        sl.generate(ws["id"], "fake_letter")
        assert False
    except ValueError:
        pass


def test_letters_persisted_and_listable():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    l1 = sl.generate(ws["id"], "expert_opinion")
    l2 = sl.generate(ws["id"], "peer_recommendation")
    assert sl.get_letter(l1["id"])["id"] == l1["id"]
    all_l = sl.list_letters(workspace_id=ws["id"])
    assert len(all_l) == 2
    experts = sl.list_letters(letter_kind="expert_opinion")
    assert len(experts) == 1


def test_render_text_returns_letter_body():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    letter = sl.generate(ws["id"], "expert_opinion", author_profile={"name": "Dr. X"})
    text = SupportLetterService.render_text(letter)
    assert "Dr. X" in text


def test_render_review_text_includes_metadata():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    letter = sl.generate(ws["id"], "expert_opinion")
    review = SupportLetterService.render_review_text(letter)
    assert "Citations:" in review
    assert "Words:" in review


def test_facts_pulled_from_intake_and_passport():
    ie, di, cw, sl = _make()
    sess = ie.start_session("user-1", "O-1")
    ie.submit_answers(sess["id"], {"first_name": "Wei", "last_name": "Chen"})
    di.upload("user-1", sess["id"], "passport.pdf", size_bytes=500_000, resolution_dpi=300)
    ws = cw.create_workspace("user-1", "O-1", "US", intake_session_id=sess["id"])
    letter = sl.generate(ws["id"], "expert_opinion")
    # Facts contain extracted passport data
    assert letter["facts"]["beneficiary_name"]


def test_critical_role_letter_includes_role_section():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    letter = sl.generate(ws["id"], "critical_role", author_profile={
        "organization_name": "Distinguished Org", "role": "Lead Engineer", "start_date": "2020-01-01"
    })
    assert "Distinguished Org" in letter["body"]
    assert "Lead Engineer" in letter["body"]


def test_membership_letter_includes_organization():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    letter = sl.generate(ws["id"], "membership_attestation", author_profile={
        "organization_name": "IEEE",
    })
    assert "IEEE" in letter["body"]


def test_get_template_returns_spec():
    t = SupportLetterService.get_template("expert_opinion")
    assert t is not None
    assert t["name"] == "Expert Opinion Letter"


def test_custom_facts_override_defaults():
    ie, di, cw, sl = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    letter = sl.generate(ws["id"], "expert_opinion", custom_facts={"beneficiary_name": "OVERRIDE"})
    assert letter["facts"]["beneficiary_name"] == "OVERRIDE"
    assert "OVERRIDE" in letter["body"]
