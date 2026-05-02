"""Time Tracking + Billable Hours service.

Every immigration attorney with hourly billing needs this. Tracks billable
and non-billable time per case, runs timers, captures activity-based
events automatically, generates invoice-ready summaries.

Core concepts:
  - Timer       : start/stop session for live tracking
  - TimeEntry   : single completed billable/non-billable event
  - Invoice     : aggregated entries by case for a date range, formatted
  - ActivityLog : automatic time capture from platform events (case
                  workspace updates, form populations, document reviews)

Billable categorization is data-driven (BILLING_RATES per attorney +
ACTIVITY_DEFAULTS per platform action) so adding new activity types is
one config entry.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Activity defaults
# ---------------------------------------------------------------------------

# Activity type → (label, default billable, default minutes)
ACTIVITY_DEFAULTS: dict[str, dict[str, Any]] = {
    "case_review":              {"label": "Case Review", "billable": True, "default_minutes": 15},
    "intake_review":            {"label": "Intake Review", "billable": True, "default_minutes": 30},
    "form_drafting":            {"label": "Form Drafting", "billable": True, "default_minutes": 45},
    "form_review":              {"label": "Form Review", "billable": True, "default_minutes": 20},
    "document_review":          {"label": "Document Review", "billable": True, "default_minutes": 15},
    "petition_letter_drafting": {"label": "Petition Letter Drafting", "billable": True, "default_minutes": 90},
    "rfe_response_drafting":    {"label": "RFE Response Drafting", "billable": True, "default_minutes": 120},
    "support_letter_drafting":  {"label": "Support Letter Drafting", "billable": True, "default_minutes": 30},
    "client_communication":     {"label": "Client Communication", "billable": True, "default_minutes": 15},
    "client_call":              {"label": "Client Call", "billable": True, "default_minutes": 30},
    "client_email":             {"label": "Client Email", "billable": True, "default_minutes": 10},
    "research":                 {"label": "Legal Research", "billable": True, "default_minutes": 30},
    "filing_prep":              {"label": "Filing Preparation", "billable": True, "default_minutes": 45},
    "filing_submission":        {"label": "Filing Submission", "billable": True, "default_minutes": 30},
    "court_appearance":         {"label": "Court / Hearing Appearance", "billable": True, "default_minutes": 60},
    "consultation":             {"label": "Consultation", "billable": True, "default_minutes": 30},
    "case_administration":      {"label": "Case Administration", "billable": False, "default_minutes": 10},
    "platform_setup":           {"label": "Platform Setup", "billable": False, "default_minutes": 5},
    "internal_meeting":         {"label": "Internal Meeting", "billable": False, "default_minutes": 30},
    "training":                 {"label": "Training", "billable": False, "default_minutes": 60},
    "other":                    {"label": "Other", "billable": True, "default_minutes": 15},
}

VALID_RATE_KINDS = ("hourly", "flat_fee", "non_billable")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TimeTrackingService:
    """Track billable + non-billable time across cases."""

    def __init__(self, case_workspace: Any | None = None) -> None:
        self._cases = case_workspace
        self._timers: dict[str, dict] = {}     # active timers
        self._entries: dict[str, dict] = {}    # completed time entries
        self._rates: dict[str, dict] = {}      # billing rates per attorney
        self._invoices: dict[str, dict] = {}   # generated invoices

    # ---------- billing rates ----------
    def set_billing_rate(self, attorney_id: str, rate_per_hour: float, currency: str = "USD") -> dict:
        if rate_per_hour <= 0:
            raise ValueError("Hourly rate must be positive")
        record = {
            "attorney_id": attorney_id,
            "rate_per_hour": float(rate_per_hour),
            "currency": currency,
            "set_at": datetime.utcnow().isoformat(),
        }
        self._rates[attorney_id] = record
        return record

    def get_billing_rate(self, attorney_id: str) -> dict | None:
        return self._rates.get(attorney_id)

    # ---------- timer lifecycle ----------
    def start_timer(
        self,
        attorney_id: str,
        workspace_id: str | None = None,
        activity_type: str = "other",
        description: str = "",
    ) -> dict:
        if activity_type not in ACTIVITY_DEFAULTS:
            raise ValueError(f"Unknown activity type: {activity_type}")
        # Stop any existing timer for this attorney first
        self._auto_stop_existing(attorney_id)
        timer = {
            "id": str(uuid.uuid4()),
            "attorney_id": attorney_id,
            "workspace_id": workspace_id,
            "activity_type": activity_type,
            "description": description,
            "started_at": datetime.utcnow().isoformat(),
            "stopped_at": None,
            "elapsed_seconds": 0,
            "is_running": True,
        }
        self._timers[timer["id"]] = timer
        return timer

    def stop_timer(self, timer_id: str, description_override: str | None = None) -> dict:
        timer = self._timers.get(timer_id)
        if timer is None:
            raise ValueError(f"Timer not found: {timer_id}")
        if not timer["is_running"]:
            return timer
        stopped_at = datetime.utcnow()
        timer["stopped_at"] = stopped_at.isoformat()
        timer["is_running"] = False
        started = datetime.fromisoformat(timer["started_at"])
        timer["elapsed_seconds"] = int((stopped_at - started).total_seconds())
        if description_override is not None:
            timer["description"] = description_override
        # Convert into a TimeEntry
        entry = self._timer_to_entry(timer)
        self._entries[entry["id"]] = entry
        timer["entry_id"] = entry["id"]
        return timer

    def get_active_timer(self, attorney_id: str) -> dict | None:
        for t in self._timers.values():
            if t["attorney_id"] == attorney_id and t["is_running"]:
                return t
        return None

    def list_timers(self, attorney_id: str | None = None) -> list[dict]:
        out = list(self._timers.values())
        if attorney_id:
            out = [t for t in out if t["attorney_id"] == attorney_id]
        return out

    def _auto_stop_existing(self, attorney_id: str) -> None:
        active = self.get_active_timer(attorney_id)
        if active:
            self.stop_timer(active["id"])

    # ---------- direct entries ----------
    def add_entry(
        self,
        attorney_id: str,
        minutes: float,
        activity_type: str = "other",
        workspace_id: str | None = None,
        description: str = "",
        billable_override: bool | None = None,
        entry_date: str | None = None,
    ) -> dict:
        if minutes <= 0:
            raise ValueError("Minutes must be positive")
        if activity_type not in ACTIVITY_DEFAULTS:
            raise ValueError(f"Unknown activity type: {activity_type}")
        spec = ACTIVITY_DEFAULTS[activity_type]
        billable = spec["billable"] if billable_override is None else bool(billable_override)
        seconds = int(minutes * 60)
        entry_date = entry_date or datetime.utcnow().date().isoformat()
        amount = self._compute_amount(attorney_id, seconds, billable)
        entry = {
            "id": str(uuid.uuid4()),
            "attorney_id": attorney_id,
            "workspace_id": workspace_id,
            "activity_type": activity_type,
            "activity_label": spec["label"],
            "description": description,
            "minutes": float(minutes),
            "elapsed_seconds": seconds,
            "billable": billable,
            "amount": amount,
            "currency": (self._rates.get(attorney_id) or {}).get("currency", "USD"),
            "entry_date": entry_date,
            "logged_at": datetime.utcnow().isoformat(),
            "source": "manual",
        }
        self._entries[entry["id"]] = entry
        return entry

    def auto_log_activity(
        self,
        attorney_id: str,
        activity_type: str,
        workspace_id: str | None = None,
        description: str = "",
        minutes_override: float | None = None,
    ) -> dict:
        """Capture time automatically from a platform event (e.g. attorney
        populated a form). Uses the activity's default duration unless
        overridden."""
        if activity_type not in ACTIVITY_DEFAULTS:
            raise ValueError(f"Unknown activity type: {activity_type}")
        minutes = minutes_override if minutes_override is not None else ACTIVITY_DEFAULTS[activity_type]["default_minutes"]
        entry = self.add_entry(
            attorney_id=attorney_id, minutes=minutes,
            activity_type=activity_type, workspace_id=workspace_id,
            description=description,
        )
        entry["source"] = "auto"
        return entry

    def list_entries(
        self,
        attorney_id: str | None = None,
        workspace_id: str | None = None,
        billable: bool | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict]:
        entries = list(self._entries.values())
        if attorney_id:
            entries = [e for e in entries if e["attorney_id"] == attorney_id]
        if workspace_id:
            entries = [e for e in entries if e["workspace_id"] == workspace_id]
        if billable is not None:
            entries = [e for e in entries if e["billable"] == billable]
        if since:
            entries = [e for e in entries if e["entry_date"] >= since]
        if until:
            entries = [e for e in entries if e["entry_date"] <= until]
        return sorted(entries, key=lambda e: e["entry_date"], reverse=True)

    def update_entry(
        self,
        entry_id: str,
        minutes: float | None = None,
        description: str | None = None,
        billable: bool | None = None,
        activity_type: str | None = None,
    ) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        if minutes is not None:
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
            entry["minutes"] = float(minutes)
            entry["elapsed_seconds"] = int(minutes * 60)
        if description is not None:
            entry["description"] = description
        if billable is not None:
            entry["billable"] = bool(billable)
        if activity_type is not None:
            if activity_type not in ACTIVITY_DEFAULTS:
                raise ValueError(f"Unknown activity type: {activity_type}")
            entry["activity_type"] = activity_type
            entry["activity_label"] = ACTIVITY_DEFAULTS[activity_type]["label"]
        # Recompute amount
        entry["amount"] = self._compute_amount(entry["attorney_id"], entry["elapsed_seconds"], entry["billable"])
        entry["updated_at"] = datetime.utcnow().isoformat()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    # ---------- summary + invoice ----------
    def workspace_summary(self, workspace_id: str) -> dict:
        entries = self.list_entries(workspace_id=workspace_id)
        return self._summarize(entries)

    def attorney_summary(self, attorney_id: str, since: str | None = None, until: str | None = None) -> dict:
        entries = self.list_entries(attorney_id=attorney_id, since=since, until=until)
        return self._summarize(entries)

    @staticmethod
    def _summarize(entries: list[dict]) -> dict:
        total_seconds = sum(e["elapsed_seconds"] for e in entries)
        billable_seconds = sum(e["elapsed_seconds"] for e in entries if e["billable"])
        non_billable_seconds = total_seconds - billable_seconds
        total_amount = sum(e.get("amount") or 0 for e in entries if e["billable"])
        currency = entries[0]["currency"] if entries else "USD"
        # Activity breakdown
        by_activity: dict[str, dict] = {}
        for e in entries:
            t = e["activity_type"]
            if t not in by_activity:
                by_activity[t] = {"label": e["activity_label"], "minutes": 0.0, "amount": 0.0, "billable": e["billable"]}
            by_activity[t]["minutes"] += e["minutes"]
            by_activity[t]["amount"] += (e.get("amount") or 0) if e["billable"] else 0
        return {
            "entry_count": len(entries),
            "total_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2),
            "billable_seconds": billable_seconds,
            "billable_hours": round(billable_seconds / 3600, 2),
            "non_billable_seconds": non_billable_seconds,
            "non_billable_hours": round(non_billable_seconds / 3600, 2),
            "total_amount": round(total_amount, 2),
            "currency": currency,
            "by_activity": by_activity,
        }

    def generate_invoice(
        self,
        workspace_id: str,
        since: str | None = None,
        until: str | None = None,
        attorney_id: str | None = None,
    ) -> dict:
        entries = self.list_entries(workspace_id=workspace_id, attorney_id=attorney_id, since=since, until=until, billable=True)
        summary = self._summarize(entries)
        invoice = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "attorney_id": attorney_id,
            "since": since,
            "until": until,
            "entries": entries,
            "summary": summary,
            "subtotal": summary["total_amount"],
            "currency": summary["currency"],
            "status": "draft",
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._invoices[invoice["id"]] = invoice
        return invoice

    def get_invoice(self, invoice_id: str) -> dict | None:
        return self._invoices.get(invoice_id)

    def list_invoices(self, workspace_id: str | None = None, attorney_id: str | None = None) -> list[dict]:
        out = list(self._invoices.values())
        if workspace_id:
            out = [i for i in out if i["workspace_id"] == workspace_id]
        if attorney_id:
            out = [i for i in out if i["attorney_id"] == attorney_id]
        return out

    # ---------- internals ----------
    def _timer_to_entry(self, timer: dict) -> dict:
        spec = ACTIVITY_DEFAULTS.get(timer["activity_type"], ACTIVITY_DEFAULTS["other"])
        billable = spec["billable"]
        amount = self._compute_amount(timer["attorney_id"], timer["elapsed_seconds"], billable)
        return {
            "id": str(uuid.uuid4()),
            "attorney_id": timer["attorney_id"],
            "workspace_id": timer["workspace_id"],
            "activity_type": timer["activity_type"],
            "activity_label": spec["label"],
            "description": timer["description"],
            "minutes": round(timer["elapsed_seconds"] / 60, 2),
            "elapsed_seconds": timer["elapsed_seconds"],
            "billable": billable,
            "amount": amount,
            "currency": (self._rates.get(timer["attorney_id"]) or {}).get("currency", "USD"),
            "entry_date": datetime.fromisoformat(timer["started_at"]).date().isoformat(),
            "logged_at": datetime.utcnow().isoformat(),
            "source": "timer",
            "timer_id": timer["id"],
        }

    def _compute_amount(self, attorney_id: str, seconds: int, billable: bool) -> float:
        if not billable:
            return 0.0
        rate = self._rates.get(attorney_id)
        if not rate:
            return 0.0
        hours = seconds / 3600
        return round(hours * rate["rate_per_hour"], 2)

    # ---------- introspection ----------
    @staticmethod
    def list_activity_types() -> list[dict]:
        return [
            {"type": k, "label": v["label"], "billable_default": v["billable"], "default_minutes": v["default_minutes"]}
            for k, v in ACTIVITY_DEFAULTS.items()
        ]
