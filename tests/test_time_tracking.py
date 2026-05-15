"""Tests for the Time Tracking + Billable Hours service."""

from immigration_compliance.services.time_tracking_service import (
    TimeTrackingService,
    ACTIVITY_DEFAULTS,
)


def test_activity_defaults_cover_immigration_workflow():
    expected = {
        "petition_letter_drafting", "rfe_response_drafting", "form_drafting",
        "client_communication", "research", "filing_prep", "consultation",
    }
    assert expected <= set(ACTIVITY_DEFAULTS.keys())


def test_set_billing_rate():
    svc = TimeTrackingService()
    rate = svc.set_billing_rate("atty-1", 350.0)
    assert rate["rate_per_hour"] == 350.0
    assert svc.get_billing_rate("atty-1") == rate


def test_negative_rate_rejected():
    svc = TimeTrackingService()
    try:
        svc.set_billing_rate("atty-1", -100)
        assert False
    except ValueError:
        pass


def test_add_billable_entry_calculates_amount():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    entry = svc.add_entry("atty-1", minutes=60, activity_type="petition_letter_drafting", workspace_id="ws-1")
    assert entry["billable"] is True
    assert entry["amount"] == 300.0


def test_non_billable_activity_zero_amount():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    entry = svc.add_entry("atty-1", minutes=30, activity_type="case_administration", workspace_id="ws-1")
    assert entry["billable"] is False
    assert entry["amount"] == 0.0


def test_billable_override():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    # Override a non-billable activity to billable
    entry = svc.add_entry("atty-1", minutes=30, activity_type="case_administration", billable_override=True)
    assert entry["billable"] is True
    assert entry["amount"] == 150.0


def test_no_rate_set_yields_zero_amount():
    svc = TimeTrackingService()
    entry = svc.add_entry("atty-1", minutes=60, activity_type="petition_letter_drafting")
    assert entry["amount"] == 0.0


def test_negative_minutes_rejected():
    svc = TimeTrackingService()
    try:
        svc.add_entry("atty-1", minutes=-1, activity_type="other")
        assert False
    except ValueError:
        pass


def test_unknown_activity_type_rejected():
    svc = TimeTrackingService()
    try:
        svc.add_entry("atty-1", minutes=10, activity_type="not-a-type")
        assert False
    except ValueError:
        pass


def test_timer_start_and_stop():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    t = svc.start_timer("atty-1", workspace_id="ws-1", activity_type="research", description="case law")
    assert t["is_running"] is True
    stopped = svc.stop_timer(t["id"])
    assert stopped["is_running"] is False
    # An entry was created
    entries = svc.list_entries(attorney_id="atty-1")
    assert len(entries) == 1


def test_active_timer_lookup():
    svc = TimeTrackingService()
    svc.start_timer("atty-1", activity_type="other")
    active = svc.get_active_timer("atty-1")
    assert active is not None
    assert active["attorney_id"] == "atty-1"


def test_starting_new_timer_stops_existing():
    svc = TimeTrackingService()
    t1 = svc.start_timer("atty-1", activity_type="research")
    t2 = svc.start_timer("atty-1", activity_type="case_review")
    assert t1["id"] != t2["id"]
    # Original timer was auto-stopped
    refreshed = svc.list_timers(attorney_id="atty-1")
    stopped = [t for t in refreshed if not t["is_running"]]
    assert len(stopped) == 1


def test_auto_log_uses_default_minutes():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    entry = svc.auto_log_activity("atty-1", "petition_letter_drafting", workspace_id="ws-1")
    assert entry["minutes"] == 90  # default for petition_letter_drafting
    assert entry["source"] == "auto"


def test_workspace_summary_aggregates_billable_and_non_billable():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 200.0)
    svc.add_entry("atty-1", minutes=60, activity_type="research", workspace_id="ws-1")
    svc.add_entry("atty-1", minutes=30, activity_type="case_administration", workspace_id="ws-1")
    s = svc.workspace_summary("ws-1")
    assert s["billable_hours"] == 1.0
    assert s["non_billable_hours"] == 0.5
    assert s["total_amount"] == 200.0


def test_invoice_generation():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 250.0)
    svc.add_entry("atty-1", minutes=60, activity_type="research", workspace_id="ws-1")
    svc.add_entry("atty-1", minutes=30, activity_type="case_administration", workspace_id="ws-1")  # non-billable
    inv = svc.generate_invoice("ws-1", attorney_id="atty-1")
    # Only billable entry included
    assert len(inv["entries"]) == 1
    assert inv["subtotal"] == 250.0


def test_update_entry_recomputes_amount():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 200.0)
    entry = svc.add_entry("atty-1", minutes=30, activity_type="research")
    updated = svc.update_entry(entry["id"], minutes=60)
    assert updated["minutes"] == 60.0
    assert updated["amount"] == 200.0


def test_delete_entry():
    svc = TimeTrackingService()
    e = svc.add_entry("atty-1", minutes=30, activity_type="research")
    assert svc.delete_entry(e["id"]) is True
    assert svc.delete_entry("non-existent") is False


def test_list_entries_filters():
    svc = TimeTrackingService()
    svc.add_entry("atty-1", minutes=30, activity_type="research", workspace_id="ws-1")
    svc.add_entry("atty-1", minutes=15, activity_type="case_administration", workspace_id="ws-2")
    ws1 = svc.list_entries(workspace_id="ws-1")
    assert len(ws1) == 1
    billable_only = svc.list_entries(billable=True)
    assert all(e["billable"] for e in billable_only)
    non_billable_only = svc.list_entries(billable=False)
    assert all(not e["billable"] for e in non_billable_only)


def test_attorney_summary_with_date_range():
    svc = TimeTrackingService()
    svc.set_billing_rate("atty-1", 300.0)
    svc.add_entry("atty-1", minutes=60, activity_type="research", entry_date="2026-01-15")
    svc.add_entry("atty-1", minutes=30, activity_type="research", entry_date="2026-02-15")
    feb = svc.attorney_summary("atty-1", since="2026-02-01", until="2026-02-28")
    assert feb["entry_count"] == 1
    jan = svc.attorney_summary("atty-1", until="2026-01-31")
    assert jan["entry_count"] == 1


def test_activity_types_listing_includes_all():
    types = TimeTrackingService.list_activity_types()
    assert len(types) == len(ACTIVITY_DEFAULTS)
    for t in types:
        assert "type" in t and "label" in t and "billable_default" in t
