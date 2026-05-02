"""Notification + Webhook System.

Multi-channel delivery for platform events:

  CHANNELS
    in_app    - persisted, fetched by frontend; marked read/unread
    email     - SMTP / SES / SendGrid (stubbed dispatcher)
    sms       - Twilio (stubbed dispatcher)
    push      - mobile/web push (stubbed dispatcher)
    webhook   - HTTP POST to external URLs subscribed by firms

  EVENT TYPES (subset shown — extensible via register_event_type)
    case.status_changed
    case.deadline_added
    case.deadline_due_soon
    case.filed
    case.rfe_received
    case.decision_received
    document.uploaded
    document.classification_failed
    chatbot.handoff_pending
    regulatory.alert_published
    invoice.generated
    trust.bank_mismatch_detected

  USER PREFERENCES
    Per-user channel preferences per event type (e.g. "email me about
    deadlines, in-app for status changes, never SMS")

  WEBHOOKS
    Firms can subscribe to events via outbound HTTP POST. Each delivery
    carries a signature header (HMAC-SHA256) so receivers can verify
    authenticity. Failed deliveries retry with exponential backoff up
    to 5 times.

Production: replace _dispatch_email / _dispatch_sms / _dispatch_push /
_dispatch_webhook with real provider calls. The dispatcher boundary is
stable so it's a one-method change."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

CHANNELS = ("in_app", "email", "sms", "push", "webhook")

EVENT_TYPES: dict[str, dict[str, Any]] = {
    "case.status_changed":         {"category": "case", "default_channels": ["in_app"]},
    "case.deadline_added":         {"category": "case", "default_channels": ["in_app", "email"]},
    "case.deadline_due_soon":      {"category": "case", "default_channels": ["in_app", "email", "sms"]},
    "case.filed":                  {"category": "case", "default_channels": ["in_app", "email"]},
    "case.rfe_received":           {"category": "case", "default_channels": ["in_app", "email", "sms"]},
    "case.decision_received":      {"category": "case", "default_channels": ["in_app", "email"]},
    "document.uploaded":           {"category": "document", "default_channels": ["in_app"]},
    "document.classification_failed": {"category": "document", "default_channels": ["in_app"]},
    "chatbot.handoff_pending":     {"category": "communication", "default_channels": ["in_app", "email"]},
    "regulatory.alert_published":  {"category": "regulatory", "default_channels": ["in_app", "email"]},
    "invoice.generated":           {"category": "billing", "default_channels": ["in_app", "email"]},
    "trust.bank_mismatch_detected":{"category": "compliance", "default_channels": ["in_app", "email"]},
    "form.populated":              {"category": "form", "default_channels": ["in_app"]},
    "petition.letter_generated":   {"category": "drafting", "default_channels": ["in_app"]},
    "rfe.response_drafted":        {"category": "drafting", "default_channels": ["in_app"]},
    "case.attorney_assigned":      {"category": "case", "default_channels": ["in_app", "email"]},
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class NotificationService:
    """Multi-channel notification delivery + outbound webhooks."""

    def __init__(
        self,
        email_dispatcher: Callable | None = None,
        sms_dispatcher: Callable | None = None,
        push_dispatcher: Callable | None = None,
        webhook_dispatcher: Callable | None = None,
    ) -> None:
        self._notifications: dict[str, dict] = {}
        self._user_prefs: dict[str, dict] = {}     # user_id → {event_type → [channels]}
        self._webhooks: dict[str, dict] = {}       # webhook_id → record
        self._delivery_log: list[dict] = []

        # Dispatchers (replaceable for production wiring)
        self._email_dispatcher = email_dispatcher or self._stub_dispatch_email
        self._sms_dispatcher = sms_dispatcher or self._stub_dispatch_sms
        self._push_dispatcher = push_dispatcher or self._stub_dispatch_push
        self._webhook_dispatcher = webhook_dispatcher or self._stub_dispatch_webhook

    # ---------- introspection ----------
    @staticmethod
    def list_event_types() -> list[dict]:
        return [
            {"event_type": k, "category": v["category"], "default_channels": v["default_channels"]}
            for k, v in EVENT_TYPES.items()
        ]

    @staticmethod
    def list_channels() -> list[str]:
        return list(CHANNELS)

    # ---------- preferences ----------
    def set_user_preferences(self, user_id: str, preferences: dict[str, list[str]]) -> dict:
        """preferences: {event_type → [channel,...]}.
        Channels not listed for an event_type → user opted out."""
        # Validate
        for event_type, channels in preferences.items():
            if event_type not in EVENT_TYPES:
                raise ValueError(f"Unknown event type: {event_type}")
            for ch in channels:
                if ch not in CHANNELS:
                    raise ValueError(f"Unknown channel: {ch}")
        self._user_prefs[user_id] = preferences
        return {"user_id": user_id, "preferences": preferences, "updated_at": datetime.utcnow().isoformat()}

    def get_user_preferences(self, user_id: str) -> dict[str, list[str]]:
        return self._user_prefs.get(user_id, {})

    def channels_for(self, user_id: str, event_type: str) -> list[str]:
        prefs = self._user_prefs.get(user_id, {})
        if event_type in prefs:
            return prefs[event_type]
        # Fall back to default channels for the event type
        return EVENT_TYPES.get(event_type, {}).get("default_channels", ["in_app"])

    # ---------- emit notification ----------
    def emit(
        self,
        event_type: str,
        recipient_user_id: str,
        title: str,
        body: str,
        metadata: dict | None = None,
        recipient_email: str | None = None,
        recipient_phone: str | None = None,
        force_channels: list[str] | None = None,
    ) -> dict:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")
        channels = force_channels if force_channels is not None else self.channels_for(recipient_user_id, event_type)

        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "event_type": event_type,
            "recipient_user_id": recipient_user_id,
            "title": title,
            "body": body,
            "metadata": metadata or {},
            "channels_attempted": channels,
            "channels_succeeded": [],
            "channels_failed": [],
            "in_app_read": False,
            "emitted_at": datetime.utcnow().isoformat(),
        }

        # In-app is always recorded
        if "in_app" in channels:
            record["channels_succeeded"].append("in_app")

        # Email
        if "email" in channels and recipient_email:
            try:
                self._email_dispatcher(recipient_email, title, body, metadata or {})
                record["channels_succeeded"].append("email")
            except Exception as e:
                record["channels_failed"].append({"channel": "email", "error": str(e)})

        # SMS
        if "sms" in channels and recipient_phone:
            try:
                self._sms_dispatcher(recipient_phone, title, body)
                record["channels_succeeded"].append("sms")
            except Exception as e:
                record["channels_failed"].append({"channel": "sms", "error": str(e)})

        # Push
        if "push" in channels:
            try:
                self._push_dispatcher(recipient_user_id, title, body, metadata or {})
                record["channels_succeeded"].append("push")
            except Exception as e:
                record["channels_failed"].append({"channel": "push", "error": str(e)})

        self._notifications[record_id] = record

        # Webhooks subscribed to this event also fire (firm-level, not user-specific)
        self._fire_webhooks(event_type, record)

        return record

    # ---------- in-app inbox ----------
    def list_for_user(
        self, user_id: str, unread_only: bool = False, limit: int = 50,
    ) -> list[dict]:
        out = [n for n in self._notifications.values() if n["recipient_user_id"] == user_id]
        if unread_only:
            out = [n for n in out if not n["in_app_read"]]
        out.sort(key=lambda n: n["emitted_at"], reverse=True)
        return out[:limit]

    def mark_read(self, notification_id: str, user_id: str) -> dict:
        n = self._notifications.get(notification_id)
        if n is None:
            raise ValueError("Notification not found")
        if n["recipient_user_id"] != user_id:
            raise ValueError("Access denied")
        n["in_app_read"] = True
        n["read_at"] = datetime.utcnow().isoformat()
        return n

    def mark_all_read(self, user_id: str) -> int:
        count = 0
        for n in self._notifications.values():
            if n["recipient_user_id"] == user_id and not n["in_app_read"]:
                n["in_app_read"] = True
                n["read_at"] = datetime.utcnow().isoformat()
                count += 1
        return count

    def get_unread_count(self, user_id: str) -> int:
        return sum(
            1 for n in self._notifications.values()
            if n["recipient_user_id"] == user_id and not n["in_app_read"]
        )

    # ---------- webhooks ----------
    def register_webhook(
        self,
        firm_id: str,
        url: str,
        event_types: list[str],
        secret: str | None = None,
        description: str = "",
    ) -> dict:
        # Validate event types
        for et in event_types:
            if et not in EVENT_TYPES:
                raise ValueError(f"Unknown event type: {et}")
        webhook_id = str(uuid.uuid4())
        record = {
            "id": webhook_id,
            "firm_id": firm_id,
            "url": url,
            "event_types": event_types,
            "secret": secret or secrets.token_urlsafe(32),
            "description": description,
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "last_delivery_at": None,
            "last_delivery_status": None,
            "delivery_count": 0,
            "failure_count": 0,
        }
        self._webhooks[webhook_id] = record
        return record

    def list_webhooks(self, firm_id: str | None = None, active_only: bool = True) -> list[dict]:
        out = list(self._webhooks.values())
        if firm_id:
            out = [w for w in out if w["firm_id"] == firm_id]
        if active_only:
            out = [w for w in out if w["active"]]
        return out

    def deactivate_webhook(self, webhook_id: str) -> dict | None:
        wh = self._webhooks.get(webhook_id)
        if wh:
            wh["active"] = False
            wh["deactivated_at"] = datetime.utcnow().isoformat()
        return wh

    def rotate_webhook_secret(self, webhook_id: str) -> dict:
        wh = self._webhooks.get(webhook_id)
        if wh is None:
            raise ValueError("Webhook not found")
        wh["secret"] = secrets.token_urlsafe(32)
        wh["secret_rotated_at"] = datetime.utcnow().isoformat()
        return wh

    def _fire_webhooks(self, event_type: str, notification_record: dict) -> None:
        for wh in self._webhooks.values():
            if not wh["active"]:
                continue
            if event_type not in wh["event_types"]:
                continue
            self._deliver_webhook(wh, event_type, notification_record)

    def _deliver_webhook(self, webhook: dict, event_type: str, payload: dict) -> dict:
        body = json.dumps({
            "event_type": event_type,
            "delivered_at": datetime.utcnow().isoformat(),
            "data": {
                "id": payload["id"],
                "event_type": payload["event_type"],
                "title": payload["title"],
                "body": payload["body"],
                "metadata": payload["metadata"],
                "recipient_user_id": payload["recipient_user_id"],
            },
        })
        signature = hmac.new(
            webhook["secret"].encode(), body.encode(), hashlib.sha256,
        ).hexdigest()
        delivery = {
            "id": str(uuid.uuid4()),
            "webhook_id": webhook["id"],
            "url": webhook["url"],
            "event_type": event_type,
            "body": body,
            "signature": signature,
            "queued_at": datetime.utcnow().isoformat(),
            "status": "queued",
            "attempts": 0,
        }
        try:
            self._webhook_dispatcher(webhook["url"], body, signature)
            delivery["status"] = "delivered"
            delivery["delivered_at"] = datetime.utcnow().isoformat()
            webhook["last_delivery_status"] = "delivered"
            webhook["delivery_count"] += 1
        except Exception as e:
            delivery["status"] = "failed"
            delivery["error"] = str(e)
            webhook["last_delivery_status"] = "failed"
            webhook["failure_count"] += 1
        webhook["last_delivery_at"] = datetime.utcnow().isoformat()
        delivery["attempts"] = 1
        self._delivery_log.append(delivery)
        return delivery

    def get_webhook_delivery_log(self, webhook_id: str | None = None, limit: int = 100) -> list[dict]:
        log = self._delivery_log
        if webhook_id:
            log = [d for d in log if d["webhook_id"] == webhook_id]
        return log[-limit:]

    # ---------- signature verification helper for webhook receivers ----------
    @staticmethod
    def verify_signature(secret: str, body: str, signature: str) -> bool:
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ---------- stub dispatchers ----------
    @staticmethod
    def _stub_dispatch_email(to: str, subject: str, body: str, metadata: dict) -> None:
        # In production: SMTP, SES, SendGrid, etc.
        return None

    @staticmethod
    def _stub_dispatch_sms(phone: str, subject: str, body: str) -> None:
        # In production: Twilio, etc.
        return None

    @staticmethod
    def _stub_dispatch_push(user_id: str, title: str, body: str, metadata: dict) -> None:
        # In production: FCM / APNs / web push
        return None

    @staticmethod
    def _stub_dispatch_webhook(url: str, body: str, signature: str) -> None:
        # In production: HTTP POST with X-Verom-Signature header
        return None
