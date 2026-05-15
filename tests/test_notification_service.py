"""Tests for the Notification + Webhook system."""

from immigration_compliance.services.notification_service import (
    NotificationService,
    EVENT_TYPES,
    CHANNELS,
)


def test_event_types_cover_major_categories():
    expected_categories = {"case", "document", "communication", "regulatory", "billing", "compliance"}
    actual_categories = {v["category"] for v in EVENT_TYPES.values()}
    assert expected_categories <= actual_categories


def test_channels_complete():
    assert set(CHANNELS) == {"in_app", "email", "sms", "push", "webhook"}


def test_emit_records_notification():
    svc = NotificationService()
    n = svc.emit("case.status_changed", "user-1", "Status changed", "Case is now filed")
    assert n["recipient_user_id"] == "user-1"
    assert "in_app" in n["channels_succeeded"]


def test_emit_unknown_event_type_rejected():
    svc = NotificationService()
    try:
        svc.emit("not.a.real.event", "user-1", "x", "y")
        assert False
    except ValueError:
        pass


def test_set_user_preferences_validates():
    svc = NotificationService()
    try:
        svc.set_user_preferences("u1", {"fake.event": ["in_app"]})
        assert False
    except ValueError:
        pass
    try:
        svc.set_user_preferences("u1", {"case.filed": ["fake_channel"]})
        assert False
    except ValueError:
        pass


def test_user_preferences_override_defaults():
    svc = NotificationService()
    svc.set_user_preferences("u1", {"case.filed": ["in_app"]})
    channels = svc.channels_for("u1", "case.filed")
    assert channels == ["in_app"]


def test_default_channels_used_when_no_pref():
    svc = NotificationService()
    channels = svc.channels_for("u1", "case.deadline_due_soon")
    assert "in_app" in channels


def test_inbox_filtered_by_user():
    svc = NotificationService()
    svc.emit("case.filed", "user-1", "U1", "B")
    svc.emit("case.filed", "user-2", "U2", "B")
    inbox = svc.list_for_user("user-1")
    assert len(inbox) == 1
    assert inbox[0]["recipient_user_id"] == "user-1"


def test_unread_count_and_mark_read():
    svc = NotificationService()
    n1 = svc.emit("case.filed", "user-1", "T1", "B")
    n2 = svc.emit("case.filed", "user-1", "T2", "B")
    assert svc.get_unread_count("user-1") == 2
    svc.mark_read(n1["id"], "user-1")
    assert svc.get_unread_count("user-1") == 1


def test_mark_all_read():
    svc = NotificationService()
    for _ in range(3):
        svc.emit("case.filed", "user-1", "T", "B")
    count = svc.mark_all_read("user-1")
    assert count == 3
    assert svc.get_unread_count("user-1") == 0


def test_mark_read_unauthorized():
    svc = NotificationService()
    n = svc.emit("case.filed", "user-1", "T", "B")
    try:
        svc.mark_read(n["id"], "different-user")
        assert False
    except ValueError:
        pass


def test_webhook_registration():
    svc = NotificationService()
    wh = svc.register_webhook(
        firm_id="firm-1", url="https://firm.example/hook",
        event_types=["case.filed", "case.rfe_received"],
    )
    assert wh["firm_id"] == "firm-1"
    assert wh["active"] is True
    assert len(wh["secret"]) >= 20


def test_webhook_unknown_event_type_rejected():
    svc = NotificationService()
    try:
        svc.register_webhook(firm_id="f", url="https://x", event_types=["fake.event"])
        assert False
    except ValueError:
        pass


def test_webhook_fires_on_matching_event():
    svc = NotificationService()
    wh = svc.register_webhook(firm_id="f", url="https://x", event_types=["case.filed"])
    svc.emit("case.filed", "user-1", "T", "B")
    deliveries = svc.get_webhook_delivery_log(wh["id"])
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "delivered"


def test_webhook_does_not_fire_on_non_matching_event():
    svc = NotificationService()
    wh = svc.register_webhook(firm_id="f", url="https://x", event_types=["case.filed"])
    svc.emit("case.status_changed", "user-1", "T", "B")
    deliveries = svc.get_webhook_delivery_log(wh["id"])
    assert len(deliveries) == 0


def test_webhook_signature_verifies():
    svc = NotificationService()
    wh = svc.register_webhook(firm_id="f", url="https://x", event_types=["case.filed"])
    svc.emit("case.filed", "user-1", "T", "B")
    delivery = svc.get_webhook_delivery_log(wh["id"])[0]
    assert NotificationService.verify_signature(wh["secret"], delivery["body"], delivery["signature"]) is True
    assert NotificationService.verify_signature("wrong", delivery["body"], delivery["signature"]) is False


def test_deactivate_webhook_stops_delivery():
    svc = NotificationService()
    wh = svc.register_webhook(firm_id="f", url="https://x", event_types=["case.filed"])
    svc.deactivate_webhook(wh["id"])
    svc.emit("case.filed", "user-1", "T", "B")
    deliveries = svc.get_webhook_delivery_log(wh["id"])
    assert len(deliveries) == 0


def test_rotate_webhook_secret():
    svc = NotificationService()
    wh = svc.register_webhook(firm_id="f", url="https://x", event_types=["case.filed"])
    old_secret = wh["secret"]
    rotated = svc.rotate_webhook_secret(wh["id"])
    assert rotated["secret"] != old_secret


def test_force_channels_bypasses_prefs():
    svc = NotificationService()
    svc.set_user_preferences("u1", {"case.filed": ["in_app"]})
    n = svc.emit("case.filed", "u1", "T", "B", force_channels=["in_app", "email"], recipient_email="u@x.com")
    assert "email" in n["channels_succeeded"]


def test_email_dispatch_failure_recorded():
    def broken(to, subject, body, metadata):
        raise RuntimeError("smtp down")
    svc = NotificationService(email_dispatcher=broken)
    n = svc.emit("case.filed", "u1", "T", "B", recipient_email="u@x.com", force_channels=["in_app", "email"])
    assert any(f["channel"] == "email" for f in n["channels_failed"])


def test_event_types_listing():
    types = NotificationService.list_event_types()
    ids = {t["event_type"] for t in types}
    assert "case.filed" in ids
    assert "case.deadline_due_soon" in ids
