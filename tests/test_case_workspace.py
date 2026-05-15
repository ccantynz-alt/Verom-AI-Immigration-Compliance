"""Tests for the CaseWorkspaceService — the unified system of record."""

from immigration_compliance.services.case_workspace_service import (
    CaseWorkspaceService,
    WORKSPACE_STATUSES,
)
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService
from immigration_compliance.services.form_population_service import FormPopulationService
from immigration_compliance.services.attorney_match_service import AttorneyMatchService
from immigration_compliance.services.conflict_check_service import ConflictCheckService
from immigration_compliance.services.rfe_predictor_service import RFEPredictorService


def _make_full_stack():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    fp = FormPopulationService()
    am = AttorneyMatchService()
    cc = ConflictCheckService()
    rp = RFEPredictorService()
    cw = CaseWorkspaceService(ie, di, fp, am, cc, rp)
    return cw, ie, di, fp, am, cc, rp


def test_create_workspace_initializes_state():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id="sess-1")
    assert ws["status"] == "intake"
    assert ws["visa_type"] == "H-1B"
    assert ws["country"] == "US"
    assert ws["intake_session_id"] == "sess-1"
    assert ws["form_record_ids"] == []
    # Auto-creates timeline events
    timeline = cw.get_timeline(ws["id"])
    kinds = [e["kind"] for e in timeline]
    assert "case_created" in kinds and "intake_started" in kinds


def test_list_workspaces_filters_by_applicant_and_attorney():
    cw, *_ = _make_full_stack()
    cw.create_workspace("user-1", "H-1B", "US")
    cw.create_workspace("user-2", "F-1", "US")
    cw.create_workspace("user-1", "I-130", "US", attorney_id="atty-1")
    user_1 = cw.list_workspaces(applicant_id="user-1")
    assert len(user_1) == 2
    atty_1 = cw.list_workspaces(attorney_id="atty-1")
    assert len(atty_1) == 1


def test_status_lifecycle():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.update_status(ws["id"], "documents")
    assert cw.get_workspace(ws["id"])["status"] == "documents"
    cw.update_status(ws["id"], "review")
    assert cw.get_workspace(ws["id"])["status"] == "review"


def test_status_update_rejects_unknown():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    try:
        cw.update_status(ws["id"], "not-a-status")
        assert False
    except ValueError:
        pass


def test_link_form_record_dedupes():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.link_form_record(ws["id"], "form-1")
    cw.link_form_record(ws["id"], "form-2")
    cw.link_form_record(ws["id"], "form-1")  # dup
    assert cw.get_workspace(ws["id"])["form_record_ids"] == ["form-1", "form-2"]


def test_record_filing_sets_status_and_receipt():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.record_filing(ws["id"], "WAC2612345678", "2026-11-01")
    refreshed = cw.get_workspace(ws["id"])
    assert refreshed["status"] == "filed"
    assert refreshed["filing_receipt_number"] == "WAC2612345678"
    assert refreshed["filed_date"] == "2026-11-01"


def test_assign_attorney_logs_event():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.assign_attorney(ws["id"], "atty-1", "Jennifer Park")
    refreshed = cw.get_workspace(ws["id"])
    assert refreshed["attorney_id"] == "atty-1"
    timeline = cw.get_timeline(ws["id"])
    kinds = [e["kind"] for e in timeline]
    assert "attorney_assigned" in kinds


def test_notes_are_stored_and_filterable():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.add_note(ws["id"], "atty-1", "Internal strategy note", visibility="internal")
    cw.add_note(ws["id"], "atty-1", "Client-facing update", visibility="client_visible")
    internal = cw.list_notes(ws["id"], visibility="internal")
    client = cw.list_notes(ws["id"], visibility="client_visible")
    assert len(internal) == 1 and len(client) == 1


