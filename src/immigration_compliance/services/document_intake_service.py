"""Document Intake Pipeline — upload, classify, OCR, validate, conflict-check.

This is the runtime layer that turns a stack of uploaded files into a validated,
case-ready document set. The pipeline is deterministic and inspectable:

  1. UPLOAD       — file metadata captured, hashed, stored
  2. QUALITY      — resolution, format, page count, blur heuristics
  3. CLASSIFY     — AI-guessed document type (passport, I-94, degree, paystub…)
  4. EXTRACT      — OCR / structured data extraction
  5. VALIDATE     — required fields present, dates valid, expiry not lapsed
  6. RECONCILE    — cross-check extracted data against intake answers
  7. CHECKLIST    — map document to the relevant intake checklist item

OCR/classification here are heuristic stand-ins (filename + extension + mime
hints + the 'document_type' the user supplied). When wiring real OCR (Textract,
Google DocAI, Azure Form Recognizer), the call sites for `_classify` and
`_extract` are the only places that change."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Document type hints — used to map user uploads to checklist doc_ids
# ---------------------------------------------------------------------------

# Each known doc_type maps to: friendly label, expected fields after OCR,
# and the intake checklist doc_ids it can satisfy.
DOCUMENT_TYPES: dict[str, dict[str, Any]] = {
    "passport": {
        "label": "Passport",
        "fields": ["full_name", "passport_number", "nationality", "dob", "expiry"],
        "satisfies": ["valid_passport"],
        "requires_unexpired": True,
        "min_validity_months": 6,
    },
    "i94": {
        "label": "I-94 Arrival/Departure",
        "fields": ["admission_number", "class_of_admission", "admitted_until"],
        "satisfies": ["i94_record"],
        "requires_unexpired": False,
    },
    "i20": {
        "label": "Form I-20",
        "fields": ["sevis_id", "school_name", "program_start", "program_end", "funding_source"],
        "satisfies": ["i20"],
        "requires_unexpired": True,
    },
    "approval_notice": {
        "label": "USCIS Approval Notice (I-797)",
        "fields": ["receipt_number", "form_type", "valid_from", "valid_to", "petitioner", "beneficiary"],
        "satisfies": ["approved_i130_or_i140"],
        "requires_unexpired": False,
    },
    "lca": {
        "label": "Certified LCA",
        "fields": ["lca_number", "wage_level", "wage_rate", "worksite", "employer", "soc_code"],
        "satisfies": ["lca_certified"],
        "requires_unexpired": False,
    },
    "degree": {
        "label": "Degree / Diploma",
        "fields": ["institution", "degree", "field_of_study", "date_conferred"],
        "satisfies": [
            "bachelors_degree_or_equivalent",
            "academic_qualifications",
            "academic_transcripts",
        ],
        "requires_unexpired": False,
    },
    "transcript": {
        "label": "Academic Transcript",
        "fields": ["institution", "gpa", "courses", "date_issued"],
        "satisfies": ["academic_transcripts"],
        "requires_unexpired": False,
    },
    "english_test": {
        "label": "English Proficiency Test",
        "fields": ["test_name", "score", "test_date"],
        "satisfies": ["english_proficiency_certificate", "english_proficiency_test", "language_test_results"],
        "requires_unexpired": True,
        "min_validity_months": 0,
    },
    "bank_statement": {
        "label": "Bank Statement",
        "fields": ["account_holder", "balance", "currency", "statement_period"],
        "satisfies": [
            "financial_evidence",
            "financial_evidence_28_days",
            "proof_of_funds_gic",
            "proof_of_funds_if_FSW",
            "evidence_of_funds_NZD20K",
            "blocked_account_evidence",
            "financial_capacity_evidence",
        ],
        "requires_unexpired": False,
    },
    "paystub": {
        "label": "Pay Stub",
        "fields": ["employee_name", "employer", "pay_period", "gross_pay", "ytd"],
        "satisfies": ["salary_evidence"],
        "requires_unexpired": False,
    },
    "tax_return": {
        "label": "Tax Return",
        "fields": ["filer_name", "tax_year", "agi", "filing_status"],
        "satisfies": ["tax_returns_3_years"],
        "requires_unexpired": False,
    },
    "marriage_certificate": {
        "label": "Marriage Certificate",
        "fields": ["spouse_1", "spouse_2", "date_of_marriage", "place_of_marriage"],
        "satisfies": ["marriage_certificate_if_applicable"],
        "requires_unexpired": False,
    },
    "birth_certificate": {
        "label": "Birth Certificate",
        "fields": ["full_name", "dob", "place_of_birth", "parent_names"],
        "satisfies": ["birth_certificate", "birth_certificates"],
        "requires_unexpired": False,
    },
    "police_certificate": {
        "label": "Police Clearance Certificate",
        "fields": ["full_name", "country", "date_issued"],
        "satisfies": ["police_certificate_if_required", "police_certificates_all_countries", "police_certificates"],
        "requires_unexpired": True,
        "min_validity_months": 6,
    },
    "medical_exam": {
        "label": "Medical Exam Report",
        "fields": ["patient_name", "exam_date", "physician_name", "vaccinations"],
        "satisfies": ["i693_medical_exam", "medical_exam", "medical_exam_if_required", "health_examination", "tb_test_if_required"],
        "requires_unexpired": True,
        "min_validity_months": 1,
    },
    "employment_letter": {
        "label": "Employment / Offer Letter",
        "fields": ["employee_name", "employer", "position", "salary", "start_date"],
        "satisfies": [
            "employment_offer_letter",
            "employment_offer_or_itinerary",
            "skilled_employment_offer",
            "employment_contract",
            "work_experience_letters",
            "experience_letters",
        ],
        "requires_unexpired": False,
    },
    "support_letter": {
        "label": "Support / Expert Letter",
        "fields": ["letter_from", "letter_about", "date_signed"],
        "satisfies": [
            "expert_letters",
            "advisory_opinion_or_peer_consultation",
            "employer_supporting_documents",
            "specialty_occupation_evidence",
        ],
        "requires_unexpired": False,
    },
    "photo": {
        "label": "Passport-style Photo",
        "fields": [],
        "satisfies": ["photo_ds_compliant", "passport_photos", "biometric_photos"],
        "requires_unexpired": False,
    },
    "ds160_confirmation": {
        "label": "DS-160 Confirmation",
        "fields": ["confirmation_number", "applicant_name"],
        "satisfies": ["ds160_confirmation"],
        "requires_unexpired": False,
    },
    "sevis_receipt": {
        "label": "SEVIS Fee Receipt",
        "fields": ["sevis_id", "amount_paid", "payment_date"],
        "satisfies": ["sevis_fee_receipt"],
        "requires_unexpired": False,
    },
    "cas_letter": {
        "label": "CAS Letter (UK)",
        "fields": ["cas_number", "sponsor_license", "course", "tuition"],
        "satisfies": ["cas_letter"],
        "requires_unexpired": True,
    },
    "cos_letter": {
        "label": "Certificate of Sponsorship (UK)",
        "fields": ["cos_number", "sponsor", "occupation_code", "salary"],
        "satisfies": ["certificate_of_sponsorship"],
        "requires_unexpired": True,
    },
    "loa_dli": {
        "label": "Letter of Acceptance (Canada)",
        "fields": ["dli_number", "institution", "program", "start_date"],
        "satisfies": ["letter_of_acceptance_dli"],
        "requires_unexpired": False,
    },
    "coe": {
        "label": "Confirmation of Enrolment (Australia)",
        "fields": ["coe_number", "provider", "course", "start_date", "end_date"],
        "satisfies": ["coe_confirmation_of_enrolment"],
        "requires_unexpired": False,
    },
    "uni_admission": {
        "label": "University Admission Letter",
        "fields": ["institution", "program", "start_date"],
        "satisfies": ["university_admission_letter", "school_admission_letter", "offer_of_place"],
        "requires_unexpired": False,
    },
    "id_card": {
        "label": "Government-issued ID",
        "fields": ["full_name", "id_number", "expiry"],
        "satisfies": ["petitioner_id", "beneficiary_id"],
        "requires_unexpired": True,
    },
    "other": {
        "label": "Other / Uncategorized",
        "fields": [],
        "satisfies": [],
        "requires_unexpired": False,
    },
}


# ---------------------------------------------------------------------------
# Quality heuristics
# ---------------------------------------------------------------------------

ACCEPTABLE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic"}
MIN_FILE_SIZE = 50_000           # 50KB — below this is suspicious for a real doc
MAX_FILE_SIZE = 25_000_000       # 25MB — above this needs splitting/compression
MIN_RESOLUTION_DPI = 200          # 200 DPI for OCR; 300 ideal


# ---------------------------------------------------------------------------
# DocumentIntakeService
# ---------------------------------------------------------------------------

class DocumentIntakeService:
    """Pipeline for uploading + processing applicant documents.

    Storage is in-memory by design: Verom's storage layer (S3-compatible bucket
    encrypted at rest) is plugged in via the `_persist` hook in production. The
    service signature stays the same."""

    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    # ---------- public API ----------
    def upload(
        self,
        applicant_id: str,
        session_id: str | None,
        filename: str,
        size_bytes: int,
        mime_type: str = "",
        declared_type: str | None = None,
        page_count: int = 1,
        resolution_dpi: int | None = None,
        content_hash: str | None = None,
    ) -> dict:
        """Run a fresh upload through the full pipeline. Returns the processed record."""
        doc_id = str(uuid.uuid4())
        record: dict[str, Any] = {
            "id": doc_id,
            "applicant_id": applicant_id,
            "session_id": session_id,
            "filename": filename,
            "size_bytes": size_bytes,
            "mime_type": mime_type or self._guess_mime(filename),
            "page_count": page_count,
            "resolution_dpi": resolution_dpi,
            "content_hash": content_hash or hashlib.sha256(f"{applicant_id}|{filename}|{size_bytes}".encode()).hexdigest(),
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "processing",
            "stages": {},
        }

        # 1) QUALITY
        record["stages"]["quality"] = self._quality_check(record)

        # 2) CLASSIFY
        record["stages"]["classify"] = self._classify(filename, declared_type, mime_type)
        record["document_type"] = record["stages"]["classify"]["document_type"]

        # 3) EXTRACT (mock OCR — returns plausible structured fields)
        record["stages"]["extract"] = self._extract(record["document_type"], filename)
        record["extracted"] = record["stages"]["extract"]["fields"]

        # 4) VALIDATE
        record["stages"]["validate"] = self._validate(record)

        # 5) CHECKLIST MAPPING (filled later via reconcile_against_checklist)
        record["satisfies"] = DOCUMENT_TYPES.get(record["document_type"], {}).get("satisfies", [])

        # Final status
        quality_ok = record["stages"]["quality"]["acceptable"]
        validate_ok = record["stages"]["validate"]["valid"]
        record["status"] = "ready" if (quality_ok and validate_ok) else "needs_attention"

        self._documents[doc_id] = record
        return record

    def get_document(self, doc_id: str) -> dict | None:
        return self._documents.get(doc_id)

    def list_documents(self, applicant_id: str | None = None, session_id: str | None = None) -> list[dict]:
        docs = list(self._documents.values())
        if applicant_id:
            docs = [d for d in docs if d["applicant_id"] == applicant_id]
        if session_id:
            docs = [d for d in docs if d["session_id"] == session_id]
        return docs

    def delete_document(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None

    # ---------- reconciliation against checklist + intake answers ----------
    def reconcile_against_checklist(self, applicant_id: str, session_id: str, checklist: dict, intake_answers: dict | None = None) -> dict:
        """Map uploaded docs to checklist items, compute completeness, surface conflicts."""
        intake_answers = intake_answers or {}
        docs = self.list_documents(applicant_id=applicant_id, session_id=session_id)

        # Index docs by what they satisfy
        satisfied: dict[str, list[dict]] = {}
        for d in docs:
            for doc_id_satisfied in d.get("satisfies", []):
                satisfied.setdefault(doc_id_satisfied, []).append({
                    "uploaded_doc_id": d["id"],
                    "filename": d["filename"],
                    "document_type": d["document_type"],
                    "status": d["status"],
                })

        # Walk the checklist
        items_status = []
        complete_count = 0
        required_count = 0
        for item in checklist.get("items", []):
            cid = item["doc_id"]
            matches = satisfied.get(cid, [])
            is_required = item.get("required", True)
            if is_required:
                required_count += 1
            done = any(m["status"] == "ready" for m in matches)
            if done and is_required:
                complete_count += 1
            items_status.append({
                "checklist_item_id": cid,
                "label": item["label"],
                "category": item["category"],
                "required": is_required,
                "uploaded": matches,
                "status": "complete" if done else ("partial" if matches else "missing"),
            })

        completeness_pct = round((complete_count / required_count) * 100) if required_count else 100

        # Cross-check extracted data vs intake answers
        conflicts = self._detect_data_conflicts(docs, intake_answers)

        return {
            "applicant_id": applicant_id,
            "session_id": session_id,
            "total_required": required_count,
            "total_complete": complete_count,
            "completeness_pct": completeness_pct,
            "ready_to_file": completeness_pct == 100 and not conflicts,
            "items": items_status,
            "data_conflicts": conflicts,
            "reconciled_at": datetime.utcnow().isoformat(),
        }

    # ---------- pipeline stages ----------
    def _quality_check(self, record: dict) -> dict:
        issues = []
        recs = []
        ext = self._ext(record["filename"])
        if ext not in ACCEPTABLE_EXTENSIONS:
            issues.append(f"Unsupported file type: {ext}")
            recs.append("Re-upload as PDF, JPG, or PNG")
        if record["size_bytes"] < MIN_FILE_SIZE:
            issues.append("File is unusually small — likely a thumbnail or partial scan")
            recs.append("Re-scan at higher resolution")
        if record["size_bytes"] > MAX_FILE_SIZE:
            issues.append("File exceeds 25MB — too large for processing")
            recs.append("Split the document or compress before upload")
        if record["resolution_dpi"] is not None and record["resolution_dpi"] < MIN_RESOLUTION_DPI:
            issues.append(f"Resolution {record['resolution_dpi']} DPI is below the {MIN_RESOLUTION_DPI} DPI minimum for OCR")
            recs.append(f"Re-scan at {MIN_RESOLUTION_DPI}+ DPI (300 DPI ideal)")
        score = max(0, 100 - len(issues) * 25)
        return {
            "score": score,
            "format": ext,
            "size_kb": round(record["size_bytes"] / 1024),
            "page_count": record["page_count"],
            "resolution_dpi": record["resolution_dpi"],
            "issues": issues,
            "recommendations": recs or ["File passes quality checks"],
            "acceptable": len(issues) == 0,
        }

    def _classify(self, filename: str, declared_type: str | None, mime_type: str) -> dict:
        """Classify document by (declared) → filename heuristics → mime fallback."""
        if declared_type and declared_type in DOCUMENT_TYPES:
            return {
                "document_type": declared_type,
                "label": DOCUMENT_TYPES[declared_type]["label"],
                "method": "declared",
                "confidence": 0.95,
            }
        guessed = self._guess_from_filename(filename)
        if guessed:
            return {
                "document_type": guessed,
                "label": DOCUMENT_TYPES[guessed]["label"],
                "method": "filename_heuristic",
                "confidence": 0.72,
            }
        return {
            "document_type": "other",
            "label": DOCUMENT_TYPES["other"]["label"],
            "method": "fallback",
            "confidence": 0.4,
        }

    @staticmethod
    def _guess_from_filename(filename: str) -> str | None:
        f = filename.lower().replace("-", "_").replace(" ", "_")
        rules: list[tuple[str, str]] = [
            ("passport", "passport"),
            ("i94", "i94"),
            ("i_94", "i94"),
            ("i20", "i20"),
            ("i_20", "i20"),
            ("i797", "approval_notice"),
            ("approval", "approval_notice"),
            ("lca", "lca"),
            ("transcript", "transcript"),
            ("diploma", "degree"),
            ("degree", "degree"),
            ("ielts", "english_test"),
            ("toefl", "english_test"),
            ("pte", "english_test"),
            ("celpip", "english_test"),
            ("bank", "bank_statement"),
            ("statement", "bank_statement"),
            ("paystub", "paystub"),
            ("paycheck", "paystub"),
            ("salary", "paystub"),
            ("w2", "tax_return"),
            ("1040", "tax_return"),
            ("tax_return", "tax_return"),
            ("marriage", "marriage_certificate"),
            ("birth_cert", "birth_certificate"),
            ("birth_certificate", "birth_certificate"),
            ("police", "police_certificate"),
            ("medical", "medical_exam"),
            ("i693", "medical_exam"),
            ("offer_letter", "employment_letter"),
            ("offer", "employment_letter"),
            ("employment", "employment_letter"),
            ("expert", "support_letter"),
            ("support_letter", "support_letter"),
            ("recommendation", "support_letter"),
            ("photo", "photo"),
            ("headshot", "photo"),
            ("ds160", "ds160_confirmation"),
            ("ds_160", "ds160_confirmation"),
            ("sevis", "sevis_receipt"),
            ("cas", "cas_letter"),
            ("cos", "cos_letter"),
            ("loa", "loa_dli"),
            ("acceptance", "loa_dli"),
            ("coe", "coe"),
            ("admission", "uni_admission"),
            ("license", "id_card"),
            ("driver", "id_card"),
            ("national_id", "id_card"),
        ]
        for needle, doc_type in rules:
            if needle in f:
                return doc_type
        return None

    def _extract(self, document_type: str, filename: str) -> dict:
        """Mock OCR extraction — returns plausible fields. In production this calls
        Textract/DocAI/Form Recognizer. The downstream code is OCR-implementation
        agnostic: it only consumes `fields` and `confidence`."""
        spec = DOCUMENT_TYPES.get(document_type, DOCUMENT_TYPES["other"])
        # Generate stub field values keyed off filename so different uploads look different
        seed = int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)  # noqa: S324
        stubs: dict[str, Any] = {}
        for f in spec["fields"]:
            stubs[f] = self._stub_value(f, seed)
        return {
            "fields": stubs,
            "raw_text_chars": 1500 + (seed % 4000),
            "confidence": 0.88 if document_type != "other" else 0.4,
            "engine": "verom-mock-v1",
        }

    @staticmethod
    def _stub_value(field_name: str, seed: int) -> Any:
        if field_name in ("dob", "date_conferred", "test_date", "exam_date", "date_of_marriage", "date_issued", "payment_date", "valid_from"):
            year = 1990 + (seed % 30)
            return f"{year}-01-15"
        if field_name in ("expiry", "valid_to", "admitted_until", "program_end", "end_date"):
            year = date.today().year + 1 + (seed % 5)
            return f"{year}-12-31"
        if field_name == "passport_number":
            return f"X{seed % 100000000:08d}"
        if field_name == "receipt_number":
            return f"WAC{(seed % 1000000000):010d}"
        if field_name == "admission_number":
            return f"{(seed % 100000000000):011d}"
        if field_name in ("balance", "gross_pay", "ytd", "salary", "tuition", "amount_paid", "agi"):
            return 50000 + (seed % 100000)
        if field_name == "wage_level":
            return ["I", "II", "III", "IV"][seed % 4]
        if field_name == "currency":
            return "USD"
        return f"<extracted:{field_name}>"

    def _validate(self, record: dict) -> dict:
        spec = DOCUMENT_TYPES.get(record["document_type"], {})
        extracted = record.get("extracted", {})
        issues = []
        # Required fields present
        for f in spec.get("fields", []):
            if not extracted.get(f):
                issues.append(f"Missing field: {f}")
        # Expiry checks
        if spec.get("requires_unexpired"):
            expiry_field = "expiry" if "expiry" in extracted else "valid_to" if "valid_to" in extracted else None
            if expiry_field:
                exp = self._parse_date(extracted[expiry_field])
                if exp:
                    today = date.today()
                    if exp < today:
                        issues.append(f"Document expired on {exp.isoformat()}")
                    else:
                        min_months = spec.get("min_validity_months", 0)
                        days_remaining = (exp - today).days
                        if min_months and days_remaining < min_months * 30:
                            issues.append(f"Document expires in {days_remaining} days — minimum {min_months} months required")
        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def _parse_date(s: Any) -> date | None:
        if isinstance(s, date):
            return s
        if not s or not isinstance(s, str):
            return None
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
        if not m:
            return None
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    @staticmethod
    def _detect_data_conflicts(docs: list[dict], intake_answers: dict) -> list[dict]:
        """Surface inconsistencies between extracted document fields and intake answers."""
        conflicts: list[dict] = []
        # Example: passport name vs intake first_name
        for d in docs:
            if d["document_type"] != "passport":
                continue
            extracted = d.get("extracted", {})
            extracted_name = (extracted.get("full_name") or "").lower()
            intake_first = (intake_answers.get("first_name") or "").lower()
            intake_last = (intake_answers.get("last_name") or "").lower()
            if intake_first and intake_first not in extracted_name and not extracted_name.startswith("<"):
                conflicts.append({
                    "code": "NAME_MISMATCH",
                    "severity": "medium",
                    "doc_id": d["id"],
                    "field": "full_name",
                    "extracted_value": extracted.get("full_name"),
                    "intake_value": f"{intake_answers.get('first_name')} {intake_answers.get('last_name')}",
                    "explanation": "Name on passport does not appear to match the name provided in intake.",
                    "recommendation": "Confirm the passport name and intake spelling. USCIS requires exact match.",
                })
        return conflicts

    @staticmethod
    def _ext(filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    @staticmethod
    def _guess_mime(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "tiff": "image/tiff",
            "tif": "image/tiff",
            "heic": "image/heic",
        }.get(ext, "application/octet-stream")

    # ---------- introspection ----------
    @staticmethod
    def list_supported_document_types() -> list[dict]:
        return [
            {
                "document_type": dt,
                "label": spec["label"],
                "satisfies": spec["satisfies"],
                "extracts_fields": spec["fields"],
            }
            for dt, spec in DOCUMENT_TYPES.items()
        ]
