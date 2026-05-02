"""Government E-Filing Proxy — submit forms directly from Verom.

Wraps direct e-filing to USCIS, DOL FLAG, DOS CEAC, and EOIR ECAS into a
single submission interface. Goes beyond status checking — actually FILES
from the platform.

Each filing portal has different requirements:
  - USCIS: PDF upload, electronic signature, fee payment
  - DOL FLAG: PERM / LCA submission with employer info + position details
  - DOS CEAC: DS-160/DS-260 push, consular interview scheduling
  - EOIR ECAS: PDF auto-formatted to 300 DPI, court-specific filing rules

The service exposes a unified `submit_filing()` API. Behind the scenes,
each portal has its own submitter implementation; new portals are added
by registering a submitter.

Submission states track the full lifecycle:
  - draft               not yet submitted
  - validating          pre-submission validation
  - submitting          API call in progress
  - submitted           portal accepted, awaiting processing
  - acknowledged        portal returned receipt / case number
  - failed              submission failed (retry or fix)
  - rejected            portal rejected the filing (must re-file)

Auto-receipt capture: when a portal returns a receipt number,
automatically link it back to the case workspace.

Production: each PortalSubmitter calls the portal's real API. This
implementation provides deterministic mock submitters for dev/test
that simulate the full lifecycle including failure modes."""

from __future__ import annotations

import random
import re
import uuid
from datetime import datetime
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Portal registry
# ---------------------------------------------------------------------------

PORTALS: dict[str, dict[str, Any]] = {
    "uscis": {
        "name": "USCIS Online",
        "url": "https://my.uscis.gov",
        "supported_forms": [
            "I-129", "I-130", "I-485", "I-765", "I-131", "I-140", "I-360",
            "I-539", "I-589", "I-601", "I-751", "N-400", "N-600", "G-28",
        ],
        "required_attachments": True,
        "fee_payment": "in_portal",
        "receipt_format": r"^[A-Z]{3}\d{10}$",
        "receipt_pattern_help": "3 letters + 10 digits (e.g. WAC2612345678)",
    },
    "dol_flag": {
        "name": "DOL FLAG (PERM / LCA)",
        "url": "https://flag.dol.gov",
        "supported_forms": ["ETA-9089", "ETA-9035"],
        "required_attachments": True,
        "fee_payment": "none",
        "receipt_format": r"^[A-Z]-\d{3}-\d{5}-\d{6}$",
        "receipt_pattern_help": "Letter + numeric blocks (e.g. I-200-12345-678901)",
    },
    "dos_ceac": {
        "name": "DOS CEAC (DS-160 / DS-260)",
        "url": "https://ceac.state.gov",
        "supported_forms": ["DS-160", "DS-260", "DS-117", "DS-2019"],
        "required_attachments": False,
        "fee_payment": "external",
        "receipt_format": r"^AA\d{8}$",
        "receipt_pattern_help": "AA + 8 digits (e.g. AA00123456)",
    },
    "eoir_ecas": {
        "name": "EOIR ECAS (Immigration Court)",
        "url": "https://ecas.eoir.justice.gov",
        "supported_forms": ["EOIR-26", "EOIR-29", "EOIR-33", "EOIR-42A", "EOIR-42B", "EOIR-28"],
        "required_attachments": True,
        "fee_payment": "external",
        "receipt_format": r"^\d{9}$",
        "receipt_pattern_help": "9-digit case number",
    },
}


