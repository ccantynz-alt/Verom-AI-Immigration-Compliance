"""Government Status Polling Daemon — attorney-notified-before-client.

The mechanic that solves the #1 USCIS portal complaint: attorneys finding out from
clients. This service maintains a polling registry of every active receipt number,
checks status against the wired government clients on a cadence, and pushes a
notification to the assigned attorney 30+ minutes before any client-facing surface
is allowed to display the new state.

Design:
  - Subscriptions: workspace_id + receipt_number + agency, registered after a filing
  - Polling cadence: configurable per agency (USCIS = 60 min, DOL = 240 min,
    DOS = 360 min, EOIR = 360 min). High-priority cases poll faster.
  - Status diff detection: when the latest poll differs from the last-seen state,
    fire an attorney_first_notification, then schedule the client_notification
    to fire after the configured silence window (30 min default).
  - Backoff: failed polls back off exponentially (1m → 2m → 4m → 8m max 30m)
  - Audit: every poll attempt + every notification event is logged

The actual government-API calls go through pluggable callables so production
swaps in the real `USCISClientService` / `EFilingProxyService.acknowledge` /
DOL / DOS / EOIR clients without changing this service's surface.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Cadence catalog
# ---------------------------------------------------------------------------

DEFAULT_CADENCE_MINUTES: dict[str, int] = {
    "uscis": 60,
    "dol": 240,
    "dos": 360,
    "eoir": 360,
    "sevis": 240,
    "ircc": 360,    # Canada
    "dha": 360,     # Australia
    "ukvi": 360,    # UK Home Office
}

DEFAULT_ATTORNEY_LEAD_MINUTES = 30   # how long before the client sees an update

POLL_PRIORITIES = ("normal", "high", "urgent")
PRIORITY_MULTIPLIER = {"normal": 1.0, "high": 0.5, "urgent": 0.25}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class GovernmentStatusPollingService:
    """Polling daemon registry + diff detection."""

    def __init__(
        self,
        notification_service: Any | None = None,
        case_workspace: Any | None = None,
        status_clients: dict[str, Callable] | None = None,
    ) -> None:
        self._notifications = notification_service
        self._cases = case_workspace
        self._status_clients = status_clients or {}    # agency → callable(receipt_number) -> dict
        self._subscriptions: dict[str, dict] = {}
        self._poll_log: list[dict] = []
        self._notification_log: list[dict] = []

    # ---------- registration ----------
    def subscribe(
        self,
        receipt_number: str,
        agency: str,
        workspace_id: str | None = None,
        attorney_id: str | None = None,
        applicant_id: str | None = None,
        priority: str = "normal",
        attorney_lead_minutes: int = DEFAULT_ATTORNEY_LEAD_MINUTES,
    ) -> dict:
        if agency not in DEFAULT_CADENCE_MINUTES:
            raise ValueError(f"Unknown agency: {agency}")
        if priority not in POLL_PRIORITIES:
            raise ValueError(f"Unknown priority: {priority}")
        sub_id = str(uuid.uuid4())
        record = {
            "id": sub_id,
            "receipt_number": receipt_number, "agency": agency,
            "workspace_id": workspace_id, "attorney_id": attorney_id,
            "applicant_id": applicant_id, "priority": priority,
            "attorney_lead_minutes": attorney_lead_minutes,
            "active": True,
            "registered_at": datetime.utcnow().isoformat(),
            "last_seen_state": None,
            "last_polled_at": None,
            "next_poll_due_at": datetime.utcnow().isoformat(),
            "consecutive_failures": 0,
        }
        self._subscriptions[sub_id] = record
        return record

    def unsubscribe(self, subscription_id: str) -> bool:
        sub = self._subscriptions.get(subscription_id)
        if sub is None:
            return False
        sub["active"] = False
        sub["unsubscribed_at"] = datetime.utcnow().isoformat()
        return True

    def get_subscription(self, subscription_id: str) -> dict | None:
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(
        self,
        agency: str | None = None,
        attorney_id: str | None = None,
        active_only: bool = True,
    ) -> list[dict]:
        out = list(self._subscriptions.values())
        if agency:
            out = [s for s in out if s["agency"] == agency]
        if attorney_id:
            out = [s for s in out if s.get("attorney_id") == attorney_id]
        if active_only:
            out = [s for s in out if s["active"]]
        return out

    # ---------- polling ----------
    def get_due_subscriptions(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.utcnow()
        out = []
        for s in self._subscriptions.values():
            if not s["active"]:
                continue
            if s.get("next_poll_due_at"):
                if datetime.fromisoformat(s["next_poll_due_at"]) <= now:
                    out.append(s)
            else:
                out.append(s)
        return out

    def poll_subscription(self, subscription_id: str) -> dict:
        sub = self._subscriptions.get(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription not found: {subscription_id}")
        if not sub["active"]:
            raise ValueError("Subscription is inactive")
        client = self._status_clients.get(sub["agency"])
        now = datetime.utcnow()
        sub["last_polled_at"] = now.isoformat()

        if client is None:
            # No client wired — record stub poll
            poll = self._record_poll(sub, ok=True, response={"status": "client_not_wired"})
            self._schedule_next(sub, success=True)
            return poll

        try:
            response = client(sub["receipt_number"])
        except Exception as e:
            sub["consecutive_failures"] += 1
            poll = self._record_poll(sub, ok=False, response={"error": str(e)})
            self._schedule_next(sub, success=False)
            return poll

        sub["consecutive_failures"] = 0
        new_state = self._extract_state(response)
        old_state = sub.get("last_seen_state")
        state_changed = (new_state != old_state) and new_state is not None
        poll = self._record_poll(sub, ok=True, response=response, state_changed=state_changed)

        if state_changed:
            sub["last_seen_state"] = new_state
            self._handle_state_change(sub, old_state=old_state, new_state=new_state, response=response)

        self._schedule_next(sub, success=True)
        return poll

    def _record_poll(self, sub: dict, ok: bool, response: dict, state_changed: bool = False) -> dict:
        poll = {
            "id": str(uuid.uuid4()),
            "subscription_id": sub["id"],
            "receipt_number": sub["receipt_number"],
            "agency": sub["agency"],
            "ok": ok,
            "response": response,
            "state_changed": state_changed,
            "polled_at": sub["last_polled_at"],
        }
        self._poll_log.append(poll)
        return poll

    @staticmethod
    def _extract_state(response: dict) -> str | None:
        # Government clients return shapes like {"status": "...", ...}
        if not isinstance(response, dict):
            return None
        return response.get("status") or response.get("state") or response.get("case_status")

    def _schedule_next(self, sub: dict, success: bool) -> None:
        agency = sub["agency"]
        base_minutes = DEFAULT_CADENCE_MINUTES.get(agency, 240)
        if not success:
            # Exponential backoff up to 30 minutes
            backoff = min(30, max(1, 2 ** (sub["consecutive_failures"] - 1)))
            next_due = datetime.utcnow() + timedelta(minutes=backoff)
        else:
            multiplier = PRIORITY_MULTIPLIER.get(sub.get("priority", "normal"), 1.0)
            next_due = datetime.utcnow() + timedelta(minutes=base_minutes * multiplier)
        sub["next_poll_due_at"] = next_due.isoformat()

    # ---------- attorney-first notification ----------
    def _handle_state_change(
        self, sub: dict, old_state: str | None, new_state: str, response: dict,
    ) -> None:
        attorney_id = sub.get("attorney_id")
        applicant_id = sub.get("applicant_id")
        title = f"USCIS status changed: {sub['receipt_number']}"
        body = f"{old_state or 'unknown'} → {new_state}"
        # Fire to attorney immediately
        if attorney_id and self._notifications:
            try:
                self._notifications.emit(
                    event_type="case.status_changed",
                    recipient_user_id=attorney_id,
                    title=title, body=body,
                    metadata={
                        "receipt_number": sub["receipt_number"],
                        "agency": sub["agency"],
                        "old_state": old_state, "new_state": new_state,
                        "case_id": sub.get("workspace_id"),
                        "intent": "attorney_first",
                    },
                )
            except Exception:
                pass
        # Schedule the applicant notification after the lead window
        scheduled_for = (
            datetime.utcnow() + timedelta(minutes=sub.get("attorney_lead_minutes", DEFAULT_ATTORNEY_LEAD_MINUTES))
        ).isoformat()
        record = {
            "id": str(uuid.uuid4()),
            "subscription_id": sub["id"],
            "attorney_id": attorney_id, "applicant_id": applicant_id,
            "old_state": old_state, "new_state": new_state,
            "attorney_notified_at": datetime.utcnow().isoformat() if attorney_id else None,
            "applicant_scheduled_for": scheduled_for,
            "applicant_delivered_at": None,
        }
        self._notification_log.append(record)

    def deliver_pending_applicant_notifications(self, now: datetime | None = None) -> list[dict]:
        """Tick: deliver applicant notifications whose lead window has passed."""
        now = now or datetime.utcnow()
        delivered = []
        for record in self._notification_log:
            if record.get("applicant_delivered_at"):
                continue
            if not record.get("applicant_id"):
                continue
            scheduled = datetime.fromisoformat(record["applicant_scheduled_for"])
            if scheduled <= now:
                if self._notifications:
                    try:
                        self._notifications.emit(
                            event_type="case.status_changed",
                            recipient_user_id=record["applicant_id"],
                            title="Case status update from USCIS",
                            body=f"{record['old_state'] or 'unknown'} → {record['new_state']}",
                            metadata={
                                "intent": "applicant_followup",
                                "subscription_id": record["subscription_id"],
                            },
                        )
                    except Exception:
                        pass
                record["applicant_delivered_at"] = datetime.utcnow().isoformat()
                delivered.append(record)
        return delivered

    # ---------- introspection ----------
    def get_poll_log(self, subscription_id: str | None = None, limit: int = 200) -> list[dict]:
        log = self._poll_log
        if subscription_id:
            log = [p for p in log if p["subscription_id"] == subscription_id]
        return log[-limit:]

    def get_notification_log(self, attorney_id: str | None = None, limit: int = 200) -> list[dict]:
        log = self._notification_log
        if attorney_id:
            log = [n for n in log if n.get("attorney_id") == attorney_id]
        return log[-limit:]

    @staticmethod
    def list_supported_agencies() -> list[str]:
        return list(DEFAULT_CADENCE_MINUTES.keys())

    @staticmethod
    def list_priorities() -> list[str]:
        return list(POLL_PRIORITIES)

    def register_status_client(self, agency: str, client_callable: Callable) -> None:
        """Wire a real status client (production swap)."""
        self._status_clients[agency] = client_callable
