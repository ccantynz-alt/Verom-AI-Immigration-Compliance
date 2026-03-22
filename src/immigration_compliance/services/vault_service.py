"""Document vault and receipt tracker service.

The vault is the feature that makes users never leave — all their immigration
documents in one place with expiration tracking and smart alerts.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone

from immigration_compliance.models.consultation import (
    ExpirationAlert,
    ReceiptTracker,
    TravelAdvisory,
    TravelAdvisoryRequest,
    VaultDocument,
)


class VaultService:
    """Secure document vault with expiration tracking."""

    def __init__(self) -> None:
        self._documents: dict[str, VaultDocument] = {}
        self._receipts: dict[str, ReceiptTracker] = {}

    # --- Document Vault ---

    def add_document(self, doc: VaultDocument) -> VaultDocument:
        doc_id = f"vault_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        saved = doc.model_copy(update={"id": doc_id, "uploaded_at": now})
        self._documents[doc_id] = saved
        return saved

    def get_document(self, doc_id: str) -> VaultDocument | None:
        return self._documents.get(doc_id)

    def list_documents(self, user_id: str) -> list[VaultDocument]:
        return [d for d in self._documents.values() if d.user_id == user_id]

    def delete_document(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None

    def get_expiration_alerts(self, user_id: str) -> list[ExpirationAlert]:
        """Get expiration alerts for all documents with expiry dates."""
        today = date.today()
        alerts: list[ExpirationAlert] = []

        for doc in self._documents.values():
            if doc.user_id != user_id or not doc.expiration_date:
                continue
            try:
                exp = date.fromisoformat(doc.expiration_date)
            except ValueError:
                continue

            days = (exp - today).days

            if days < 0:
                urgency = "expired"
            elif days <= 30:
                urgency = "critical"
            elif days <= 90:
                urgency = "warning"
            elif days <= 180:
                urgency = "info"
            else:
                continue  # Not alerting for > 6 months out

            alerts.append(ExpirationAlert(
                document_id=doc.id,
                document_type=doc.document_type,
                filename=doc.filename,
                expiration_date=doc.expiration_date,
                days_remaining=days,
                urgency=urgency,
            ))

        # Sort by urgency (expired first, then by days remaining)
        urgency_order = {"expired": 0, "critical": 1, "warning": 2, "info": 3}
        alerts.sort(key=lambda a: (urgency_order.get(a.urgency, 4), a.days_remaining))
        return alerts

    # --- Receipt Tracker ---

    def add_receipt(self, tracker: ReceiptTracker) -> ReceiptTracker:
        tracker_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        saved = tracker.model_copy(update={
            "id": tracker_id,
            "last_checked": now,
            "case_status": "Case Was Received",
            "status_history": [{"status": "Case Was Received", "date": now}],
        })
        self._receipts[tracker_id] = saved
        return saved

    def get_receipt(self, tracker_id: str) -> ReceiptTracker | None:
        return self._receipts.get(tracker_id)

    def list_receipts(self, user_id: str) -> list[ReceiptTracker]:
        return [r for r in self._receipts.values() if r.user_id == user_id]

    def delete_receipt(self, tracker_id: str) -> bool:
        return self._receipts.pop(tracker_id, None) is not None

    def check_receipt_status(self, tracker_id: str) -> ReceiptTracker | None:
        """Simulate checking USCIS case status. In production, this calls the USCIS API."""
        tracker = self._receipts.get(tracker_id)
        if tracker is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        updated = tracker.model_copy(update={"last_checked": now})
        self._receipts[tracker_id] = updated
        return updated

    @staticmethod
    def validate_receipt_number(receipt_number: str) -> bool:
        """Validate USCIS receipt number format (e.g., EAC2190012345, IOE0912345678)."""
        # Common formats: 3 letters + 10 digits, or IOE + 10 digits
        pattern = r'^[A-Z]{3}\d{10}$'
        return bool(re.match(pattern, receipt_number.replace("-", "").replace(" ", "").upper()))


class TravelAdvisoryService:
    """Assesses whether an applicant can safely travel given their pending cases."""

    # Cases where travel is risky or blocked
    _TRAVEL_RISK_FORMS = {
        "I-485": {
            "risk": "risky",
            "warning": "Traveling while I-485 (Adjustment of Status) is pending may result in abandonment of your application unless you have an approved Advance Parole (I-131).",
            "recommendation": "Apply for Advance Parole (I-131) before any international travel.",
        },
        "I-589": {
            "risk": "blocked",
            "warning": "Traveling to your home country while an asylum case is pending can result in denial. Travel to third countries requires Advance Parole.",
            "recommendation": "Do NOT travel to your home country. Consult your attorney before any travel.",
        },
        "I-751": {
            "risk": "caution",
            "warning": "Travel is generally permitted with valid green card, but extended absences may cause issues.",
            "recommendation": "Keep trips under 6 months. Carry your I-751 receipt notice.",
        },
        "N-400": {
            "risk": "caution",
            "warning": "Extended travel during naturalization process may reset your continuous residence requirement.",
            "recommendation": "Avoid trips longer than 6 months. Trips over 30 days may be questioned.",
        },
        "I-765": {
            "risk": "safe",
            "warning": "EAD application does not restrict travel, but ensure you have valid travel documents.",
            "recommendation": "Carry your current valid visa or Advance Parole if applicable.",
        },
    }

    def assess_travel(
        self,
        pending_forms: list[str],
        destination_country: str,
        has_advance_parole: bool = False,
    ) -> TravelAdvisory:
        """Assess travel risk based on pending cases."""
        warnings: list[str] = []
        recommendations: list[str] = []
        case_impacts: list[str] = []
        worst_risk = "safe"
        risk_order = {"safe": 0, "caution": 1, "risky": 2, "blocked": 3}

        for form in pending_forms:
            form_upper = form.upper().strip()
            risk_info = self._TRAVEL_RISK_FORMS.get(form_upper)
            if risk_info:
                risk = risk_info["risk"]
                # Advance parole can downgrade "risky" to "caution" for I-485
                if form_upper == "I-485" and has_advance_parole:
                    risk = "caution"
                    warnings.append(f"{form_upper}: Travel permitted with approved Advance Parole. Carry I-131 approval notice.")
                else:
                    warnings.append(f"{form_upper}: {risk_info['warning']}")

                recommendations.append(risk_info["recommendation"])
                case_impacts.append(f"{form_upper} ({risk})")

                if risk_order.get(risk, 0) > risk_order.get(worst_risk, 0):
                    worst_risk = risk

        if not pending_forms:
            warnings.append("No pending cases found. Ensure your travel documents are valid.")
            worst_risk = "safe"

        recommendations.append("Always carry copies of all immigration documents when traveling.")
        can_travel = worst_risk in ("safe", "caution")

        return TravelAdvisory(
            can_travel=can_travel,
            risk_level=worst_risk,
            warnings=warnings,
            recommendations=recommendations,
            pending_cases_impact=case_impacts,
        )
