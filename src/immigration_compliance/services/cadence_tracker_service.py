"""Required-Cadence Update Tracker — silent-attorney problem solver.

Attorneys must post a status update every X days while a case is active or the
case auto-flags to the applicant and the firm's escalation chain. Combined with
verification + outcome reviews, this is the trust feature no incumbent can copy
because their attorney users would revolt — but new attorneys joining Verom
accept it as the cost of qualified leads.

Mechanic:
  - Each active workspace has a configured cadence (default: 14 days, can shorten
    to 7 days for high-priority cases or extend to 30 days during processing-
    quiet windows like waiting on USCIS adjudication).
  - When the deadline passes without an update, the case is "stale". After 24h
    of staleness, it's "overdue" and the applicant is notified. After 72h, the
    case is "alert" — the firm partner / escalation contact is notified and
    the attorney's response_health metric drops.
  - Updates can be posted via the chatbot, case workspace, or any client comm
    channel. The service watches for those events.

This service is intentionally focused on the cadence accounting. The actual
notifications go through NotificationService.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


CADENCE_DAYS_DEFAULT = 14
STALE_GRACE_HOURS = 24
ALERT_ESCALATION_HOURS = 72


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CadenceTrackerService:
    """Track required-cadence status updates per active case."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._notifications = notification_service
        self._tracking: dict[str, dict] = {}     # workspace_id → tracker record
        self._update_log: list[dict] = []
        self._escalations: list[dict] = []

    # ---------- enroll ----------
    def enroll(
        self, workspace_id: str,
        cadence_days: int = CADENCE_DAYS_DEFAULT,
        stale_grace_hours: int = STALE_GRACE_HOURS,
        alert_escalation_hours: int = ALERT_ESCALATION_HOURS,
        attorney_id: str | None = None,
        applicant_id: str | None = None,
        partner_id: str | None = None,
    ) -> dict:
        if cadence_days <= 0:
            raise ValueError("Cadence must be positive")
        if workspace_id in self._tracking:
            return self._tracking[workspace_id]
        record = {
            "workspace_id": workspace_id,
            "cadence_days": cadence_days,
            "stale_grace_hours": stale_grace_hours,
            "alert_escalation_hours": alert_escalation_hours,
            "attorney_id": attorney_id,
            "applicant_id": applicant_id,
            "partner_id": partner_id,
            "active": True,
            "last_update_at": datetime.utcnow().isoformat(),
            "next_update_due_at": (datetime.utcnow() + timedelta(days=cadence_days)).isoformat(),
            "status": "fresh",  # fresh | due_soon | stale | overdue | alert | paused
            "missed_updates": 0,
            "escalation_count": 0,
            "enrolled_at": datetime.utcnow().isoformat(),
        }
        self._tracking[workspace_id] = record
        return record

    def disenroll(self, workspace_id: str, reason: str = "") -> dict | None:
        record = self._tracking.get(workspace_id)
        if record is None:
            return None
        record["active"] = False
        record["disenrolled_at"] = datetime.utcnow().isoformat()
        record["disenrollment_reason"] = reason
        return record

    def pause(self, workspace_id: str, reason: str = "") -> dict:
        record = self._tracking.get(workspace_id)
        if record is None:
            raise ValueError("Workspace not enrolled")
        record["status"] = "paused"
        record["paused_reason"] = reason
        record["paused_at"] = datetime.utcnow().isoformat()
        return record

    def resume(self, workspace_id: str) -> dict:
        record = self._tracking.get(workspace_id)
        if record is None:
            raise ValueError("Workspace not enrolled")
        record["status"] = "fresh"
        record["resumed_at"] = datetime.utcnow().isoformat()
        record["last_update_at"] = datetime.utcnow().isoformat()
        record["next_update_due_at"] = (
            datetime.utcnow() + timedelta(days=record["cadence_days"])
        ).isoformat()
        return record

    # ---------- recording updates ----------
    def record_update(
        self, workspace_id: str,
        actor_id: str,
        kind: str = "status_update",
        body: str = "",
    ) -> dict:
        record = self._tracking.get(workspace_id)
        if record is None:
            raise ValueError("Workspace not enrolled")
        if not record["active"]:
            return record
        now = datetime.utcnow()
        log = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "actor_id": actor_id, "kind": kind,
            "body": body[:500],
            "at": now.isoformat(),
        }
        self._update_log.append(log)
        record["last_update_at"] = now.isoformat()
        record["next_update_due_at"] = (
            now + timedelta(days=record["cadence_days"])
        ).isoformat()
        record["status"] = "fresh"
        return log

    # ---------- ticking ----------
    def tick(self, now: datetime | None = None) -> dict:
        """Walk all active trackers, advance their status, and fire escalations."""
        now = now or datetime.utcnow()
        moved_to_due_soon = []
        moved_to_stale = []
        moved_to_overdue = []
        moved_to_alert = []
        for record in self._tracking.values():
            if not record["active"] or record["status"] == "paused":
                continue
            try:
                due = datetime.fromisoformat(record["next_update_due_at"])
            except ValueError:
                continue
            time_past_due = now - due
            grace = timedelta(hours=record["stale_grace_hours"])
            escalate = timedelta(hours=record["alert_escalation_hours"])
            old_status = record["status"]
            if time_past_due < timedelta(0):
                # Not yet due
                hours_to_due = (-time_past_due).total_seconds() / 3600
                if hours_to_due <= 48 and record["status"] == "fresh":
                    record["status"] = "due_soon"
                    moved_to_due_soon.append(record["workspace_id"])
            elif timedelta(0) <= time_past_due < grace:
                if record["status"] != "stale":
                    record["status"] = "stale"
                    moved_to_stale.append(record["workspace_id"])
            elif grace <= time_past_due < escalate:
                if record["status"] != "overdue":
                    record["status"] = "overdue"
                    record["missed_updates"] += 1
                    moved_to_overdue.append(record["workspace_id"])
                    self._notify_overdue(record)
            else:
                if record["status"] != "alert":
                    record["status"] = "alert"
                    record["escalation_count"] += 1
                    moved_to_alert.append(record["workspace_id"])
                    self._escalate(record, now)
        return {
            "ticked_at": now.isoformat(),
            "moved_to_due_soon": moved_to_due_soon,
            "moved_to_stale": moved_to_stale,
            "moved_to_overdue": moved_to_overdue,
            "moved_to_alert": moved_to_alert,
            "active_tracker_count": sum(1 for r in self._tracking.values() if r["active"]),
        }

    def _notify_overdue(self, record: dict) -> None:
        if not self._notifications:
            return
        # Notify applicant
        if record.get("applicant_id"):
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=record["applicant_id"],
                    title="Your attorney hasn't updated your case recently",
                    body=(
                        f"It's been more than {record['cadence_days']} days since your last update. "
                        "Your attorney has been notified."
                    ),
                    metadata={
                        "intent": "cadence_overdue",
                        "workspace_id": record["workspace_id"],
                    },
                )
            except Exception:
                pass
        # Nudge attorney
        if record.get("attorney_id"):
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=record["attorney_id"],
                    title="Case update overdue",
                    body=(
                        f"Workspace {record['workspace_id']} hasn't had a status update in "
                        f"more than {record['cadence_days']} days. Please update."
                    ),
                    metadata={
                        "intent": "cadence_attorney_nudge",
                        "workspace_id": record["workspace_id"],
                    },
                )
            except Exception:
                pass

    def _escalate(self, record: dict, now: datetime) -> None:
        escalation = {
            "id": str(uuid.uuid4()),
            "workspace_id": record["workspace_id"],
            "attorney_id": record.get("attorney_id"),
            "applicant_id": record.get("applicant_id"),
            "partner_id": record.get("partner_id"),
            "missed_updates": record["missed_updates"],
            "escalation_count": record["escalation_count"],
            "at": now.isoformat(),
        }
        self._escalations.append(escalation)
        if not self._notifications:
            return
        # Notify the partner / escalation contact
        if record.get("partner_id"):
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=record["partner_id"],
                    title="ALERT: Case update has been missed",
                    body=(
                        f"Attorney has not updated workspace {record['workspace_id']} "
                        f"for {record['cadence_days']}+ days past the deadline. "
                        f"Escalation #{record['escalation_count']}."
                    ),
                    metadata={
                        "intent": "cadence_alert_escalation",
                        "workspace_id": record["workspace_id"],
                    },
                )
            except Exception:
                pass

    # ---------- queries ----------
    def get_tracker(self, workspace_id: str) -> dict | None:
        return self._tracking.get(workspace_id)

    def list_trackers(
        self, status: str | None = None, attorney_id: str | None = None,
    ) -> list[dict]:
        out = list(self._tracking.values())
        if status:
            out = [r for r in out if r["status"] == status]
        if attorney_id:
            out = [r for r in out if r.get("attorney_id") == attorney_id]
        return out

    def list_overdue_or_alert(self) -> list[dict]:
        return [r for r in self._tracking.values() if r["status"] in ("overdue", "alert")]

    def list_escalations(self, partner_id: str | None = None, limit: int = 100) -> list[dict]:
        out = self._escalations
        if partner_id:
            out = [e for e in out if e.get("partner_id") == partner_id]
        return out[-limit:]

    def get_update_log(self, workspace_id: str | None = None, limit: int = 100) -> list[dict]:
        log = self._update_log
        if workspace_id:
            log = [u for u in log if u["workspace_id"] == workspace_id]
        return log[-limit:]

    # ---------- attorney response health ----------
    def attorney_response_health(self, attorney_id: str) -> dict:
        records = [r for r in self._tracking.values() if r.get("attorney_id") == attorney_id]
        if not records:
            return {"attorney_id": attorney_id, "score": None, "active_cases": 0}
        active = [r for r in records if r["active"]]
        overdue_or_alert = sum(1 for r in active if r["status"] in ("overdue", "alert"))
        total_missed = sum(r["missed_updates"] for r in records)
        total_escalations = sum(r["escalation_count"] for r in records)
        # Score from 0-100; perfect score has 0 misses / 0 escalations / 0 currently overdue
        if not active:
            score = 100
        else:
            penalty = (
                (overdue_or_alert / len(active)) * 60
                + min(20, total_missed * 2)
                + min(20, total_escalations * 5)
            )
            score = max(0, round(100 - penalty))
        return {
            "attorney_id": attorney_id,
            "score": score,
            "active_cases": len(active),
            "currently_overdue_or_alert": overdue_or_alert,
            "lifetime_missed_updates": total_missed,
            "lifetime_escalations": total_escalations,
            "computed_at": datetime.utcnow().isoformat(),
        }
