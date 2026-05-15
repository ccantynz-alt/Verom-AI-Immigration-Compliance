"""Tests for the Calendly-style consultation booking service."""

from datetime import datetime, timedelta

from immigration_compliance.services.consultation_booking_service import (
    ConsultationBookingService,
    CONSULT_TYPES,
    VALID_SLOT_DURATIONS,
)


def _full_week_avail():
    return [
        {"day_of_week": 0, "start": "09:00", "end": "17:00"},
        {"day_of_week": 1, "start": "09:00", "end": "17:00"},
        {"day_of_week": 2, "start": "09:00", "end": "17:00"},
        {"day_of_week": 3, "start": "09:00", "end": "17:00"},
        {"day_of_week": 4, "start": "09:00", "end": "17:00"},
    ]


def test_set_availability_validates_slot_duration():
    svc = ConsultationBookingService()
    try:
        svc.set_availability("a1", _full_week_avail(), slot_duration=37)
        assert False
    except ValueError:
        pass


def test_set_availability_validates_day_of_week():
    svc = ConsultationBookingService()
    try:
        svc.set_availability("a1", [{"day_of_week": 9, "start": "09:00", "end": "17:00"}])
        assert False
    except ValueError:
        pass


def test_set_availability_validates_time_format():
    svc = ConsultationBookingService()
    try:
        svc.set_availability("a1", [{"day_of_week": 0, "start": "9 AM", "end": "5 PM"}])
        assert False
    except ValueError:
        pass


def test_create_booking_link():
    svc = ConsultationBookingService()
    link = svc.create_booking_link("a1", slug="my-link", consult_type="intake", duration_minutes=30)
    assert link["url_path"] == "/book/my-link"
    assert link["active"] is True


def test_duplicate_slug_rejected():
    svc = ConsultationBookingService()
    svc.create_booking_link("a1", slug="my-link")
    try:
        svc.create_booking_link("a1", slug="my-link")
        assert False
    except ValueError:
        pass


def test_invalid_consult_type_rejected():
    svc = ConsultationBookingService()
    try:
        svc.create_booking_link("a1", slug="x", consult_type="emergency")
        assert False
    except ValueError:
        pass


def test_open_slots_returned_for_business_hours():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    slots = svc.get_open_slots("a1")
    assert len(slots) > 0
    # All slots should be 30 minutes
    for s in slots:
        assert s["duration_minutes"] == 30


def test_no_slots_when_no_availability():
    svc = ConsultationBookingService()
    slots = svc.get_open_slots("ghost")
    assert slots == []


def test_blackout_blocks_slots_in_range():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    # Blackout for the rest of the year
    today = datetime.utcnow().date().isoformat()
    end = (datetime.utcnow().date() + timedelta(days=365)).isoformat()
    svc.add_blackout("a1", start_date=today, end_date=end, reason="Sabbatical")
    slots = svc.get_open_slots("a1")
    assert len(slots) == 0


def test_blackout_invalid_dates_rejected():
    svc = ConsultationBookingService()
    try:
        svc.add_blackout("a1", "2027-12-31", "2027-12-01")  # end before start
        assert False
    except ValueError:
        pass


def test_book_consultation_succeeds():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30, fee_usd=200)
    slots = svc.get_open_slots("a1")
    assert len(slots) > 0
    consult = svc.book_consultation(
        booking_slug="x", scheduled_start=slots[0]["start"],
        client_name="Wei Chen", client_email="w@x.com",
    )
    assert consult["status"] == "requested"  # paid consult, awaiting payment
    assert consult["payment_url"] is not None


def test_free_consultation_auto_confirmed():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="free", consult_type="intake", duration_minutes=30, fee_usd=0.0)
    slots = svc.get_open_slots("a1")
    consult = svc.book_consultation(
        booking_slug="free", scheduled_start=slots[0]["start"],
        client_name="A", client_email="a@x.com",
    )
    assert consult["status"] == "confirmed"
    assert consult["fee_paid"] is True


def test_double_booking_prevented():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30)
    slots = svc.get_open_slots("a1")
    svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                          client_name="A", client_email="a@x.com")
    try:
        svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                              client_name="B", client_email="b@x.com")
        assert False
    except ValueError:
        pass


def test_booked_slot_removed_from_open_slots():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30)
    slots_before = svc.get_open_slots("a1")
    svc.book_consultation(booking_slug="x", scheduled_start=slots_before[0]["start"],
                          client_name="A", client_email="a@x.com")
    slots_after = svc.get_open_slots("a1")
    assert len(slots_after) == len(slots_before) - 1


def test_cancel_consultation():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30)
    slots = svc.get_open_slots("a1")
    consult = svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                                     client_name="A", client_email="a@x.com")
    cancelled = svc.cancel_consultation(consult["id"], reason="Schedule conflict")
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancel_reason"] == "Schedule conflict"


def test_confirm_payment_advances_status():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30, fee_usd=200)
    slots = svc.get_open_slots("a1")
    consult = svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                                     client_name="A", client_email="a@x.com")
    assert consult["status"] == "requested"
    paid = svc.confirm_payment(consult["id"])
    assert paid["status"] == "confirmed"
    assert paid["fee_paid"] is True


def test_mark_complete():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30)
    slots = svc.get_open_slots("a1")
    consult = svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                                     client_name="A", client_email="a@x.com")
    completed = svc.mark_consultation_complete(consult["id"], summary="Discussed H-1B path")
    assert completed["status"] == "completed"
    assert completed["summary"] == "Discussed H-1B path"


def test_mark_no_show():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30)
    slots = svc.get_open_slots("a1")
    consult = svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                                     client_name="A", client_email="a@x.com")
    ns = svc.mark_no_show(consult["id"])
    assert ns["status"] == "no_show"


def test_attorney_calendar_summary():
    svc = ConsultationBookingService()
    svc.set_availability("a1", _full_week_avail(), slot_duration=30)
    svc.create_booking_link("a1", slug="x", consult_type="intake", duration_minutes=30, fee_usd=0)
    slots = svc.get_open_slots("a1")
    svc.book_consultation(booking_slug="x", scheduled_start=slots[0]["start"],
                          client_name="A", client_email="a@x.com")
    cal = svc.attorney_calendar("a1")
    assert cal["consultation_count"] == 1
    assert cal["by_status"]["confirmed"] == 1


def test_consult_types_listing():
    types = ConsultationBookingService.list_consult_types()
    assert set(types) == set(CONSULT_TYPES)


def test_slot_durations_listing():
    durations = ConsultationBookingService.list_slot_durations()
    assert set(durations) == set(VALID_SLOT_DURATIONS)


def test_min_notice_blocks_immediate_slots():
    svc = ConsultationBookingService()
    # Set min_notice_hours=24 so today's slots are excluded
    svc.set_availability("a1", _full_week_avail(), slot_duration=30, min_notice_hours=24)
    slots = svc.get_open_slots("a1")
    # All slots should be at least 24 hours from now
    now = datetime.utcnow()
    for s in slots[:10]:
        slot_dt = datetime.fromisoformat(s["start"])
        assert slot_dt - now >= timedelta(hours=24) - timedelta(minutes=1)


def test_deactivated_link_returns_none():
    svc = ConsultationBookingService()
    svc.create_booking_link("a1", slug="x")
    svc.deactivate_booking_link("x")
    assert svc.get_booking_link("x") is None
