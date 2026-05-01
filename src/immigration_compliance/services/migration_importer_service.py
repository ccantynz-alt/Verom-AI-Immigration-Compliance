"""White-Glove Migration Importer — bulk import from competitor platforms.

The single biggest barrier to switching practice management systems is
data lift. This service ingests CSV exports from Docketwise, INSZoom,
LollyLaw, Clio Manage, and eImmigration, auto-maps each platform's
column structure to Verom's intake schema, and creates ready-to-go
case workspaces — typically without manual mapping.

Mechanics:
  1. PROFILE     — detect the source platform from CSV header signature
  2. MAP         — apply the source-specific column mapping to translate
                   each row into Verom's canonical case shape
  3. VALIDATE    — flag rows missing required fields or with bad data
  4. IMPORT      — for each valid row, create an intake session, populate
                   answers, create a CaseWorkspace, and queue forms
  5. REPORT      — return summary: imported / skipped / warnings, with
                   line-by-line traceability for the firm to review

Profiles are data-driven: adding a new competitor is one entry in
COMPETITOR_PROFILES with column-mapping rules and any value transforms.

Idempotency: every imported row carries the source platform + source row
ID so re-running an import doesn't duplicate cases (we de-dup on hash)."""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import datetime
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Competitor profiles
# ---------------------------------------------------------------------------

# Each profile defines:
#   header_signature: list of column names that must all appear (used for
#                     auto-detection of the source platform)
#   field_map: mapping from platform column → canonical field
#              {"applicant_first_name": "FirstName"} reads CSV column
#              "FirstName" and writes to canonical field
#              "applicant_first_name"
#   value_transforms: per-canonical-field transform spec (optional)
#                     {"visa_type": {"H1B": "H-1B", "H1-B": "H-1B"}}
#   country_default, status_default for fields not present

COMPETITOR_PROFILES: dict[str, dict[str, Any]] = {
    "docketwise": {
        "name": "Docketwise",
        "header_signature": ["client_first_name", "client_last_name", "case_type", "matter_status"],
        "field_map": {
            "applicant_first_name": "client_first_name",
            "applicant_last_name": "client_last_name",
            "applicant_dob": "client_dob",
            "applicant_email": "client_email",
            "applicant_phone": "client_phone",
            "country_of_birth": "client_country_of_birth",
            "passport_number": "client_passport_number",
            "visa_type": "case_type",
            "case_status": "matter_status",
            "filing_receipt_number": "uscis_receipt_number",
            "petitioner_name": "petitioner_name",
            "attorney_name": "responsible_attorney",
            "source_row_id": "matter_id",
        },
        "value_transforms": {
            "visa_type": {
                "H1B": "H-1B", "H1-B": "H-1B", "H 1 B": "H-1B",
                "L1A": "L-1", "L1B": "L-1", "L1": "L-1",
                "O1": "O-1", "O 1 A": "O-1",
                "I130": "I-130", "I 130": "I-130",
                "I485": "I-485", "I-485 AOS": "I-485",
                "F1": "F-1", "F 1": "F-1",
            },
            "case_status": {
                "Open": "intake", "In Progress": "documents",
                "Filed": "filed", "Approved": "approved",
                "Denied": "denied", "Closed": "withdrawn",
                "Receipt": "filed", "RFE": "rfe",
            },
        },
        "country_default": "US",
    },
    "inszoom": {
        "name": "INSZoom / Mitratech",
        "header_signature": ["beneficiary_first_name", "beneficiary_last_name", "petition_type", "case_id"],
        "field_map": {
            "applicant_first_name": "beneficiary_first_name",
            "applicant_last_name": "beneficiary_last_name",
            "applicant_dob": "beneficiary_dob",
            "applicant_email": "beneficiary_email",
            "passport_number": "beneficiary_passport",
            "country_of_birth": "beneficiary_country",
            "visa_type": "petition_type",
            "case_status": "case_status",
            "filing_receipt_number": "receipt_number",
            "petitioner_name": "petitioner_company",
            "attorney_name": "lead_attorney",
            "source_row_id": "case_id",
        },
        "value_transforms": {
            "visa_type": {
                "H-1B Initial": "H-1B", "H-1B Extension": "H-1B",
                "L-1A": "L-1", "L-1B": "L-1",
                "O-1A": "O-1", "O-1B": "O-1",
                "EB-2 NIW": "I-140", "EB-1A": "I-140",
                "I-130 Spouse": "I-130", "I-130 Parent": "I-130",
            },
            "case_status": {
                "Open": "intake", "Pending": "documents",
                "Filed-Pending": "filed", "Approved": "approved",
                "Denied": "denied", "Withdrawn": "withdrawn",
                "RFE Issued": "rfe",
            },
        },
        "country_default": "US",
    },
    "lollylaw": {
        "name": "LollyLaw",
        "header_signature": ["first_name", "last_name", "matter_type", "matter_id"],
        "field_map": {
            "applicant_first_name": "first_name",
            "applicant_last_name": "last_name",
            "applicant_dob": "dob",
            "applicant_email": "email",
            "applicant_phone": "phone",
            "country_of_birth": "country",
            "visa_type": "matter_type",
            "case_status": "status",
            "filing_receipt_number": "receipt",
            "attorney_name": "attorney",
            "source_row_id": "matter_id",
        },
        "value_transforms": {
            "visa_type": {
                "H1B Cap": "H-1B", "H1B Extension": "H-1B",
                "I130 Marriage": "I-130", "I130 Parent": "I-130",
                "I485 AOS": "I-485",
            },
            "case_status": {
                "Active": "documents", "Pending Filing": "review",
                "Filed": "filed", "Approved": "approved",
                "Denied": "denied", "Closed": "withdrawn",
            },
        },
        "country_default": "US",
    },
    "clio": {
        "name": "Clio Manage",
        "header_signature": ["matter_number", "client_first_name", "client_last_name", "practice_area"],
        "field_map": {
            "applicant_first_name": "client_first_name",
            "applicant_last_name": "client_last_name",
            "applicant_email": "client_email",
            "applicant_phone": "client_phone",
            "visa_type": "matter_description",
            "case_status": "matter_status",
            "attorney_name": "responsible_attorney",
            "source_row_id": "matter_number",
        },
        "value_transforms": {
            "case_status": {
                "Open": "intake",
                "Pending": "documents",
                "Closed": "withdrawn",
            },
        },
        "country_default": "US",
    },
    "eimmigration": {
        "name": "eImmigration / Cerenade",
        "header_signature": ["client_id", "case_number", "visa_category", "status"],
        "field_map": {
            "applicant_first_name": "first_name",
            "applicant_last_name": "last_name",
            "applicant_dob": "date_of_birth",
            "applicant_email": "email_address",
            "passport_number": "passport_no",
            "country_of_birth": "country_of_birth",
            "visa_type": "visa_category",
            "case_status": "status",
            "filing_receipt_number": "receipt_no",
            "petitioner_name": "petitioner",
            "attorney_name": "atty",
            "source_row_id": "case_number",
        },
        "value_transforms": {
            "case_status": {
                "Open": "intake", "Active": "documents",
                "Filed": "filed", "Approved": "approved",
                "Denied": "denied", "Closed": "withdrawn",
            },
        },
        "country_default": "US",
    },
}


