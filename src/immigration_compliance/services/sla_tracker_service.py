"""Same-Day SLA Tracker — initial-contact and response-time discipline.

Public commitments are only believable if they're metered. This service watches
SLA-relevant events on the platform (lead capture, brief offer, applicant
message, RFE assignment) and tracks whether the responsible party (attorney,
firm) meets the SLA window. SLA breaches auto-flag for reassignment.

Tracked SLAs:
  - lead_initial_contact     attorney must contact a new matched lead within 4h
  - brief_offer_response     attorney must accept/decline a brief within 48h
  - applicant_message_reply  attorney must reply to a client message within 24h
  - rfe_acknowledgment       attorney must acknowledge a new RFE within 4h
  - filing_window_kickoff    attorney must start filing prep within 7d of retainer

Each SLA entry has a window, escalation hook, and breach record. Healthy
attorneys see their SLA percentage publicly on their profile.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import datetime, timedelta
from typing import Any


SLA_DEFINITIONS: dict[str, dict[str, Any]] = {
    "lead_initial_contact": {
        "label": "Initial contact with new lead",
        "window_hours": 4,
        "escalation_at_hours": 8,
    },
    "brief_offer_response": {
        "label": "Brief offer accept/decline",
        "window_hours": 48,
        "escalation_at_hours": 72,
    },
    "applicant_message_reply": {
        "label": "Reply to applicant message",
        "window_hours": 24,
        "escalation_at_hours": 48,
    },
    "rfe_acknowledgment": {
        "label": "Acknowledge new RFE",
        "window_hours": 4,
        "escalation_at_hours": 12,
    },
    "filing_window_kickoff": {
        "label": "Start filing prep after retainer",
        "window_hours": 168,  # 7 days
        "escalation_at_hours": 240,
    },
    "consultation_followup": {
        "label": "Send consult follow-up + proposal",
        "window_hours": 48,
        "escalation_at_hours": 96,
    },
}


SLA_STATUS = ("open", "met", "breached", "escalated", "auto_reassigned")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SlaTrackerService:
    """Track SLA-bearing events and breach detection."""

    def __init__(
        self,
        notification_service: Any | None = None,
        attorney_match_service: Any | None = None,
    ) -> None:
        self._notifications = notification_service
        self._matcher = attorney_match_service
        self._entries: dict[str, dict] = {}
        self._reassignments: list[dict] = []

    # ---------- introspection ----------
    @staticmethod
    def list_sla_kinds() -> list[dict]:
        return [
            {"kind": k, **v} for k, v in SLA_DEFINITIONS.items()
        ]

    @staticmethod
    def get_sla_definition(kind: str) -> dict | None:
        return SLA_DEFINITIONS.get(kind)

    # ---------- start a tracked SLA ----------
    def start(
        self,
        kind: str,
        responsible_user_id: str,
        related_workspace_id: str | None = None,
        related_brief_id: str | None = None,
        applicant_id: str | None = None,
        firm_id: str | None = None,
        custom_window_hours: int | None = None,
    ) -> dict:
        if kind not in SLA_DEFINITIONS:
            raise ValueError(f"Unknown SLA kind: {kind}")
        spec = SLA_DEFINITIONS[kind]
        window_hours = custom_window_hours or spec["window_hours"]
        escalation_hours = spec["escalation_at_hours"]
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow()
        record = {
            "id": entry_id,
            "kind": kind,
            "label": spec["label"],
            "responsible_user_id": responsible_user_id,
            "related_workspace_id": related_workspace_id,
            "related_brief_id": related_brief_id,
            "applicant_id": applicant_id,
            "firm_id": firm_id,
            "started_at": now.isoformat(),
            "window_hours": window_hours,
            "escalation_at_hours": escalation_hours,
            "deadline_at": (now + timedelta(hours=window_hours)).isoformat(),
            "escalation_at": (now + timedelta(hours=escalation_hours)).isoformat(),
            "status": "open",
            "completed_at": None,
            "breached_at": None,
            "elapsed_hours": None,
        }
        self._entries[entry_id] = record
        return record

    def complete(self, entry_id: str, completed_by_user_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("SLA entry not found")
        if entry["status"] not in ("open", "breached"):
            return entry
        now = datetime.utcnow()
        started = datetime.fromisoformat(entry["started_at"])
        elapsed = (now - started).total_seconds() / 3600
        entry["completed_at"] = now.isoformat()
        entry["completed_by_user_id"] = completed_by_user_id
        entry["elapsed_hours"] = round(elapsed, 2)
        if entry["status"] == "open":
            entry["status"] = "met"
        # If already breached, status stays "breached"
        return entry

    def cancel(self, entry_id: str, reason: str = "") -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("SLA entry not found")
        entry["status"] = "cancelled"
        entry["cancellation_reason"] = reason
        entry["cancelled_at"] = datetime.utcnow().isoformat()
        return entry

    # ---------- ticking ----------
    def tick(self, now: datetime | None = None) -> dict:
        """Walk all open entries, mark breaches and escalations."""
        now = now or datetime.utcnow()
        moved_to_breached = []
        moved_to_escalated = []
        moved_to_reassigned = []
        for entry in self._entries.values():
            if entry["status"] not in ("open", "breached"):
                continue
            try:
                deadline = datetime.fromisoformat(entry["deadline_at"])
                escalation = datetime.fromisoformat(entry["escalation_at"])
            except ValueError:
                continue
            if now > escalation and entry["status"] != "escalated":
                if entry["status"] == "open":
                    entry["status"] = "breached"
                    entry["breached_at"] = deadline.isoformat()
                    moved_to_breached.append(entry["id"])
                entry["status"] = "escalated"
                moved_to_escalated.append(entry["id"])
                self._fire_escalation(entry)
            elif now > deadline and entry["status"] == "open":
                entry["status"] = "breached"
                entry["breached_at"] = deadline.isoformat()
                moved_to_breached.append(entry["id"])
                self._fire_breach(entry)
        return {
            "ticked_at": now.isoformat(),
            "breached": moved_to_breached,
            "escalated": moved_to_escalated,
            "auto_reassigned": moved_to_reassigned,
        }

    # ---------- breach handling ----------
    def _fire_breach(self, entry: dict) -> None:
        if not self._notifications:
            return
        try:
            self._notifications.emit(
                event_type="case.status_changed",
                recipient_user_id=entry["responsible_user_id"],
                title="SLA breached",
                body=f"{entry['label']} SLA ({entry['window_hours']}h) has been missed.",
                metadata={
                    "intent": "sla_breach",
                    "sla_kind": entry["kind"],
                    "entry_id": entry["id"],
                },
            )
        except Exception:
            pass
        if entry.get("applicant_id"):
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=entry["applicant_id"],
                    title="Your attorney response time SLA was missed",
                    body=(
                        f"Your attorney did not {entry['label'].lower()} within the "
                        f"{entry['window_hours']}-hour SLA window. They have been notified."
                    ),
                    metadata={"intent": "sla_breach_applicant"},
                )
            except Exception:
                pass

    def _fire_escalation(self, entry: dict) -> None:
        if not self._notifications:
            return
        # Notify firm partner if known
        if entry.get("firm_id"):
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=entry["firm_id"],
                    title=f"SLA escalation: {entry['label']}",
                    body=(
                        f"{entry['label']} SLA exceeded {entry['escalation_at_hours']}h. "
                        f"Attorney {entry['responsible_user_id']} responsible."
                    ),
                    metadata={"intent": "sla_escalation", "entry_id": entry["id"]},
                )
            except Exception:
                pass

    def auto_reassign(self, entry_id: str, new_responsible_user_id: str) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError("SLA entry not found")
        record = {
            "id": str(uuid.uuid4()),
            "entry_id": entry_id,
            "from_user_id": entry["responsible_user_id"],
            "to_user_id": new_responsible_user_id,
            "at": datetime.utcnow().isoformat(),
        }
        self._reassignments.append(record)
        entry["status"] = "auto_reassigned"
        entry["responsible_user_id"] = new_responsible_user_id
        # Reset window
        entry["started_at"] = datetime.utcnow().isoformat()
        entry["deadline_at"] = (datetime.utcnow() + timedelta(hours=entry["window_hours"])).isoformat()
        entry["escalation_at"] = (datetime.utcnow() + timedelta(hours=entry["escalation_at_hours"])).isoformat()
        return record

    # ---------- queries ----------
    def get_entry(self, entry_id: str) -> dict | None:
        return self._entries.get(entry_id)

    def list_entries(
        self,
        responsible_user_id: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        firm_id: str | None = None,
    ) -> list[dict]:
        out = list(self._entries.values())
        if responsible_user_id:
            out = [e for e in out if e["responsible_user_id"] == responsible_user_id]
        if kind:
            out = [e for e in out if e["kind"] == kind]
        if status:
            out = [e for e in out if e["status"] == status]
        if firm_id:
            out = [e for e in out if e.get("firm_id") == firm_id]
        return out

    def list_breached(self) -> list[dict]:
        return [e for e in self._entries.values() if e["status"] in ("breached", "escalated", "auto_reassigned")]

    # ---------- attorney scorecard ----------
    def attorney_sla_health(self, attorney_id: str) -> dict:
        entries = [e for e in self._entries.values() if e["responsible_user_id"] == attorney_id]
        if not entries:
            return {"attorney_id": attorney_id, "score": None, "entry_count": 0}
        completed = [e for e in entries if e["status"] in ("met", "breached")]
        met = [e for e in completed if e["status"] == "met"]
        breached = [e for e in completed if e["status"] == "breached"]
        elapsed_hours = [e["elapsed_hours"] for e in met if e.get("elapsed_hours") is not None]
        n = len(completed)
        sla_pct = round((len(met) / n) * 100, 1) if n else None
        median_response_hours = round(statistics.median(elapsed_hours), 2) if elapsed_hours else None
        # Breakdown by SLA kind
        by_kind: dict[str, dict] = {}
        for e in completed:
            kind = e["kind"]
            if kind not in by_kind:
                by_kind[kind] = {"count": 0, "met": 0}
            by_kind[kind]["count"] += 1
            if e["status"] == "met":
                by_kind[kind]["met"] += 1
        for kind in by_kind:
            by_kind[kind]["sla_pct"] = round(by_kind[kind]["met"] / by_kind[kind]["count"] * 100, 1)
        # Score: SLA percentage minus penalty for active breaches
        active_breaches = sum(1 for e in entries if e["status"] in ("breached", "escalated"))
        if sla_pct is None:
            score = None
        else:
            score = max(0, round(sla_pct - active_breaches * 5))
        return {
            "attorney_id": attorney_id,
            "score": score,
            "entry_count": len(entries),
            "completed_count": n,
            "met_count": len(met),
            "breached_count": len(breached),
            "sla_pct": sla_pct,
            "median_response_hours": median_response_hours,
            "active_breaches": active_breaches,
            "by_kind": by_kind,
            "computed_at": datetime.utcnow().isoformat(),
        }
