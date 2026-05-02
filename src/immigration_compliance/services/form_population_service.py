"""Smart Form Auto-Population — single intake → populates USCIS / agency forms.

Every populated field carries field-level provenance: which intake answer
(or extracted document field) drove it, when, and with what confidence. This
makes the output auditable for the attorney and bi-directionally syncable
(change a form value → update the source; change the source → update the form).

Form schema registry covers the highest-volume forms:
  - G-28      Notice of Entry of Appearance as Attorney
  - I-129     Petition for a Nonimmigrant Worker (H-1B / L-1 / O-1)
  - I-130     Petition for Alien Relative
  - I-485     Application to Register Permanent Residence
  - I-765     Application for Employment Authorization
  - I-131     Application for Travel Document
  - DS-160    (subset — bio, passport, address, contact)

Each schema defines fields with: id, label, type, source (intake.<id> or
extracted.<doc_type>.<field>), default ("N/A" per USCIS empty-field guidance),
required, and a section grouping for UI rendering.

The engine is rules-based today. To swap in an LLM-based form filler later,
override `_resolve_source` to consult the LLM after the deterministic pass."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Form Schema Registry
# ---------------------------------------------------------------------------

# Source notation:
#   "intake.<answer_id>"           → pull from intake answers
#   "extracted.<doc_type>.<field>" → pull from a doc of that type's extracted data
#   "applicant.<field>"            → pull from applicant profile
#   "static.<value>"               → hardcoded literal (rare — used for form metadata)
#   "computed.<rule>"              → server-computed (e.g., today's date, age)

FORM_SCHEMAS: dict[str, dict[str, Any]] = {
    "G-28": {
        "name": "G-28 — Notice of Entry of Appearance as Attorney or Accredited Representative",
        "agency": "USCIS",
        "edition": "07/13/23",
        "sections": ["Attorney Info", "Client Info", "Signatures"],
        "fields": [
            {"id": "atty_full_name",     "label": "Attorney full name",                "type": "text",   "source": "applicant.attorney_full_name",  "section": "Attorney Info", "required": True},
            {"id": "atty_bar_number",    "label": "Bar number",                        "type": "text",   "source": "applicant.attorney_bar_number", "section": "Attorney Info", "required": True},
            {"id": "atty_firm_name",     "label": "Firm name",                         "type": "text",   "source": "applicant.attorney_firm",       "section": "Attorney Info"},
            {"id": "atty_state",         "label": "State of bar admission",            "type": "text",   "source": "applicant.attorney_state",      "section": "Attorney Info", "required": True},
            {"id": "client_full_name",   "label": "Client full name",                  "type": "text",   "source": "extracted.passport.full_name",  "section": "Client Info",    "required": True, "fallback_source": "intake.client_name"},
            {"id": "client_dob",         "label": "Client date of birth",              "type": "date",   "source": "extracted.passport.dob",        "section": "Client Info",    "required": True},
            {"id": "client_country",     "label": "Country of citizenship",            "type": "text",   "source": "extracted.passport.nationality","section": "Client Info"},
            {"id": "client_address",     "label": "Client address",                    "type": "text",   "source": "intake.applicant_address",      "section": "Client Info"},
            {"id": "form_filed_with",    "label": "Form being filed",                  "type": "text",   "source": "intake.target_form",            "section": "Signatures"},
            {"id": "engagement_date",    "label": "Date of engagement",                "type": "date",   "source": "computed.today",                "section": "Signatures"},
        ],
    },
    "I-129": {
        "name": "I-129 — Petition for a Nonimmigrant Worker",
        "agency": "USCIS",
        "edition": "01/17/25",
        "applicable_visas": ["H-1B", "L-1", "O-1", "TN", "P-1"],
        "sections": ["Petitioner", "Beneficiary", "Position", "Wage", "Employment Period"],
        "fields": [
            {"id": "petitioner_legal_name", "label": "Petitioner legal name",          "type": "text",   "source": "intake.petitioner_name",         "section": "Petitioner", "required": True},
            {"id": "petitioner_fein",        "label": "Petitioner FEIN",                "type": "text",   "source": "intake.petitioner_fein",         "section": "Petitioner", "required": True},
            {"id": "petitioner_naics",       "label": "Petitioner NAICS code",          "type": "text",   "source": "intake.petitioner_naics",        "section": "Petitioner"},
            {"id": "petitioner_year_est",    "label": "Year established",               "type": "number", "source": "intake.petitioner_year_established", "section": "Petitioner"},
            {"id": "petitioner_employees",   "label": "Number of employees",            "type": "number", "source": "intake.petitioner_employees",    "section": "Petitioner"},
            {"id": "petitioner_revenue",     "label": "Gross annual income (USD)",      "type": "number", "source": "intake.petitioner_revenue",      "section": "Petitioner"},
            {"id": "beneficiary_name",       "label": "Beneficiary full name",          "type": "text",   "source": "extracted.passport.full_name",   "section": "Beneficiary", "required": True},
            {"id": "beneficiary_dob",        "label": "Beneficiary date of birth",      "type": "date",   "source": "extracted.passport.dob",         "section": "Beneficiary", "required": True},
            {"id": "beneficiary_country",    "label": "Country of birth",               "type": "text",   "source": "extracted.passport.nationality", "section": "Beneficiary"},
            {"id": "beneficiary_passport",   "label": "Passport number",                "type": "text",   "source": "extracted.passport.passport_number", "section": "Beneficiary"},
            {"id": "beneficiary_i94",        "label": "I-94 admission number",          "type": "text",   "source": "extracted.i94.admission_number", "section": "Beneficiary"},
            {"id": "beneficiary_status",     "label": "Current immigration status",     "type": "text",   "source": "intake.current_status_in_us",    "section": "Beneficiary"},
            {"id": "position_title",         "label": "Position title",                 "type": "text",   "source": "intake.position_title",          "section": "Position", "required": True},
            {"id": "position_soc",           "label": "SOC code",                       "type": "text",   "source": "intake.position_soc_code",       "section": "Position"},
            {"id": "position_duties",        "label": "Position duties (summary)",      "type": "text",   "source": "intake.position_duties",         "section": "Position"},
            {"id": "wage_offered",           "label": "Wage offered",                   "type": "number", "source": "extracted.lca.wage_rate",        "section": "Wage", "required": True, "fallback_source": "intake.wage_offered"},
            {"id": "wage_level",             "label": "Wage level",                     "type": "text",   "source": "extracted.lca.wage_level",       "section": "Wage", "fallback_source": "intake.wage_level"},
            {"id": "wage_unit",              "label": "Wage unit (yr/hr/wk/mo/bi)",     "type": "text",   "source": "intake.wage_unit",               "section": "Wage", "default": "yr"},
            {"id": "lca_number",             "label": "LCA number",                     "type": "text",   "source": "extracted.lca.lca_number",       "section": "Wage"},
            {"id": "employment_start",       "label": "Requested start date",           "type": "date",   "source": "intake.employment_start_date",   "section": "Employment Period", "required": True},
            {"id": "employment_end",         "label": "Requested end date",             "type": "date",   "source": "intake.employment_end_date",     "section": "Employment Period", "required": True},
            {"id": "worksite_address",       "label": "Worksite address",               "type": "text",   "source": "intake.worksite_address",        "section": "Employment Period"},
        ],
    },
    "I-130": {
        "name": "I-130 — Petition for Alien Relative",
        "agency": "USCIS",
        "edition": "04/01/24",
        "sections": ["Petitioner", "Beneficiary", "Relationship"],
        "fields": [
            {"id": "petitioner_full_name", "label": "Petitioner full name",          "type": "text", "source": "intake.petitioner_full_name", "section": "Petitioner", "required": True},
            {"id": "petitioner_dob",       "label": "Petitioner date of birth",      "type": "date", "source": "intake.petitioner_dob",        "section": "Petitioner", "required": True},
            {"id": "petitioner_status",    "label": "Petitioner status (USC/LPR)",   "type": "text", "source": "intake.petitioner_status",     "section": "Petitioner", "required": True},
            {"id": "petitioner_a_number",  "label": "Petitioner A-number (if LPR)",  "type": "text", "source": "intake.petitioner_a_number",   "section": "Petitioner"},
            {"id": "beneficiary_name",     "label": "Beneficiary full name",         "type": "text", "source": "extracted.passport.full_name", "section": "Beneficiary", "required": True},
            {"id": "beneficiary_dob",      "label": "Beneficiary date of birth",     "type": "date", "source": "extracted.passport.dob",       "section": "Beneficiary", "required": True},
            {"id": "beneficiary_country",  "label": "Country of birth",              "type": "text", "source": "extracted.passport.nationality","section": "Beneficiary"},
            {"id": "relationship",         "label": "Relationship to petitioner",    "type": "text", "source": "intake.relationship",          "section": "Relationship", "required": True},
            {"id": "marriage_date",        "label": "Date of marriage (if spouse)",  "type": "date", "source": "extracted.marriage_certificate.date_of_marriage", "section": "Relationship"},
            {"id": "marriage_place",       "label": "Place of marriage (if spouse)", "type": "text", "source": "extracted.marriage_certificate.place_of_marriage","section": "Relationship"},
            {"id": "prior_petitions",      "label": "Petitioner prior I-130s for spouses?", "type": "boolean", "source": "intake.prior_petitions", "section": "Relationship"},
        ],
    },
    "I-485": {
        "name": "I-485 — Application to Register Permanent Residence or Adjust Status",
        "agency": "USCIS",
        "edition": "12/02/24",
        "sections": ["Applicant", "Underlying Petition", "Status & Eligibility", "Background"],
        "fields": [
            {"id": "applicant_name",         "label": "Applicant full name",         "type": "text", "source": "extracted.passport.full_name",  "section": "Applicant", "required": True},
            {"id": "applicant_dob",          "label": "Applicant date of birth",     "type": "date", "source": "extracted.passport.dob",        "section": "Applicant", "required": True},
            {"id": "applicant_passport",     "label": "Passport number",             "type": "text", "source": "extracted.passport.passport_number", "section": "Applicant"},
            {"id": "applicant_country",      "label": "Country of citizenship",      "type": "text", "source": "extracted.passport.nationality","section": "Applicant"},
            {"id": "applicant_a_number",     "label": "A-number (if any)",           "type": "text", "source": "intake.a_number",               "section": "Applicant"},
            {"id": "applicant_address",      "label": "Mailing address",             "type": "text", "source": "intake.applicant_address",      "section": "Applicant"},
            {"id": "applicant_phone",        "label": "Phone number",                "type": "text", "source": "intake.applicant_phone",        "section": "Applicant"},
            {"id": "applicant_email",        "label": "Email address",               "type": "text", "source": "intake.applicant_email",        "section": "Applicant"},
            {"id": "underlying_form",        "label": "Underlying petition form",    "type": "text", "source": "intake.underlying_form",        "section": "Underlying Petition", "required": True},
            {"id": "underlying_receipt",     "label": "Underlying receipt number",   "type": "text", "source": "extracted.approval_notice.receipt_number", "section": "Underlying Petition", "required": True},
            {"id": "underlying_priority",    "label": "Priority date",               "type": "date", "source": "intake.priority_date",          "section": "Underlying Petition", "required": True},
            {"id": "i94_admission_number",   "label": "I-94 admission number",       "type": "text", "source": "extracted.i94.admission_number","section": "Status & Eligibility"},
            {"id": "i94_class",              "label": "I-94 class of admission",     "type": "text", "source": "extracted.i94.class_of_admission","section": "Status & Eligibility"},
            {"id": "lawful_status_maintained","label": "Status maintained continuously?","type": "boolean", "source": "intake.lawful_status_maintained", "section": "Status & Eligibility"},
            {"id": "criminal_history",       "label": "Criminal history?",           "type": "boolean", "source": "intake.criminal_history",   "section": "Background"},
            {"id": "previously_removed",     "label": "Ever in removal proceedings?","type": "boolean", "source": "intake.previously_removed", "section": "Background"},
            {"id": "public_charge_concern",  "label": "Public benefits used?",       "type": "boolean", "source": "intake.public_charge_concern","section": "Background"},
        ],
    },
    "I-765": {
        "name": "I-765 — Application for Employment Authorization",
        "agency": "USCIS",
        "edition": "04/01/24",
        "sections": ["Applicant", "Eligibility"],
        "fields": [
            {"id": "applicant_name",         "label": "Applicant full name",        "type": "text", "source": "extracted.passport.full_name",  "section": "Applicant", "required": True},
            {"id": "applicant_dob",          "label": "Applicant date of birth",    "type": "date", "source": "extracted.passport.dob",        "section": "Applicant", "required": True},
            {"id": "applicant_country",      "label": "Country of birth",           "type": "text", "source": "extracted.passport.nationality","section": "Applicant"},
            {"id": "applicant_a_number",     "label": "A-number (if any)",          "type": "text", "source": "intake.a_number",               "section": "Applicant"},
            {"id": "applicant_address",      "label": "Mailing address",            "type": "text", "source": "intake.applicant_address",      "section": "Applicant"},
            {"id": "category",               "label": "Eligibility category code",  "type": "text", "source": "intake.ead_category",           "section": "Eligibility", "required": True},
            {"id": "i94",                    "label": "I-94 admission number",      "type": "text", "source": "extracted.i94.admission_number","section": "Eligibility"},
            {"id": "ssn_request",            "label": "Request SSN with EAD?",      "type": "boolean", "source": "intake.ssn_request",         "section": "Eligibility"},
        ],
    },
    "I-131": {
        "name": "I-131 — Application for Travel Document",
        "agency": "USCIS",
        "edition": "04/01/24",
        "sections": ["Applicant", "Travel Document Request"],
        "fields": [
            {"id": "applicant_name",         "label": "Applicant full name",        "type": "text", "source": "extracted.passport.full_name",  "section": "Applicant", "required": True},
            {"id": "applicant_dob",          "label": "Applicant date of birth",    "type": "date", "source": "extracted.passport.dob",        "section": "Applicant", "required": True},
            {"id": "applicant_a_number",     "label": "A-number (if any)",          "type": "text", "source": "intake.a_number",               "section": "Applicant"},
            {"id": "applicant_address",      "label": "Mailing address",            "type": "text", "source": "intake.applicant_address",      "section": "Applicant"},
            {"id": "doc_requested",          "label": "Document requested",         "type": "text", "source": "intake.travel_doc_type",        "section": "Travel Document Request", "required": True},
            {"id": "purpose_of_travel",      "label": "Purpose of travel",          "type": "text", "source": "intake.purpose_of_travel",      "section": "Travel Document Request"},
            {"id": "expected_departure",     "label": "Expected departure date",    "type": "date", "source": "intake.expected_departure",     "section": "Travel Document Request"},
            {"id": "duration_outside_us",    "label": "Expected duration outside US","type": "text", "source": "intake.duration_outside_us",   "section": "Travel Document Request"},
        ],
    },
    "DS-160": {
        "name": "DS-160 — Online Nonimmigrant Visa Application (subset)",
        "agency": "U.S. Department of State",
        "edition": "rolling",
        "sections": ["Personal", "Passport", "Travel", "Contact"],
        "fields": [
            {"id": "surname",                "label": "Surname",                    "type": "text", "source": "extracted.passport.full_name",  "section": "Personal", "required": True},
            {"id": "given_names",            "label": "Given names",                "type": "text", "source": "extracted.passport.full_name",  "section": "Personal", "required": True},
            {"id": "dob",                    "label": "Date of birth",              "type": "date", "source": "extracted.passport.dob",        "section": "Personal", "required": True},
            {"id": "place_of_birth",         "label": "Place of birth",             "type": "text", "source": "intake.place_of_birth",         "section": "Personal", "required": True},
            {"id": "nationality",            "label": "Nationality",                "type": "text", "source": "extracted.passport.nationality","section": "Personal", "required": True},
            {"id": "passport_number",        "label": "Passport number",            "type": "text", "source": "extracted.passport.passport_number","section": "Passport", "required": True},
            {"id": "passport_expiry",        "label": "Passport expiry",            "type": "date", "source": "extracted.passport.expiry",     "section": "Passport", "required": True},
            {"id": "purpose_of_trip",        "label": "Purpose of trip",            "type": "text", "source": "intake.purpose_of_trip",        "section": "Travel"},
            {"id": "intended_arrival",       "label": "Intended date of arrival",   "type": "date", "source": "intake.intended_arrival",       "section": "Travel"},
            {"id": "us_address",             "label": "US address while there",     "type": "text", "source": "intake.us_address",             "section": "Travel"},
            {"id": "phone",                  "label": "Phone",                      "type": "text", "source": "intake.applicant_phone",        "section": "Contact"},
            {"id": "email",                  "label": "Email",                      "type": "text", "source": "intake.applicant_email",        "section": "Contact"},
            {"id": "social_media_disclosure","label": "Social media handles",       "type": "text", "source": "intake.social_media_handles",   "section": "Contact"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Form Population Service
# ---------------------------------------------------------------------------

class FormPopulationService:
    """Populate USCIS / agency forms from intake answers + extracted document fields.

    Storage of populated forms is in-memory; production swaps in a DB. Provenance
    log is the same shape and never compacted — it's the audit trail."""

    def __init__(self) -> None:
        self._populated: dict[str, dict] = {}
        self._provenance: list[dict] = []

    # ---------- introspection ----------
    @staticmethod
    def list_forms(visa_type: str | None = None) -> list[dict]:
        out = []
        for fid, schema in FORM_SCHEMAS.items():
            if visa_type and "applicable_visas" in schema and visa_type not in schema["applicable_visas"]:
                continue
            out.append({
                "form_id": fid,
                "name": schema["name"],
                "agency": schema["agency"],
                "edition": schema["edition"],
                "sections": schema["sections"],
                "field_count": len(schema["fields"]),
                "applicable_visas": schema.get("applicable_visas", []),
            })
        return out

    @staticmethod
    def get_form_schema(form_id: str) -> dict | None:
        return FORM_SCHEMAS.get(form_id)

    @staticmethod
    def list_recommended_forms_for_visa(visa_type: str) -> list[str]:
        """Which forms typically need to be filed for this visa type."""
        recommendations: dict[str, list[str]] = {
            "H-1B":   ["G-28", "I-129", "DS-160"],
            "L-1":    ["G-28", "I-129", "DS-160"],
            "O-1":    ["G-28", "I-129", "DS-160"],
            "TN":     ["G-28", "I-129"],
            "I-130":  ["G-28", "I-130"],
            "I-485":  ["G-28", "I-485", "I-765", "I-131"],
            "F-1":    ["DS-160"],
            "J-1":    ["DS-160"],
        }
        return recommendations.get(visa_type, [])

    # ---------- population ----------
    def populate(
        self,
        form_id: str,
        applicant_id: str,
        intake_answers: dict | None = None,
        extracted_documents: list[dict] | None = None,
        applicant_profile: dict | None = None,
        empty_field_default: str = "N/A",
    ) -> dict:
        """Run population for a single form and return the filled record with provenance."""
        schema = FORM_SCHEMAS.get(form_id)
        if not schema:
            raise ValueError(f"Unknown form: {form_id}")
        intake_answers = intake_answers or {}
        applicant_profile = applicant_profile or {}
        extracted_index = self._index_extracted(extracted_documents or [])
        record_id = str(uuid.uuid4())

        populated_fields: list[dict] = []
        for spec in schema["fields"]:
            value, source_used, confidence = self._resolve_source(
                spec.get("source"),
                spec.get("fallback_source"),
                intake_answers,
                extracted_index,
                applicant_profile,
            )
            filled = value not in (None, "")
            display_value = value if filled else (spec.get("default") or empty_field_default)
            populated_fields.append({
                "field_id": spec["id"],
                "label": spec["label"],
                "type": spec["type"],
                "section": spec["section"],
                "required": spec.get("required", False),
                "value": display_value,
                "filled": filled,
                "source": source_used,
                "confidence": confidence,
                "manually_overridden": False,
            })

        required_total = sum(1 for f in populated_fields if f["required"])
        required_filled = sum(1 for f in populated_fields if f["required"] and f["filled"])
        completeness_pct = round((required_filled / required_total) * 100) if required_total else 100

        record = {
            "id": record_id,
            "form_id": form_id,
            "form_name": schema["name"],
            "agency": schema["agency"],
            "edition": schema["edition"],
            "applicant_id": applicant_id,
            "fields": populated_fields,
            "sections": schema["sections"],
            "required_total": required_total,
            "required_filled": required_filled,
            "completeness_pct": completeness_pct,
            "ready_to_file": completeness_pct == 100,
            "populated_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._populated[record_id] = record
        # Log provenance for every filled field
        for f in populated_fields:
            if f["filled"]:
                self._provenance.append({
                    "record_id": record_id,
                    "form_id": form_id,
                    "field_id": f["field_id"],
                    "value": f["value"],
                    "source": f["source"],
                    "logged_at": record["populated_at"],
                    "kind": "auto",
                })
        return record

    def populate_bundle(
        self,
        applicant_id: str,
        visa_type: str,
        intake_answers: dict | None = None,
        extracted_documents: list[dict] | None = None,
        applicant_profile: dict | None = None,
    ) -> dict:
        """Populate all recommended forms for a visa type in a single bundle."""
        forms_to_fill = self.list_recommended_forms_for_visa(visa_type)
        records = []
        total_required = 0
        total_filled = 0
        for fid in forms_to_fill:
            rec = self.populate(fid, applicant_id, intake_answers, extracted_documents, applicant_profile)
            records.append(rec)
            total_required += rec["required_total"]
            total_filled += rec["required_filled"]
        bundle_pct = round((total_filled / total_required) * 100) if total_required else 100
        return {
            "applicant_id": applicant_id,
            "visa_type": visa_type,
            "forms": records,
            "bundle_completeness_pct": bundle_pct,
            "total_required_fields": total_required,
            "total_filled_fields": total_filled,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ---------- bi-directional sync ----------
    def update_field(self, record_id: str, field_id: str, new_value: Any, edited_by: str = "user") -> dict:
        """Override a populated value. Records the override in the provenance log."""
        record = self._populated.get(record_id)
        if record is None:
            raise ValueError(f"Form record not found: {record_id}")
        target = next((f for f in record["fields"] if f["field_id"] == field_id), None)
        if target is None:
            raise ValueError(f"Field not found: {field_id}")
        target["value"] = new_value
        target["filled"] = new_value not in (None, "", "N/A")
        target["manually_overridden"] = True
        target["source"] = f"manual.{edited_by}"
        target["confidence"] = 1.0
        record["updated_at"] = datetime.utcnow().isoformat()
        # Recompute completeness
        required_total = sum(1 for f in record["fields"] if f["required"])
        required_filled = sum(1 for f in record["fields"] if f["required"] and f["filled"])
        record["required_filled"] = required_filled
        record["completeness_pct"] = round((required_filled / required_total) * 100) if required_total else 100
        record["ready_to_file"] = record["completeness_pct"] == 100
        # Provenance log entry
        self._provenance.append({
            "record_id": record_id,
            "form_id": record["form_id"],
            "field_id": field_id,
            "value": new_value,
            "source": f"manual.{edited_by}",
            "logged_at": record["updated_at"],
            "kind": "manual_override",
        })
        return record

    def get_record(self, record_id: str) -> dict | None:
        return self._populated.get(record_id)

    def list_records(self, applicant_id: str | None = None, form_id: str | None = None) -> list[dict]:
        records = list(self._populated.values())
        if applicant_id:
            records = [r for r in records if r["applicant_id"] == applicant_id]
        if form_id:
            records = [r for r in records if r["form_id"] == form_id]
        return records

    def get_provenance(self, record_id: str | None = None, field_id: str | None = None) -> list[dict]:
        log = self._provenance
        if record_id:
            log = [p for p in log if p["record_id"] == record_id]
        if field_id:
            log = [p for p in log if p["field_id"] == field_id]
        return log

    # ---------- internals ----------
    @staticmethod
    def _index_extracted(extracted_documents: list[dict]) -> dict[str, dict]:
        """Index uploaded docs by document_type. If multiple docs share a type, the
        most-recently-uploaded wins."""
        idx: dict[str, dict] = {}
        for d in sorted(extracted_documents, key=lambda d: d.get("uploaded_at", "")):
            dt = d.get("document_type")
            if dt:
                idx[dt] = d
        return idx

    @staticmethod
    def _resolve_source(
        source: str | None,
        fallback_source: str | None,
        intake_answers: dict,
        extracted_index: dict[str, dict],
        applicant_profile: dict,
    ) -> tuple[Any, str | None, float]:
        for candidate in [source, fallback_source]:
            if not candidate:
                continue
            value = FormPopulationService._lookup(candidate, intake_answers, extracted_index, applicant_profile)
            if value not in (None, ""):
                # Confidence: extracted doc fields = 0.9; intake = 0.95; profile = 0.97; computed = 1.0
                if candidate.startswith("extracted."):
                    return value, candidate, 0.9
                if candidate.startswith("intake."):
                    return value, candidate, 0.95
                if candidate.startswith("applicant."):
                    return value, candidate, 0.97
                if candidate.startswith("computed."):
                    return value, candidate, 1.0
                if candidate.startswith("static."):
                    return value, candidate, 1.0
        return None, None, 0.0

    @staticmethod
    def _lookup(source: str, intake_answers: dict, extracted_index: dict, applicant_profile: dict) -> Any:
        if source.startswith("intake."):
            return intake_answers.get(source[len("intake."):])
        if source.startswith("applicant."):
            return applicant_profile.get(source[len("applicant."):])
        if source.startswith("static."):
            return source[len("static."):]
        if source.startswith("computed."):
            rule = source[len("computed."):]
            if rule == "today":
                return datetime.utcnow().date().isoformat()
            return None
        if source.startswith("extracted."):
            tail = source[len("extracted."):]
            if "." not in tail:
                return None
            doc_type, field_name = tail.split(".", 1)
            doc = extracted_index.get(doc_type)
            if not doc:
                return None
            return doc.get("extracted", {}).get(field_name)
        return None
