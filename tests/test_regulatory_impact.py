"""Tests for the Regulatory Impact Hook — predicate evaluation + impact reports."""

from immigration_compliance.services.regulatory_impact_service import (
    RegulatoryImpactService,
    evaluate_predicate,
    _resolve_path,
    EVENT_KINDS,
    SEVERITY_LEVELS,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService


def _make():
    ie = IntakeEngineService()
    cw = CaseWorkspaceService(intake_engine=ie)
    ri = RegulatoryImpactService(case_workspace=cw)
    return ie, cw, ri


def test_resolve_path_walks_dotted_keys():
    snap = {"workspace": {"visa_type": "H-1B", "country": "US"}}
    assert _resolve_path(snap, "workspace.visa_type") == "H-1B"
    assert _resolve_path(snap, "workspace.country") == "US"
    assert _resolve_path(snap, "workspace.missing") is None


def test_evaluate_simple_equality_predicate():
    snap = {"workspace": {"visa_type": "H-1B"}}
    ok, ev = evaluate_predicate({"field": "workspace.visa_type", "op": "==", "value": "H-1B"}, snap)
    assert ok is True
    assert ev[0]["actual"] == "H-1B"


def test_evaluate_in_predicate():
    snap = {"workspace": {"visa_type": "L-1"}}
    ok, _ = evaluate_predicate({"field": "workspace.visa_type", "op": "in", "value": ["H-1B", "L-1"]}, snap)
    assert ok is True


def test_evaluate_all_of_compound():
    snap = {"workspace": {"visa_type": "H-1B", "country": "US"}}
    pred = {
        "all_of": [
            {"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
            {"field": "workspace.country", "op": "==", "value": "US"},
        ]
    }
    ok, _ = evaluate_predicate(pred, snap)
    assert ok is True


def test_evaluate_all_of_with_one_failing_returns_false():
    snap = {"workspace": {"visa_type": "H-1B", "country": "US"}}
    pred = {
        "all_of": [
            {"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
            {"field": "workspace.country", "op": "==", "value": "UK"},
        ]
    }
    ok, _ = evaluate_predicate(pred, snap)
    assert ok is False


def test_evaluate_any_of():
    snap = {"workspace": {"visa_type": "H-1B"}}
    pred = {"any_of": [
        {"field": "workspace.visa_type", "op": "==", "value": "L-1"},
        {"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
    ]}
    ok, _ = evaluate_predicate(pred, snap)
    assert ok is True


def test_evaluate_not_inverts():
    snap = {"workspace": {"visa_type": "H-1B"}}
    pred = {"not": {"field": "workspace.visa_type", "op": "==", "value": "L-1"}}
    ok, _ = evaluate_predicate(pred, snap)
    assert ok is True


def test_evaluate_exists():
    snap = {"workspace": {"visa_type": "H-1B"}}
    ok, _ = evaluate_predicate({"field": "workspace.visa_type", "op": "exists"}, snap)
    assert ok is True
    ok2, _ = evaluate_predicate({"field": "workspace.missing", "op": "exists"}, snap)
    assert ok2 is False


def test_evaluate_contains_string():
    snap = {"workspace": {"label": "H-1B Chen 2026"}}
    ok, _ = evaluate_predicate({"field": "workspace.label", "op": "contains", "value": "Chen"}, snap)
    assert ok is True


def test_ingest_event_validates_kind_and_severity():
    _, _, ri = _make()
    try:
        ri.ingest_event("X", "not-a-kind", {"field": "workspace.visa_type", "op": "==", "value": "H-1B"})
        assert False
    except ValueError:
        pass
    try:
        ri.ingest_event("X", "policy_memo", {"field": "x", "op": "==", "value": 1}, severity="bogus")
        assert False
    except ValueError:
        pass


def test_analyze_event_finds_matching_workspaces():
    ie, cw, ri = _make()
    cw.create_workspace("user-1", "H-1B", "US")
    cw.create_workspace("user-2", "H-1B", "US")
    cw.create_workspace("user-3", "O-1", "US")
    ev = ri.ingest_event(
        "H-1B scrutiny", "policy_memo",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
        severity="action_required",
    )
    report = ri.analyze_event(ev["id"])
    assert report["affected_count"] == 2
    assert report["scanned_count"] == 3


def test_analyze_event_excludes_closed_cases_by_default():
    ie, cw, ri = _make()
    ws1 = cw.create_workspace("user-1", "H-1B", "US")
    ws2 = cw.create_workspace("user-2", "H-1B", "US")
    cw.update_status(ws2["id"], "approved", "decided")
    ev = ri.ingest_event(
        "H-1B alert", "policy_memo",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
    )
    report = ri.analyze_event(ev["id"], only_active=True)
    # Only the active one should be scanned and affected
    assert report["scanned_count"] == 1


def test_analyze_event_includes_closed_when_only_active_false():
    ie, cw, ri = _make()
    ws1 = cw.create_workspace("user-1", "H-1B", "US")
    ws2 = cw.create_workspace("user-2", "H-1B", "US")
    cw.update_status(ws2["id"], "approved", "decided")
    ev = ri.ingest_event("H-1B alert", "policy_memo",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"})
    report = ri.analyze_event(ev["id"], only_active=False)
    assert report["scanned_count"] == 2


def test_each_affected_case_has_evidence_and_drafts():
    ie, cw, ri = _make()
    cw.create_workspace("user-1", "H-1B", "US")
    ev = ri.ingest_event("X", "policy_memo",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"})
    report = ri.analyze_event(ev["id"])
    a = report["affected"][0]
    assert "evidence" in a
    assert "draft_client_notification" in a
    assert "draft_attorney_action" in a


def test_attorney_action_severity_text_blocking():
    ie, cw, ri = _make()
    cw.create_workspace("user-1", "H-1B", "US")
    ev = ri.ingest_event("Critical change", "rule_change",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"},
        severity="blocking")
    report = ri.analyze_event(ev["id"])
    a = report["affected"][0]
    assert "BLOCKING" in a["draft_attorney_action"]


def test_list_events_filters_by_kind_and_severity():
    _, _, ri = _make()
    ri.ingest_event("A", "policy_memo", {"field": "workspace.visa_type", "op": "==", "value": "H-1B"})
    ri.ingest_event("B", "fee_change", {"field": "workspace.visa_type", "op": "==", "value": "H-1B"}, severity="action_required")
    only_fee = ri.list_events(kind="fee_change")
    assert len(only_fee) == 1
    only_action = ri.list_events(severity="action_required")
    assert len(only_action) == 1


def test_event_kinds_and_severity_constants_exposed():
    assert "policy_memo" in EVENT_KINDS
    assert "blocking" in SEVERITY_LEVELS
    kinds = RegulatoryImpactService.list_event_kinds()
    severities = RegulatoryImpactService.list_severity_levels()
    assert len(kinds) >= 6
    assert len(severities) == 4


def test_list_reports_for_attorney_filters():
    ie, cw, ri = _make()
    cw.create_workspace("user-1", "H-1B", "US", attorney_id="atty-1")
    cw.create_workspace("user-2", "H-1B", "US", attorney_id="atty-2")
    ev = ri.ingest_event("X", "policy_memo",
        impact_predicate={"field": "workspace.visa_type", "op": "==", "value": "H-1B"})
    ri.analyze_event(ev["id"])
    atty_1_reports = ri.list_reports(attorney_id="atty-1")
    assert len(atty_1_reports) == 1
