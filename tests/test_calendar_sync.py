"""Tests for the Calendar Sync service — ICS generation + subscriptions + OAuth stubs."""

from immigration_compliance.services.calendar_sync_service import (
    CalendarSyncService,
    IcsEvent,
    render_calendar,
    PROVIDER_CHOICES,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService


def _make_pair():
    cw = CaseWorkspaceService()
    cs = CalendarSyncService(case_workspace=cw, base_url="https://verom.ai")
    return cw, cs


def test_render_empty_calendar_is_valid():
    ics = render_calendar([], calendar_name="Test")
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip("\r\n").endswith("END:VCALENDAR")
    assert "PRODID:-//Verom" in ics


def test_render_event_includes_alarms():
    e = IcsEvent(uid="abc@verom.ai", summary="Filing due", due_date="2026-12-01")
    ics = render_calendar([e])
    assert "BEGIN:VEVENT" in ics and "END:VEVENT" in ics
    assert "TRIGGER:-P1D" in ics  # 1-day reminder
    assert "TRIGGER:-P7D" in ics  # 7-day reminder


def test_ics_escapes_special_chars():
    e = IcsEvent(uid="x@v", summary="Filing, due; today", due_date="2026-12-01")
    ics = render_calendar([e])
    assert "Filing\\, due\\; today" in ics


def test_create_subscription_returns_token_and_url():
    _, cs = _make_pair()
    sub = cs.create_subscription("user-1", scope="applicant")
    assert "token" in sub and len(sub["token"]) >= 20
    assert sub["feed_url"].endswith(".ics")
    assert sub["scope"] == "applicant"


def test_subscription_workspace_scope_requires_id():
    _, cs = _make_pair()
    try:
        cs.create_subscription("user-1", scope="workspace")
        assert False
    except ValueError:
        pass


def test_subscription_invalid_scope_rejected():
    _, cs = _make_pair()
    try:
        cs.create_subscription("user-1", scope="not-real")
        assert False
    except ValueError:
        pass


def test_revoke_subscription():
    _, cs = _make_pair()
    sub = cs.create_subscription("user-1")
    assert cs.revoke_subscription(sub["token"]) is True
    assert cs.get_subscription(sub["token"]) is None  # inactive subs return None


def test_rotate_subscription_creates_new_and_invalidates_old():
    _, cs = _make_pair()
    old = cs.create_subscription("user-1", scope="applicant", label="phone")
    new = cs.rotate_subscription(old["token"])
    assert new is not None
    assert new["token"] != old["token"]
    assert new["rotated_from"] == old["id"]
    assert cs.get_subscription(old["token"]) is None


def test_render_workspace_calendar_with_filing_and_deadlines():
    cw, cs = _make_pair()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.add_deadline(ws["id"], "RFE response due", "2027-02-15", kind="rfe")
    cw.add_deadline(ws["id"], "Premium decision", "2026-11-15", kind="processing")
    cw.record_filing(ws["id"], "WAC2612345678", "2026-11-01")
    deadlines = cw.list_deadlines(ws["id"])
    ics = cs.render_workspace_calendar(cw.get_workspace(ws["id"]), deadlines)
    assert ics.count("BEGIN:VEVENT") == 3  # 1 filing + 2 deadlines
    assert "WAC2612345678" in ics
    assert "RFE response due" in ics


def test_render_user_calendar_aggregates_workspaces():
    cw, cs = _make_pair()
    ws_a = cw.create_workspace("user-1", "H-1B", "US")
    ws_b = cw.create_workspace("user-1", "I-130", "US")
    cw.add_deadline(ws_a["id"], "A1", "2027-01-01")
    cw.add_deadline(ws_b["id"], "B1", "2027-02-01")
    ics = cs.render_user_calendar("user-1", scope="applicant")
    assert ics.count("BEGIN:VEVENT") == 2


def test_feed_for_token_renders_calendar():
    cw, cs = _make_pair()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.add_deadline(ws["id"], "Important", "2027-03-01")
    sub = cs.create_subscription("user-1", scope="applicant")
    feed = cs.render_feed_for_token(sub["token"])
    assert feed is not None
    assert "Important" in feed


def test_feed_for_revoked_token_returns_none():
    _, cs = _make_pair()
    sub = cs.create_subscription("user-1", scope="applicant")
    cs.revoke_subscription(sub["token"])
    assert cs.render_feed_for_token(sub["token"]) is None


def test_workspace_scope_renders_only_that_workspace():
    cw, cs = _make_pair()
    ws_a = cw.create_workspace("user-1", "H-1B", "US")
    ws_b = cw.create_workspace("user-1", "I-130", "US")
    cw.add_deadline(ws_a["id"], "A1", "2027-01-01")
    cw.add_deadline(ws_b["id"], "B1", "2027-02-01")
    sub = cs.create_subscription("user-1", scope="workspace", workspace_id=ws_a["id"])
    feed = cs.render_feed_for_token(sub["token"])
    assert "A1" in feed
    assert "B1" not in feed


def test_oauth_connect_records_provider():
    _, cs = _make_pair()
    conn = cs.connect_provider("user-1", "google", {"email": "u@example.com"})
    assert conn["provider"] == "google"
    assert conn["external_account"] == "u@example.com"
    assert conn["active"] is True


def test_oauth_connect_rejects_unknown_provider():
    _, cs = _make_pair()
    try:
        cs.connect_provider("user-1", "yahoo", {})
        assert False
    except ValueError:
        pass


def test_disconnect_marks_inactive():
    _, cs = _make_pair()
    c = cs.connect_provider("user-1", "outlook", {})
    assert cs.disconnect(c["id"]) is True
    assert len(cs.list_connections(user_id="user-1")) == 0


def test_push_to_calendar_logs_intent():
    cw, cs = _make_pair()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    cw.add_deadline(ws["id"], "X", "2027-01-01")
    c = cs.connect_provider("user-1", "google", {})
    push = cs.push_workspace_to_calendar(c["id"], ws["id"])
    assert push["status"] == "queued"
    assert push["event_count"] >= 1
    log = cs.get_push_log(connection_id=c["id"])
    assert len(log) == 1


def test_push_to_inactive_connection_raises():
    cw, cs = _make_pair()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    c = cs.connect_provider("user-1", "google", {})
    cs.disconnect(c["id"])
    try:
        cs.push_workspace_to_calendar(c["id"], ws["id"])
        assert False
    except ValueError:
        pass


def test_supported_providers_listed():
    providers = CalendarSyncService.list_supported_providers()
    ids = {p["id"] for p in providers}
    assert ids == set(PROVIDER_CHOICES)


def test_long_event_summary_is_folded():
    long_summary = "A" * 200
    e = IcsEvent(uid="x@v", summary=long_summary, due_date="2026-12-01")
    ics = render_calendar([e])
    # Folded continuation lines start with a single space
    summary_lines = [l for l in ics.splitlines() if l.startswith("SUMMARY:") or l.startswith(" A")]
    assert len(summary_lines) > 1
