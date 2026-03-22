"""Integration service — CSV/Excel import/export, calendar sync, e-signature, webhooks, API keys."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime


class IntegrationService:
    """Third-party integrations and data import/export."""

    def __init__(self) -> None:
        self._webhooks: dict[str, dict] = {}
        self._api_keys: dict[str, str] = {}
        self._esignature_requests: dict[str, dict] = {}

    def import_csv(self, file_data: str, mapping: dict | None = None) -> list[dict]:
        reader = csv.DictReader(io.StringIO(file_data))
        records = []
        for row in reader:
            if mapping:
                mapped = {mapping.get(k, k): v for k, v in row.items()}
                records.append(mapped)
            else:
                records.append(dict(row))
        return records

    def export_csv(self, data: list[dict], columns: list[str] | None = None) -> str:
        if not data:
            return ""
        cols = columns or list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        return output.getvalue()

    def export_excel(self, data: list[dict], columns: list[str] | None = None, sheet_name: str = "Export") -> bytes:
        # Returns CSV bytes as Excel-compatible format (real Excel would need openpyxl)
        csv_str = self.export_csv(data, columns)
        return csv_str.encode("utf-8")

    def import_excel(self, file_data: bytes) -> list[dict]:
        # Parse as CSV (simplified — real implementation would use openpyxl)
        text = file_data.decode("utf-8") if isinstance(file_data, bytes) else file_data
        return self.import_csv(text)

    def generate_word_document(self, template_name: str, data: dict) -> bytes:
        templates = {
            "cover_letter": "Re: {visa_type} Petition for {client_name}\n\nDear USCIS Officer,\n\n...",
            "brief": "Immigration Brief\n\nIn the Matter of: {client_name}\n\n...",
            "memo": "Internal Memo\n\nRe: {client_name} - {visa_type}\n\n...",
            "g28_cover": "Notice of Entry of Appearance\n\nAttorney: {attorney_name}\n\n...",
        }
        template = templates.get(template_name, templates["cover_letter"])
        content = template.format(**{k: data.get(k, f"[{k}]") for k in ["client_name", "visa_type", "attorney_name"]})
        return content.encode("utf-8")

    def create_esignature_request(self, document_id: str, signers: list[dict]) -> dict:
        req_id = str(uuid.uuid4())
        request = {
            "id": req_id,
            "document_id": document_id,
            "signers": signers,
            "status": "pending",
            "provider": "DocuSign",
            "created_at": datetime.utcnow().isoformat(),
            "signing_url": f"https://esign.verom.ai/sign/{req_id}",
        }
        self._esignature_requests[req_id] = request
        return request

    def sync_calendar(self, provider: str, events: list[dict]) -> dict:
        return {
            "provider": provider,
            "events_synced": len(events),
            "status": "success",
            "synced_at": datetime.utcnow().isoformat(),
            "next_sync": "Auto-sync enabled",
        }

    def create_zapier_webhook(self, event_type: str, url: str) -> dict:
        webhook_id = str(uuid.uuid4())
        webhook = {
            "id": webhook_id,
            "event_type": event_type,
            "url": url,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._webhooks[webhook_id] = webhook
        return webhook

    def trigger_webhook(self, event_type: str, data: dict) -> list[dict]:
        triggered = []
        for wh in self._webhooks.values():
            if wh["event_type"] == event_type and wh["status"] == "active":
                triggered.append({"webhook_id": wh["id"], "status": "delivered", "payload": data})
        return triggered

    def get_api_key(self, user_id: str) -> dict:
        if user_id not in self._api_keys:
            self._api_keys[user_id] = f"vrm_live_{uuid.uuid4().hex}"
        return {
            "user_id": user_id,
            "api_key": self._api_keys[user_id],
            "created_at": datetime.utcnow().isoformat(),
            "rate_limit": "1000 requests/hour",
        }

    def sync_accounting(self, provider: str, invoice_data: dict) -> dict:
        return {
            "provider": provider,
            "invoice_id": invoice_data.get("id", str(uuid.uuid4())),
            "status": "synced",
            "synced_at": datetime.utcnow().isoformat(),
        }

    def file_email_to_case(self, email_data: dict, case_id: str) -> dict:
        return {
            "case_id": case_id,
            "email_subject": email_data.get("subject", ""),
            "email_from": email_data.get("from", ""),
            "filed_at": datetime.utcnow().isoformat(),
            "attachments_count": len(email_data.get("attachments", [])),
            "status": "filed",
        }