SUBMISSION_STATES = (
    "draft", "validating", "submitting", "submitted",
    "acknowledged", "failed", "rejected",
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EFilingProxyService:
    """Submit filings directly to government portals from the platform."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        form_population: Any | None = None,
        submitter_factory: Callable[[str], Callable] | None = None,
    ) -> None:
        self._cases = case_workspace
        self._forms = form_population
        self._submissions: dict[str, dict] = {}
        self._submitters: dict[str, Callable] = {}
        # Default submitters use deterministic mocks
        if submitter_factory:
            for portal in PORTALS:
                self._submitters[portal] = submitter_factory(portal)
        else:
            for portal in PORTALS:
                self._submitters[portal] = self._default_submitter(portal)

    # ---------- introspection ----------
    @staticmethod
    def list_portals() -> list[dict]:
        return [
            {"id": k, "name": v["name"], "url": v["url"], "supported_forms": v["supported_forms"]}
            for k, v in PORTALS.items()
        ]

    @staticmethod
    def get_portal(portal_id: str) -> dict | None:
        return PORTALS.get(portal_id)

    @staticmethod
    def find_portal_for_form(form_id: str) -> str | None:
        for portal_id, spec in PORTALS.items():
            if form_id in spec["supported_forms"]:
                return portal_id
        return None

    # ---------- submission lifecycle ----------
    def create_submission(
        self,
        portal: str,
        form_id: str,
        workspace_id: str | None = None,
        form_record_id: str | None = None,
        attachments: list[dict] | None = None,
        attorney_id: str | None = None,
        signed: bool = False,
    ) -> dict:
        if portal not in PORTALS:
            raise ValueError(f"Unknown portal: {portal}")
        spec = PORTALS[portal]
        if form_id not in spec["supported_forms"]:
            raise ValueError(f"Form {form_id} not supported by {portal}")

        record = {
            "id": str(uuid.uuid4()),
            "portal": portal,
            "form_id": form_id,
            "workspace_id": workspace_id,
            "form_record_id": form_record_id,
            "attachments": attachments or [],
            "attorney_id": attorney_id,
            "signed": signed,
            "state": "draft",
            "events": [{"state": "draft", "at": datetime.utcnow().isoformat(), "message": "Submission created"}],
            "receipt_number": None,
            "submitted_at": None,
            "acknowledged_at": None,
            "validation_issues": [],
            "portal_response": None,
        }
        self._submissions[record["id"]] = record
        return record

    def validate_submission(self, submission_id: str) -> dict:
        record = self._submissions.get(submission_id)
        if record is None:
            raise ValueError(f"Submission not found: {submission_id}")
        spec = PORTALS[record["portal"]]
        issues = []
        if not record["signed"]:
            issues.append({"code": "UNSIGNED", "severity": "blocking",
                           "message": "Form must be electronically signed before submission."})
        if spec["required_attachments"] and not record["attachments"]:
            issues.append({"code": "MISSING_ATTACHMENTS", "severity": "blocking",
                           "message": "Portal requires supporting documents to be attached."})
        # Pull form completeness if available
        if record["form_record_id"] and self._forms:
            form_rec = self._forms.get_record(record["form_record_id"])
            if form_rec and form_rec.get("completeness_pct", 100) < 100:
                issues.append({
                    "code": "FORM_INCOMPLETE",
                    "severity": "blocking",
                    "message": f"Form is only {form_rec['completeness_pct']}% complete. All required fields must be filled.",
                })
        record["validation_issues"] = issues
        record["state"] = "validating"
        record["events"].append({
            "state": "validating", "at": datetime.utcnow().isoformat(),
            "message": f"Pre-submission validation: {len(issues)} issues",
        })
        return record

    def submit(self, submission_id: str) -> dict:
        record = self._submissions.get(submission_id)
        if record is None:
            raise ValueError(f"Submission not found: {submission_id}")
        # Validate first if not already
        if record["state"] == "draft":
            self.validate_submission(submission_id)
        if any(i["severity"] == "blocking" for i in record["validation_issues"]):
            raise ValueError("Submission has blocking validation issues; resolve before submitting.")
        # Call portal submitter
        record["state"] = "submitting"
        record["events"].append({"state": "submitting", "at": datetime.utcnow().isoformat(),
                                 "message": f"Calling {record['portal']} portal"})
        try:
            portal_response = self._submitters[record["portal"]](record)
            record["portal_response"] = portal_response
            record["receipt_number"] = portal_response.get("receipt_number")
            record["submitted_at"] = datetime.utcnow().isoformat()
            if portal_response.get("status") == "rejected":
                record["state"] = "rejected"
                record["events"].append({
                    "state": "rejected", "at": datetime.utcnow().isoformat(),
                    "message": portal_response.get("reason", "Rejected by portal"),
                })
            else:
                record["state"] = "submitted"
                record["events"].append({
                    "state": "submitted", "at": record["submitted_at"],
                    "message": f"Receipt: {record['receipt_number']}",
                })
                # Auto-link to workspace
                if record["receipt_number"] and self._cases and record["workspace_id"]:
                    try:
                        self._cases.record_filing(
                            record["workspace_id"],
                            record["receipt_number"],
                            datetime.utcnow().date().isoformat(),
                        )
                    except Exception:
                        pass
        except Exception as e:
            record["state"] = "failed"
            record["events"].append({
                "state": "failed", "at": datetime.utcnow().isoformat(),
                "message": f"Submission failed: {e}",
            })
            raise
        return record

    def acknowledge(self, submission_id: str, portal_acknowledgment: dict) -> dict:
        """Called when the portal returns an acknowledgment (receipt notice)
        after initial submission. Some portals are async — submission goes
        through, then the receipt comes back later via webhook or polling."""
        record = self._submissions.get(submission_id)
        if record is None:
            raise ValueError(f"Submission not found: {submission_id}")
        record["state"] = "acknowledged"
        record["acknowledged_at"] = datetime.utcnow().isoformat()
        if "receipt_number" in portal_acknowledgment:
            record["receipt_number"] = portal_acknowledgment["receipt_number"]
        record["events"].append({
            "state": "acknowledged", "at": record["acknowledged_at"],
            "message": "Portal acknowledgment received",
        })
        return record

    def get_submission(self, submission_id: str) -> dict | None:
        return self._submissions.get(submission_id)

    def list_submissions(
        self,
        portal: str | None = None,
        workspace_id: str | None = None,
        attorney_id: str | None = None,
        state: str | None = None,
    ) -> list[dict]:
        out = list(self._submissions.values())
        if portal:
            out = [s for s in out if s["portal"] == portal]
        if workspace_id:
            out = [s for s in out if s["workspace_id"] == workspace_id]
        if attorney_id:
            out = [s for s in out if s["attorney_id"] == attorney_id]
        if state:
            out = [s for s in out if s["state"] == state]
        return out

    # ---------- mock submitters ----------
    @staticmethod
    def _default_submitter(portal: str) -> Callable:
        def submit_fn(record: dict) -> dict:
            spec = PORTALS[portal]
            # Generate a receipt matching the portal's pattern
            receipt = EFilingProxyService._generate_receipt(spec["receipt_format"])
            # Simulate a 5% rejection rate for realism in tests
            if record.get("simulate_rejection"):
                return {"status": "rejected", "reason": "Test rejection requested"}
            return {
                "status": "accepted",
                "receipt_number": receipt,
                "portal": portal,
                "submitted_at": datetime.utcnow().isoformat(),
            }
        return submit_fn

    @staticmethod
    def _generate_receipt(pattern: str) -> str:
        """Generate a receipt number matching the portal's regex pattern."""
        if pattern == r"^[A-Z]{3}\d{10}$":
            return f"WAC{random.randint(2000000000, 9999999999):010d}"
        if pattern == r"^[A-Z]-\d{3}-\d{5}-\d{6}$":
            return f"I-{random.randint(100, 999)}-{random.randint(10000, 99999)}-{random.randint(100000, 999999)}"
        if pattern == r"^AA\d{8}$":
            return f"AA{random.randint(10000000, 99999999):08d}"
        if pattern == r"^\d{9}$":
            return f"{random.randint(100000000, 999999999):09d}"
        return f"REF-{uuid.uuid4().hex[:10].upper()}"

    @staticmethod
    def validate_receipt_format(portal: str, receipt: str) -> bool:
        spec = PORTALS.get(portal)
        if not spec:
            return False
        return bool(re.match(spec["receipt_format"], receipt))
