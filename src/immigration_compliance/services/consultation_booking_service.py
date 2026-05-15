"""Consultation Booking — Calendly-style self-service scheduler.

Public self-booking links per attorney. Clients pick from open slots,
pay the consult fee (in production: Stripe / LawPay), and receive a
confirmation. Attorney sees the booked consult on their workbench.

Concepts:
  - AvailabilityWindow  : recurring weekly hours (e.g. Mon-Fri 9am-5pm
                          Eastern with 15-minute buffers)
  - BlackoutPeriod      : explicit unavailable date range (vacation,
                          court appearances)
  - SlotDuration        : 15 / 30 / 45 / 60 minute consult slots
  - BookingLink         : public URL like /book/<slug> attorneys can
                          share
  - Consultation        : a confirmed booking
  - ConsultationFee     : per-attorney pricing (free / paid / variable)

Public booking flow (no auth required):
  1. GET attorney's available_slots in a date range
  2. POST a booking with chosen slot + client info
  3. Service validates slot is still open + creates the consultation
  4. Returns confirmation + payment URL (if paid)

Production hooks:
  - Calendar sync: post the consultation to attorney's connected calendar
  - Payment: stripe / lawpay session for paid consults
  - Reminder: 24-hour and 1-hour reminder via NotificationService"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAYS_OF_WEEK = (0, 1, 2, 3, 4, 5, 6)  # Mon=0 ... Sun=6
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

VALID_SLOT_DURATIONS = (15, 30, 45, 60, 90)
DEFAULT_BUFFER_MINUTES = 15

CONSULT_TYPES = ("intake", "follow_up", "case_review", "general", "rfe_response", "deposition_prep")

CONSULT_STATUS = ("requested", "confirmed", "completed", "cancelled", "no_show")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ConsultationBookingService:
    """Calendly-style consultation self-booking."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._notifications = notification_service
        self._availability: dict[str, dict] = {}        # attorney_id → availability config
        self._blackouts: dict[str, list[dict]] = {}      # attorney_id → blackout periods
        self._booking_links: dict[str, dict] = {}        # slug → record
        self._consultations: dict[str, dict] = {}        # consultation_id → record

    # ---------- introspection ----------
    @staticmethod
    def list_consult_types() -> list[str]:
        return list(CONSULT_TYPES)

    @staticmethod
    def list_slot_durations() -> list[int]:
        return list(VALID_SLOT_DURATIONS)

    # ---------- attorney availability ----------
    def set_availability(
        self,
        attorney_id: str,
        weekly_windows: list[dict],
        slot_duration: int = 30,
        buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
        timezone: str = "America/New_York",
        max_advance_days: int = 60,
        min_notice_hours: int = 4,
    ) -> dict:
        """weekly_windows: list of {"day_of_week": int, "start": "HH:MM",
        "end": "HH:MM"} for each working block."""
        if slot_duration not in VALID_SLOT_DURATIONS:
            raise ValueError(f"Invalid slot duration: {slot_duration}")
        for w in weekly_windows:
            if w["day_of_week"] not in DAYS_OF_WEEK:
                raise ValueError(f"Invalid day_of_week: {w['day_of_week']}")
            self._parse_time(w["start"])
            self._parse_time(w["end"])
        record = {
            "attorney_id": attorney_id,
            "weekly_windows": weekly_windows,
            "slot_duration": slot_duration,
            "buffer_minutes": buffer_minutes,
            "timezone": timezone,
            "max_advance_days": max_advance_days,
            "min_notice_hours": min_notice_hours,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._availability[attorney_id] = record
        return record

    def get_availability(self, attorney_id: str) -> dict | None:
        return self._availability.get(attorney_id)

    @staticmethod
    def _parse_time(s: str) -> time:
        try:
            h, m = s.split(":")
            return time(int(h), int(m))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid time format '{s}', expected HH:MM") from e

    # ---------- blackout periods ----------
    def add_blackout(
        self, attorney_id: str, start_date: str, end_date: str, reason: str = "",
    ) -> dict:
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as e:
            raise ValueError("Invalid date format") from e
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        blackout = {
            "id": str(uuid.uuid4()),
            "attorney_id": attorney_id,
            "start_date": start_date, "end_date": end_date,
            "reason": reason,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._blackouts.setdefault(attorney_id, []).append(blackout)
        return blackout

    def list_blackouts(self, attorney_id: str) -> list[dict]:
        return list(self._blackouts.get(attorney_id, []))

    def remove_blackout(self, attorney_id: str, blackout_id: str) -> bool:
        blackouts = self._blackouts.get(attorney_id, [])
        before = len(blackouts)
        self._blackouts[attorney_id] = [b for b in blackouts if b["id"] != blackout_id]
        return len(self._blackouts[attorney_id]) < before

    # ---------- booking links ----------
    def create_booking_link(
        self, attorney_id: str, slug: str, label: str = "",
        consult_type: str = "intake", duration_minutes: int = 30,
        fee_usd: float = 0.0, description: str = "",
    ) -> dict:
        if consult_type not in CONSULT_TYPES:
            raise ValueError(f"Invalid consult type: {consult_type}")
        if duration_minutes not in VALID_SLOT_DURATIONS:
            raise ValueError(f"Invalid duration: {duration_minutes}")
        if slug in self._booking_links:
            raise ValueError(f"Slug already in use: {slug}")
        record = {
            "id": str(uuid.uuid4()),
            "attorney_id": attorney_id, "slug": slug,
            "label": label or slug,
            "consult_type": consult_type,
            "duration_minutes": duration_minutes,
            "fee_usd": fee_usd, "description": description,
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "url_path": f"/book/{slug}",
        }
        self._booking_links[slug] = record
        return record

    def get_booking_link(self, slug: str) -> dict | None:
        link = self._booking_links.get(slug)
        return link if (link and link["active"]) else None

    def list_booking_links(self, attorney_id: str | None = None) -> list[dict]:
        out = list(self._booking_links.values())
        if attorney_id:
            out = [l for l in out if l["attorney_id"] == attorney_id]
        return [l for l in out if l["active"]]

    def deactivate_booking_link(self, slug: str) -> dict | None:
        link = self._booking_links.get(slug)
        if link:
            link["active"] = False
            link["deactivated_at"] = datetime.utcnow().isoformat()
        return link

    # ---------- slot calculation ----------
    def get_open_slots(
        self, attorney_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        avail = self._availability.get(attorney_id)
        if avail is None:
            return []
        start = date.fromisoformat(from_date) if from_date else date.today()
        end = date.fromisoformat(to_date) if to_date else (date.today() + timedelta(days=avail["max_advance_days"]))
        if end > date.today() + timedelta(days=avail["max_advance_days"]):
            end = date.today() + timedelta(days=avail["max_advance_days"])

        # Existing bookings that block slots
        existing_starts = {
            datetime.fromisoformat(c["scheduled_start"])
            for c in self._consultations.values()
            if c["attorney_id"] == attorney_id and c["status"] in ("confirmed", "requested")
        }

        # Build all candidate slots
        slots = []
        slot_minutes = avail["slot_duration"]
        buffer_minutes = avail["buffer_minutes"]
        min_notice = timedelta(hours=avail["min_notice_hours"])
        now = datetime.utcnow()
        cur = start
        while cur <= end:
            # Check blackouts
            in_blackout = any(
                date.fromisoformat(b["start_date"]) <= cur <= date.fromisoformat(b["end_date"])
                for b in self._blackouts.get(attorney_id, [])
            )
            if in_blackout:
                cur += timedelta(days=1)
                continue
            # Find windows for this day of week
            dow = cur.weekday()
            for w in avail["weekly_windows"]:
                if w["day_of_week"] != dow:
                    continue
                start_t = self._parse_time(w["start"])
                end_t = self._parse_time(w["end"])
                slot_dt = datetime.combine(cur, start_t)
                end_dt = datetime.combine(cur, end_t)
                while slot_dt + timedelta(minutes=slot_minutes) <= end_dt:
                    if slot_dt - now < min_notice:
                        slot_dt += timedelta(minutes=slot_minutes + buffer_minutes)
                        continue
                    if slot_dt in existing_starts:
                        slot_dt += timedelta(minutes=slot_minutes + buffer_minutes)
                        continue
                    slots.append({
                        "start": slot_dt.isoformat(),
                        "end": (slot_dt + timedelta(minutes=slot_minutes)).isoformat(),
                        "duration_minutes": slot_minutes,
                    })
                    slot_dt += timedelta(minutes=slot_minutes + buffer_minutes)
            cur += timedelta(days=1)
        return slots

    # ---------- booking ----------
    def book_consultation(
        self,
        booking_slug: str,
        scheduled_start: str,
        client_name: str,
        client_email: str,
        client_phone: str = "",
        notes: str = "",
        client_user_id: str | None = None,
    ) -> dict:
        link = self.get_booking_link(booking_slug)
        if link is None:
            raise ValueError(f"Booking link not found or inactive: {booking_slug}")
        attorney_id = link["attorney_id"]
        avail = self._availability.get(attorney_id)
        if avail is None:
            raise ValueError("Attorney has not set availability")
        # Validate the start time
        try:
            start_dt = datetime.fromisoformat(scheduled_start)
        except ValueError as e:
            raise ValueError("Invalid scheduled_start format") from e
        # Verify slot is open
        open_slots = self.get_open_slots(attorney_id)
        if not any(datetime.fromisoformat(s["start"]) == start_dt for s in open_slots):
            raise ValueError("Selected slot is no longer available")
        # Create the consultation
        consult_id = str(uuid.uuid4())
        record = {
            "id": consult_id,
            "attorney_id": attorney_id,
            "booking_slug": booking_slug,
            "consult_type": link["consult_type"],
            "client_name": client_name,
            "client_email": client_email,
            "client_phone": client_phone,
            "client_user_id": client_user_id,
            "notes": notes,
            "scheduled_start": start_dt.isoformat(),
            "scheduled_end": (start_dt + timedelta(minutes=link["duration_minutes"])).isoformat(),
            "duration_minutes": link["duration_minutes"],
            "fee_usd": link["fee_usd"],
            "fee_paid": link["fee_usd"] == 0,
            "payment_url": None if link["fee_usd"] == 0 else f"/pay/consultation/{consult_id}",
            "status": "confirmed" if link["fee_usd"] == 0 else "requested",
            "booked_at": datetime.utcnow().isoformat(),
            "video_url": f"https://meet.verom.ai/c/{consult_id}",
        }
        self._consultations[consult_id] = record
        # Notify attorney
        if self._notifications:
            try:
                self._notifications.emit(
                    event_type="case.attorney_assigned",
                    recipient_user_id=attorney_id,
                    title="New consultation booked",
                    body=f"{client_name} booked a {link['consult_type']} consultation for {start_dt.isoformat()}",
                )
            except Exception:
                pass
        return record

    def cancel_consultation(self, consultation_id: str, reason: str = "") -> dict:
        c = self._consultations.get(consultation_id)
        if c is None:
            raise ValueError("Consultation not found")
        if c["status"] in ("completed", "cancelled"):
            return c
        c["status"] = "cancelled"
        c["cancel_reason"] = reason
        c["cancelled_at"] = datetime.utcnow().isoformat()
        return c

    def mark_consultation_complete(
        self, consultation_id: str, summary: str = "", convert_to_workspace: bool = False,
    ) -> dict:
        c = self._consultations.get(consultation_id)
        if c is None:
            raise ValueError("Consultation not found")
        c["status"] = "completed"
        c["summary"] = summary
        c["completed_at"] = datetime.utcnow().isoformat()
        if convert_to_workspace and self._cases:
            try:
                ws = self._cases.create_workspace(
                    applicant_id=c.get("client_user_id") or c["client_email"],
                    visa_type=c.get("notes_visa_type") or "Unspecified",
                    country="US",
                    case_label=f"{c['client_name']} ({c['consult_type']})",
                    attorney_id=c["attorney_id"],
                )
                c["converted_workspace_id"] = ws["id"]
            except Exception:
                pass
        return c

    def mark_no_show(self, consultation_id: str) -> dict:
        c = self._consultations.get(consultation_id)
        if c is None:
            raise ValueError("Consultation not found")
        c["status"] = "no_show"
        c["no_show_at"] = datetime.utcnow().isoformat()
        return c

    def confirm_payment(self, consultation_id: str) -> dict:
        c = self._consultations.get(consultation_id)
        if c is None:
            raise ValueError("Consultation not found")
        c["fee_paid"] = True
        c["fee_paid_at"] = datetime.utcnow().isoformat()
        if c["status"] == "requested":
            c["status"] = "confirmed"
        return c

    # ---------- queries ----------
    def get_consultation(self, consultation_id: str) -> dict | None:
        return self._consultations.get(consultation_id)

    def list_consultations(
        self, attorney_id: str | None = None,
        client_user_id: str | None = None,
        status: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        out = list(self._consultations.values())
        if attorney_id:
            out = [c for c in out if c["attorney_id"] == attorney_id]
        if client_user_id:
            out = [c for c in out if c.get("client_user_id") == client_user_id]
        if status:
            out = [c for c in out if c["status"] == status]
        if from_date:
            out = [c for c in out if c["scheduled_start"] >= from_date]
        if to_date:
            out = [c for c in out if c["scheduled_start"] <= to_date]
        return sorted(out, key=lambda c: c["scheduled_start"])

    def attorney_calendar(
        self, attorney_id: str, from_date: str | None = None, to_date: str | None = None,
    ) -> dict:
        consults = self.list_consultations(attorney_id=attorney_id, from_date=from_date, to_date=to_date)
        return {
            "attorney_id": attorney_id,
            "consultation_count": len(consults),
            "by_status": {
                s: sum(1 for c in consults if c["status"] == s)
                for s in CONSULT_STATUS
            },
            "consultations": consults,
        }
