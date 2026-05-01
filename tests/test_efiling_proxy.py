"""Tests for the Government E-Filing Proxy."""

from immigration_compliance.services.efiling_proxy_service import (
    EFilingProxyService,
    PORTALS,
    SUBMISSION_STATES,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.form_population_service import FormPopulationService


def test_portals_cover_all_major_agencies():
    expected = {"uscis", "dol_flag", "dos_ceac", "eoir_ecas"}
    assert expected <= set(PORTALS.keys())


def test_uscis_supports_major_forms():
    spec = PORTALS["uscis"]
    forms = set(spec["supported_forms"])
    assert {"I-129", "I-130", "I-485", "I-765", "I-131"} <= forms


def test_find_portal_for_form():
    assert EFilingProxyService.find_portal_for_form("I-129") == "uscis"
    assert EFilingProxyService.find_portal_for_form("ETA-9035") == "dol_flag"
    assert EFilingProxyService.find_portal_for_form("DS-160") == "dos_ceac"
    assert EFilingProxyService.find_portal_for_form("EOIR-26") == "eoir_ecas"
    assert EFilingProxyService.find_portal_for_form("FAKE-FORM") is None


def test_create_submission():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=True, attachments=[{"f": "lca.pdf"}])
    assert s["state"] == "draft"
    assert s["portal"] == "uscis"
    assert len(s["events"]) == 1


def test_create_submission_unknown_portal_rejected():
    svc = EFilingProxyService()
    try:
        svc.create_submission(portal="fake", form_id="I-129")
        assert False
    except ValueError:
        pass


def test_create_submission_form_not_supported_rejected():
    svc = EFilingProxyService()
    try:
        svc.create_submission(portal="uscis", form_id="ETA-9035")  # DOL form, not USCIS
        assert False
    except ValueError:
        pass


def test_validate_unsigned_blocks():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=False, attachments=[{"f": "a"}])
    val = svc.validate_submission(s["id"])
    assert any(i["code"] == "UNSIGNED" and i["severity"] == "blocking" for i in val["validation_issues"])


def test_validate_missing_attachments_blocks_when_required():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=True, attachments=[])
    val = svc.validate_submission(s["id"])
    assert any(i["code"] == "MISSING_ATTACHMENTS" for i in val["validation_issues"])


def test_dos_ceac_does_not_require_attachments():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="dos_ceac", form_id="DS-160", signed=True, attachments=[])
    val = svc.validate_submission(s["id"])
    assert not any(i["code"] == "MISSING_ATTACHMENTS" for i in val["validation_issues"])


def test_submit_with_blocking_issues_raises():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=False, attachments=[{"f": "a"}])
    try:
        svc.submit(s["id"])
        assert False
    except ValueError:
        pass


def test_successful_submission_returns_receipt():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=True, attachments=[{"f": "a"}])
    result = svc.submit(s["id"])
    assert result["state"] == "submitted"
    assert result["receipt_number"] is not None
    assert EFilingProxyService.validate_receipt_format("uscis", result["receipt_number"])


def test_submission_auto_links_to_workspace():
    cw = CaseWorkspaceService()
    fp = FormPopulationService()
    svc = EFilingProxyService(case_workspace=cw, form_population=fp)
    ws = cw.create_workspace("user-1", "H-1B", "US")
    s = svc.create_submission(
        portal="uscis", form_id="I-129", workspace_id=ws["id"],
        signed=True, attachments=[{"f": "a"}],
    )
    svc.submit(s["id"])
    refreshed = cw.get_workspace(ws["id"])
    assert refreshed["filing_receipt_number"] is not None


def test_acknowledge_updates_state():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=True, attachments=[{"f": "a"}])
    svc.submit(s["id"])
    ack = svc.acknowledge(s["id"], {"receipt_number": "WAC2612345678"})
    assert ack["state"] == "acknowledged"
    assert ack["receipt_number"] == "WAC2612345678"


def test_form_completeness_checked():
    cw = CaseWorkspaceService()
    fp = FormPopulationService()
    svc = EFilingProxyService(case_workspace=cw, form_population=fp)
    # Populate an incomplete form
    rec = fp.populate("I-129", "user-1", intake_answers={}, extracted_documents=[])
    s = svc.create_submission(
        portal="uscis", form_id="I-129", form_record_id=rec["id"],
        signed=True, attachments=[{"f": "a"}],
    )
    val = svc.validate_submission(s["id"])
    # Should flag form as incomplete
    assert any(i["code"] == "FORM_INCOMPLETE" for i in val["validation_issues"])


def test_list_submissions_filters():
    svc = EFilingProxyService()
    svc.create_submission(portal="uscis", form_id="I-129", attorney_id="atty-1")
    svc.create_submission(portal="dol_flag", form_id="ETA-9035", attorney_id="atty-1")
    svc.create_submission(portal="uscis", form_id="I-130", attorney_id="atty-2")
    uscis_only = svc.list_submissions(portal="uscis")
    assert len(uscis_only) == 2
    atty_1 = svc.list_submissions(attorney_id="atty-1")
    assert len(atty_1) == 2


def test_validate_receipt_format_per_portal():
    assert EFilingProxyService.validate_receipt_format("uscis", "WAC2612345678") is True
    assert EFilingProxyService.validate_receipt_format("uscis", "INVALID") is False
    assert EFilingProxyService.validate_receipt_format("dol_flag", "I-200-12345-678901") is True
    assert EFilingProxyService.validate_receipt_format("dos_ceac", "AA12345678") is True
    assert EFilingProxyService.validate_receipt_format("eoir_ecas", "123456789") is True


def test_submission_states_constant():
    assert "draft" in SUBMISSION_STATES
    assert "submitted" in SUBMISSION_STATES
    assert "acknowledged" in SUBMISSION_STATES
    assert "rejected" in SUBMISSION_STATES


def test_portals_listing():
    portals = EFilingProxyService.list_portals()
    ids = {p["id"] for p in portals}
    assert ids == set(PORTALS.keys())


def test_events_log_each_state_change():
    svc = EFilingProxyService()
    s = svc.create_submission(portal="uscis", form_id="I-129", signed=True, attachments=[{"f": "a"}])
    svc.validate_submission(s["id"])
    svc.submit(s["id"])
    refreshed = svc.get_submission(s["id"])
    states = [e["state"] for e in refreshed["events"]]
    assert "draft" in states
    assert "validating" in states
    assert "submitted" in states


def test_eoir_ecas_court_filing():
    svc = EFilingProxyService()
    s = svc.create_submission(
        portal="eoir_ecas", form_id="EOIR-26",
        signed=True, attachments=[{"f": "brief.pdf"}],
    )
    submitted = svc.submit(s["id"])
    assert submitted["receipt_number"]
    assert EFilingProxyService.validate_receipt_format("eoir_ecas", submitted["receipt_number"])