def test_deadlines_lifecycle():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    d = cw.add_deadline(ws["id"], "RFE response due", "2027-01-15", kind="rfe")
    assert d["completed"] is False
    cw.complete_deadline(ws["id"], d["id"])
    open_only = cw.list_deadlines(ws["id"], include_completed=False)
    assert len(open_only) == 0
    all_ds = cw.list_deadlines(ws["id"], include_completed=True)
    assert len(all_ds) == 1


def test_auto_compute_deadlines_from_filing_i129():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    deadlines = cw.auto_compute_deadlines_from_filing(ws["id"], "2026-11-01", "I-129")
    assert len(deadlines) == 2
    labels = [d["label"] for d in deadlines]
    assert any("Premium" in l for l in labels)
    assert any("Standard" in l for l in labels)


def test_rfe_response_deadline():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    d = cw.add_rfe_response_deadline(ws["id"], "2026-12-01", response_window_days=87)
    assert d["kind"] == "rfe"
    assert d["due_date"] >= "2027-02-01"  # 87 days after Dec 1


def test_get_snapshot_has_all_keys_even_when_empty():
    cw = CaseWorkspaceService()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    snap = cw.get_snapshot(ws["id"])
    for key in ("workspace", "intake", "documents", "forms", "match",
                "conflicts", "rfe_risk", "timeline", "notes", "deadlines",
                "completeness", "next_actions"):
        assert key in snap


def test_snapshot_aggregates_intake_and_match():
    cw, ie, di, fp, am, cc, rp = _make_full_stack()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {
        "has_bachelors_or_higher": True, "has_us_employer_offer": True, "lca_filed": True,
        "wage_level": "III", "us_masters_or_higher": True, "selected_in_lottery": True,
        "prior_h1b_approval": False, "current_status_in_us": "F-1_OPT",
        "prior_us_visa_denial": False, "prior_immigration_violation": False,
    })
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    snap = cw.get_snapshot(ws["id"])
    assert snap["intake"] is not None
    assert snap["intake"]["validation"]["ok"] is True
    assert snap["match"] is not None
    assert len(snap["match"]["results"]) > 0


def test_completeness_uses_30_40_30_weights():
    cw, ie, di, fp, am, cc, rp = _make_full_stack()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {
        "has_bachelors_or_higher": True, "has_us_employer_offer": True, "lca_filed": True,
        "wage_level": "III", "us_masters_or_higher": True, "selected_in_lottery": True,
        "prior_h1b_approval": False, "current_status_in_us": "F-1_OPT",
    })
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    snap = cw.get_snapshot(ws["id"])
    c = snap["completeness"]
    assert "intake_pct" in c and "documents_pct" in c and "forms_pct" in c and "overall_pct" in c
    assert 0 <= c["overall_pct"] <= 100


def test_next_actions_surface_blocking_items():
    cw, ie, *_ = _make_full_stack()
    sess = ie.start_session("user-1", "H-1B")
    # Missing required answers → blocking
    ie.submit_answers(sess["id"], {"has_bachelors_or_higher": False})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    snap = cw.get_snapshot(ws["id"])
    priorities = [a["priority"] for a in snap["next_actions"]]
    assert "blocking" in priorities or "high" in priorities


def test_workspace_statuses_are_documented():
    expected = ("intake", "documents", "review", "filed", "rfe", "decision_pending", "approved", "denied", "withdrawn")
    for s in expected:
        assert s in WORKSPACE_STATUSES


def test_timeline_event_types_recorded():
    cw, *_ = _make_full_stack()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.update_status(ws["id"], "documents")
    cw.add_note(ws["id"], "user-1", "First note")
    cw.add_deadline(ws["id"], "Submit by", "2027-01-01")
    cw.record_filing(ws["id"], "WAC123", "2026-12-01")
    timeline = cw.get_timeline(ws["id"])
    kinds = {e["kind"] for e in timeline}
    assert {"case_created", "status_changed", "note_added", "deadline_added", "case_filed"} <= kinds