REQUIRED_CANONICAL_FIELDS = ("applicant_first_name", "applicant_last_name", "visa_type")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MigrationImporterService:
    """Bulk-import case data from competitor platforms."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._imports: dict[str, dict] = {}
        self._row_hashes: set[str] = set()  # for de-dup across re-runs

    # ---------- profile detection ----------
    @staticmethod
    def detect_profile(headers: Iterable[str]) -> str | None:
        header_set = {h.strip().lower() for h in headers}
        best_match: tuple[str | None, int] = (None, 0)
        for key, profile in COMPETITOR_PROFILES.items():
            sig = {s.lower() for s in profile["header_signature"]}
            overlap = len(header_set & sig)
            if overlap == len(sig) and overlap > best_match[1]:
                best_match = (key, overlap)
        return best_match[0]

    @staticmethod
    def list_profiles() -> list[dict]:
        return [
            {
                "id": k,
                "name": p["name"],
                "header_signature": p["header_signature"],
                "supports_value_transforms": "value_transforms" in p,
                "field_map_size": len(p["field_map"]),
            }
            for k, p in COMPETITOR_PROFILES.items()
        ]

    @staticmethod
    def get_profile(profile_id: str) -> dict | None:
        return COMPETITOR_PROFILES.get(profile_id)

    # ---------- mapping ----------
    def map_row(self, profile_id: str, row: dict) -> dict:
        profile = COMPETITOR_PROFILES.get(profile_id)
        if profile is None:
            raise ValueError(f"Unknown profile: {profile_id}")
        canonical: dict[str, Any] = {}
        for canonical_field, source_col in profile["field_map"].items():
            raw = row.get(source_col)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                continue
            value = raw.strip() if isinstance(raw, str) else raw
            transforms = profile.get("value_transforms", {}).get(canonical_field, {})
            if isinstance(value, str) and value in transforms:
                value = transforms[value]
            canonical[canonical_field] = value
        canonical.setdefault("country", profile.get("country_default", "US"))
        canonical["_source_platform"] = profile_id
        return canonical

    def validate_row(self, canonical: dict) -> list[str]:
        issues = []
        for f in REQUIRED_CANONICAL_FIELDS:
            if not canonical.get(f):
                issues.append(f"missing_{f}")
        return issues

    # ---------- dry-run preview ----------
    def preview(self, csv_text: str, profile_id: str | None = None) -> dict:
        """Parse + map + validate without creating any workspaces."""
        reader = csv.DictReader(io.StringIO(csv_text))
        headers = reader.fieldnames or []
        detected = profile_id or self.detect_profile(headers)
        if detected is None:
            return {
                "profile_id": None,
                "headers": headers,
                "rows": [],
                "summary": {
                    "total": 0,
                    "valid": 0,
                    "invalid": 0,
                    "duplicates": 0,
                    "detected_profile": None,
                },
                "error": "No matching competitor profile detected. Try specifying profile_id manually.",
            }
        profile = COMPETITOR_PROFILES[detected]
        rows_out = []
        valid = 0
        invalid = 0
        duplicates = 0
        for i, row in enumerate(reader, start=1):
            mapped = self.map_row(detected, row)
            issues = self.validate_row(mapped)
            row_hash = self._row_hash(detected, mapped)
            is_dup = row_hash in self._row_hashes
            rows_out.append({
                "row_number": i,
                "source": row,
                "mapped": mapped,
                "issues": issues,
                "duplicate": is_dup,
                "row_hash": row_hash,
            })
            if is_dup:
                duplicates += 1
            elif issues:
                invalid += 1
            else:
                valid += 1
        return {
            "profile_id": detected,
            "profile_name": profile["name"],
            "headers": headers,
            "rows": rows_out,
            "summary": {
                "total": len(rows_out),
                "valid": valid,
                "invalid": invalid,
                "duplicates": duplicates,
                "detected_profile": detected,
            },
            "previewed_at": datetime.utcnow().isoformat(),
        }

    # ---------- import ----------
    def run_import(
        self,
        applicant_owner_id: str,
        csv_text: str,
        profile_id: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Run the full import. If dry_run=True, just preview without
        creating workspaces or writing state."""
        preview = self.preview(csv_text, profile_id=profile_id)
        if preview.get("error"):
            return {**preview, "imported_count": 0, "import_id": None}
        if dry_run:
            return {**preview, "imported_count": 0, "dry_run": True}

        import_id = str(uuid.uuid4())
        imported_workspaces = []
        skipped = []

        for r in preview["rows"]:
            if r["issues"] or r["duplicate"]:
                skipped.append({
                    "row_number": r["row_number"],
                    "reason": "duplicate" if r["duplicate"] else "validation: " + ", ".join(r["issues"]),
                    "source": r["source"],
                })
                continue
            ws = self._create_workspace_from_row(applicant_owner_id, r["mapped"], preview["profile_id"])
            if ws:
                imported_workspaces.append(ws)
                self._row_hashes.add(r["row_hash"])

        record = {
            "id": import_id,
            "applicant_owner_id": applicant_owner_id,
            "profile_id": preview["profile_id"],
            "profile_name": preview.get("profile_name"),
            "imported_count": len(imported_workspaces),
            "skipped_count": len(skipped),
            "summary": preview["summary"],
            "imported_workspaces": [w["id"] for w in imported_workspaces],
            "skipped": skipped,
            "completed_at": datetime.utcnow().isoformat(),
        }
        self._imports[import_id] = record
        return record

    def _create_workspace_from_row(self, owner_id: str, mapped: dict, profile_id: str) -> dict | None:
        if not self._cases:
            return None
        visa_type = mapped.get("visa_type")
        if not visa_type:
            return None

        # Optionally start an intake session pre-populated with what we know
        intake_session_id = None
        if self._intake:
            try:
                if self._intake.get_visa_config(visa_type):
                    sess = self._intake.start_session(owner_id, visa_type)
                    seed_answers = {k: v for k, v in mapped.items() if not k.startswith("_")}
                    self._intake.submit_answers(sess["id"], seed_answers)
                    intake_session_id = sess["id"]
            except Exception:
                intake_session_id = None

        label = self._compose_label(mapped)
        ws = self._cases.create_workspace(
            applicant_id=owner_id,
            visa_type=visa_type,
            country=mapped.get("country", "US"),
            intake_session_id=intake_session_id,
            case_label=label,
        )
        ws["imported_from"] = profile_id
        ws["source_row_id"] = mapped.get("source_row_id")
        # Status mapping
        new_status = mapped.get("case_status")
        if new_status:
            try:
                self._cases.update_status(ws["id"], new_status, f"Imported from {profile_id}")
            except Exception:
                pass
        # If a receipt number is present, record the filing
        if mapped.get("filing_receipt_number"):
            try:
                self._cases.record_filing(ws["id"], mapped["filing_receipt_number"])
            except Exception:
                pass
        return ws

    @staticmethod
    def _compose_label(mapped: dict) -> str:
        first = mapped.get("applicant_first_name", "")
        last = mapped.get("applicant_last_name", "")
        visa = mapped.get("visa_type", "Case")
        full = f"{first} {last}".strip() or "Imported case"
        return f"{full} — {visa}"

    @staticmethod
    def _row_hash(profile_id: str, mapped: dict) -> str:
        # De-dup on profile + source row id + applicant name
        parts = [
            profile_id,
            str(mapped.get("source_row_id", "")),
            str(mapped.get("applicant_first_name", "")).lower(),
            str(mapped.get("applicant_last_name", "")).lower(),
            str(mapped.get("applicant_dob", "")),
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]  # noqa: S324

    # ---------- audit ----------
    def get_import(self, import_id: str) -> dict | None:
        return self._imports.get(import_id)

    def list_imports(self, owner_id: str | None = None) -> list[dict]:
        out = list(self._imports.values())
        if owner_id:
            out = [r for r in out if r["applicant_owner_id"] == owner_id]
        return sorted(out, key=lambda r: r["completed_at"], reverse=True)
