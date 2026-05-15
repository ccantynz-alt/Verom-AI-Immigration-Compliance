"""WhatsApp Channel Service — international applicant communication.

Outside the US, WhatsApp is how immigration runs. This service is the
WhatsApp Business API adapter: a conversation registry, inbound/outbound
message normalization, template-message support (USCIS notice forwarding,
status updates, document requests), and a routing layer that surfaces
messages into NotificationService and ClientChatbotService.

Production: wires to the WhatsApp Business Cloud API. The dispatcher seam
(_send_whatsapp_message) is the only place the real provider call lives.
This implementation provides a deterministic mock for dev/test that
records the outbound payload and lets test callers verify it.

Composes with:
  - NotificationService (whatsapp becomes a delivery channel like email/sms)
  - ClientChatbotService (inbound applicant messages flow through the bot)
  - ConsultationBookingService (consult reminders via template)
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Callable


# WhatsApp Business API supports approved templates only for outbound
# messages outside the 24-hour customer-care window.
TEMPLATE_KINDS: dict[str, dict[str, Any]] = {
    "case_status_update": {
        "label": "Case status update",
        "category": "utility",
        "body": "Your {visa_type} case ({receipt}) is now {status}. Tap to view details.",
        "variables": ["visa_type", "receipt", "status"],
    },
    "document_request": {
        "label": "Document request",
        "category": "utility",
        "body": "We need {document_name} for your case. Please reply with a photo or upload via the secure link: {upload_url}",
        "variables": ["document_name", "upload_url"],
    },
    "appointment_confirmation": {
        "label": "Consultation confirmation",
        "category": "utility",
        "body": "Your consultation is confirmed for {date} at {time} ({timezone}). Join: {video_url}",
        "variables": ["date", "time", "timezone", "video_url"],
    },
    "rfe_received": {
        "label": "RFE received notification",
        "category": "utility",
        "body": "USCIS issued a Request for Evidence on your case. Your attorney will reach out within 48h. Response is due by {due_date}.",
        "variables": ["due_date"],
    },
    "approval": {
        "label": "Approval notification",
        "category": "utility",
        "body": "Great news! Your {visa_type} case has been APPROVED. Your attorney will follow up with the next steps.",
        "variables": ["visa_type"],
    },
    "filing_confirmation": {
        "label": "Filing confirmation",
        "category": "utility",
        "body": "Your {visa_type} petition has been filed with USCIS. Receipt: {receipt}. Filed on {filed_date}.",
        "variables": ["visa_type", "receipt", "filed_date"],
    },
    "marketing_promotion": {
        "label": "Marketing promotion",
        "category": "marketing",
        "body": "{custom_body}",
        "variables": ["custom_body"],
    },
}


CONVERSATION_STATES = ("active", "snoozed", "closed", "archived")


# Phone-number validation: E.164 format
_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class WhatsAppChannelService:
    """WhatsApp Business adapter — outbound templates + inbound message routing."""

    def __init__(
        self,
        notification_service: Any | None = None,
        client_chatbot_service: Any | None = None,
        whatsapp_dispatcher: Callable | None = None,
    ) -> None:
        self._notifications = notification_service
        self._chatbot = client_chatbot_service
        self._dispatcher = whatsapp_dispatcher or self._stub_dispatch
        self._conversations: dict[str, dict] = {}     # convo_id → record
        self._messages: list[dict] = []
        self._template_log: list[dict] = []

    # ---------- introspection ----------
    @staticmethod
    def list_templates() -> list[dict]:
        return [
            {"kind": k, "label": v["label"], "category": v["category"], "variables": v["variables"]}
            for k, v in TEMPLATE_KINDS.items()
        ]

    @staticmethod
    def get_template(kind: str) -> dict | None:
        return TEMPLATE_KINDS.get(kind)

    # ---------- conversation lifecycle ----------
    def get_or_create_conversation(
        self, applicant_user_id: str, phone_e164: str,
        workspace_id: str | None = None,
    ) -> dict:
        if not _E164.match(phone_e164):
            raise ValueError(f"Invalid E.164 phone: {phone_e164}")
        # Find existing
        for c in self._conversations.values():
            if c["applicant_user_id"] == applicant_user_id and c["phone_e164"] == phone_e164:
                return c
        convo_id = str(uuid.uuid4())
        record = {
            "id": convo_id,
            "applicant_user_id": applicant_user_id,
            "phone_e164": phone_e164,
            "workspace_id": workspace_id,
            "state": "active",
            "opened_at": datetime.utcnow().isoformat(),
            "last_message_at": None,
            "last_inbound_at": None,
            "message_count": 0,
            "in_24h_window": False,
        }
        self._conversations[convo_id] = record
        return record

    def get_conversation(self, convo_id: str) -> dict | None:
        return self._conversations.get(convo_id)

    def list_conversations(
        self, applicant_user_id: str | None = None,
        state: str | None = None,
    ) -> list[dict]:
        out = list(self._conversations.values())
        if applicant_user_id:
            out = [c for c in out if c["applicant_user_id"] == applicant_user_id]
        if state:
            out = [c for c in out if c["state"] == state]
        return sorted(out, key=lambda c: c.get("last_message_at") or c["opened_at"], reverse=True)

    def update_state(self, convo_id: str, state: str) -> dict:
        if state not in CONVERSATION_STATES:
            raise ValueError(f"Unknown conversation state: {state}")
        c = self._conversations.get(convo_id)
        if c is None:
            raise ValueError("Conversation not found")
        c["state"] = state
        c["state_updated_at"] = datetime.utcnow().isoformat()
        return c

    # ---------- outbound template ----------
    def send_template(
        self,
        convo_id: str,
        template_kind: str,
        variables: dict[str, str],
        actor_user_id: str | None = None,
    ) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError("Conversation not found")
        spec = TEMPLATE_KINDS.get(template_kind)
        if spec is None:
            raise ValueError(f"Unknown template: {template_kind}")
        # Validate all required variables are provided
        missing = [v for v in spec["variables"] if v not in variables]
        if missing:
            raise ValueError(f"Missing variables for template: {missing}")
        # Render
        try:
            body = spec["body"].format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable for template: {e}") from e

        # Dispatch
        msg_id = str(uuid.uuid4())
        send_result = self._dispatcher(
            phone=convo["phone_e164"], body=body,
            template_kind=template_kind, variables=variables,
        )
        message = {
            "id": msg_id,
            "conversation_id": convo_id,
            "direction": "outbound",
            "channel": "whatsapp",
            "is_template": True,
            "template_kind": template_kind,
            "variables": variables,
            "body": body,
            "phone_e164": convo["phone_e164"],
            "actor_user_id": actor_user_id,
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_status": send_result.get("status", "queued"),
            "provider_message_id": send_result.get("provider_message_id"),
        }
        self._messages.append(message)
        convo["last_message_at"] = message["sent_at"]
        convo["message_count"] += 1
        self._template_log.append({
            "convo_id": convo_id,
            "template_kind": template_kind,
            "category": spec["category"],
            "at": message["sent_at"],
        })
        return message

    # ---------- outbound free-text (only inside 24h window) ----------
    def send_freeform_message(
        self,
        convo_id: str,
        body: str,
        actor_user_id: str | None = None,
    ) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError("Conversation not found")
        if not convo.get("in_24h_window"):
            raise ValueError(
                "Outside 24-hour customer-care window. Use a template message "
                "(send_template) or wait for the applicant to message first."
            )
        msg_id = str(uuid.uuid4())
        send_result = self._dispatcher(
            phone=convo["phone_e164"], body=body, template_kind=None, variables=None,
        )
        message = {
            "id": msg_id,
            "conversation_id": convo_id,
            "direction": "outbound",
            "channel": "whatsapp",
            "is_template": False,
            "body": body,
            "phone_e164": convo["phone_e164"],
            "actor_user_id": actor_user_id,
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_status": send_result.get("status", "queued"),
            "provider_message_id": send_result.get("provider_message_id"),
        }
        self._messages.append(message)
        convo["last_message_at"] = message["sent_at"]
        convo["message_count"] += 1
        return message

    # ---------- inbound webhook ----------
    def receive_inbound(
        self,
        phone_e164: str,
        body: str,
        provider_message_id: str | None = None,
        applicant_user_id: str | None = None,
        workspace_id: str | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        if not _E164.match(phone_e164):
            raise ValueError(f"Invalid E.164 phone: {phone_e164}")
        # Find existing conversation by phone or create new (need applicant_user_id)
        convo = None
        for c in self._conversations.values():
            if c["phone_e164"] == phone_e164:
                convo = c
                break
        if convo is None:
            if applicant_user_id is None:
                raise ValueError("Cannot create new conversation without applicant_user_id")
            convo = self.get_or_create_conversation(applicant_user_id, phone_e164, workspace_id)

        # Open the 24-hour customer-care window
        convo["in_24h_window"] = True
        convo["last_inbound_at"] = datetime.utcnow().isoformat()

        msg_id = str(uuid.uuid4())
        message = {
            "id": msg_id,
            "conversation_id": convo["id"],
            "direction": "inbound",
            "channel": "whatsapp",
            "body": body,
            "phone_e164": phone_e164,
            "provider_message_id": provider_message_id,
            "received_at": datetime.utcnow().isoformat(),
            "attachments": attachments or [],
        }
        self._messages.append(message)
        convo["last_message_at"] = message["received_at"]
        convo["message_count"] += 1

        # Route into the chatbot if wired
        if self._chatbot and convo.get("workspace_id"):
            try:
                bot_convo = self._chatbot.get_or_create_conversation(convo["workspace_id"], convo["applicant_user_id"])
                bot_response = self._chatbot.ask(bot_convo["id"], body)
                # Forward bot reply back to WhatsApp (only inside the open window)
                if bot_response.get("bot_message"):
                    try:
                        self.send_freeform_message(
                            convo["id"], bot_response["bot_message"]["body"],
                            actor_user_id="chatbot",
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        return message

    # ---------- queries ----------
    def list_messages(
        self, convo_id: str | None = None,
        direction: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        out = self._messages
        if convo_id:
            out = [m for m in out if m["conversation_id"] == convo_id]
        if direction:
            out = [m for m in out if m["direction"] == direction]
        return out[-limit:]

    def get_template_send_log(self, limit: int = 200) -> list[dict]:
        return self._template_log[-limit:]

    # ---------- dispatcher hooks ----------
    @staticmethod
    def _stub_dispatch(phone: str, body: str, template_kind: str | None = None,
                        variables: dict | None = None) -> dict:
        # Production: WhatsApp Business Cloud API call.
        return {
            "status": "queued",
            "provider_message_id": f"wamid.MOCK.{uuid.uuid4().hex[:12]}",
        }

    def register_dispatcher(self, dispatcher: Callable) -> None:
        self._dispatcher = dispatcher
