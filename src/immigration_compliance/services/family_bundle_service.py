"""Family Bundle Engine — one intake → linked profiles + derivative cases.

The single biggest UX win for family-based immigration: when a primary
applicant's intake is complete, automatically generate linked profiles
and derivative cases for spouse, children, and other dependents — so the
attorney never re-enters the same data twice and the family files together.

Mechanics:
  - PrincipalProfile is the head case (H-1B, F-1, I-130 petitioner, etc.)
  - DerivativeProfile is each linked dependent (H-4 spouse, F-2 child,
    I-485 derivative, etc.)
  - The mapping (primary visa) → (derivative visa for each relationship)
    is data-driven via DERIVATIVE_RULES
  - For each derivative we auto-create:
      * a CaseWorkspace (linked to the same family bundle)
      * a derived intake answer set (inherits address, employer info, etc.
        from the principal where appropriate; clears identity-specific
        fields)
      * a derivative form list (G-28, I-539, I-765 for spouse, etc.)
  - Bundle-level snapshot returns every case in the family with rolled-up
    completeness so attorneys see all linked cases at once

Bundles are first-class: filed, tracked, and billed as a unit. This is
how Boundless made $50M+ on family-based immigration."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Derivative rules
# ---------------------------------------------------------------------------

# (primary_visa_type, relationship) → derivative case spec
DERIVATIVE_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "H-1B": {
        "spouse": {
            "derivative_visa": "H-4",
            "filing_with": "I-539",
            "ead_eligible": True,
            "ead_form": "I-765",
            "fields_to_inherit": ["us_address", "applicant_phone", "petitioner_name"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number", "ssn"],
        },
        "child": {
            "derivative_visa": "H-4",
            "filing_with": "I-539",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "applicant_phone", "petitioner_name"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "age_cap": 21,
        },
    },
    "L-1": {
        "spouse": {
            "derivative_visa": "L-2",
            "filing_with": "I-539",
            "ead_eligible": True,
            "ead_form": "I-765",
            "fields_to_inherit": ["us_address", "applicant_phone", "petitioner_name"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
        },
        "child": {
            "derivative_visa": "L-2",
            "filing_with": "I-539",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "applicant_phone", "petitioner_name"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "age_cap": 21,
        },
    },
    "O-1": {
        "spouse": {
            "derivative_visa": "O-3",
            "filing_with": "I-539",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "applicant_phone"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
        },
        "child": {
            "derivative_visa": "O-3",
            "filing_with": "I-539",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "applicant_phone"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "age_cap": 21,
        },
    },
    "F-1": {
        "spouse": {
            "derivative_visa": "F-2",
            "filing_with": "DS-160",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "school_name", "sevis_id"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "study_eligible": False,
        },
        "child": {
            "derivative_visa": "F-2",
            "filing_with": "DS-160",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "school_name", "sevis_id"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "age_cap": 21,
        },
    },
    "J-1": {
        "spouse": {
            "derivative_visa": "J-2",
            "filing_with": "DS-160",
            "ead_eligible": True,
            "ead_form": "I-765",
            "fields_to_inherit": ["us_address", "program_sponsor"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
        },
        "child": {
            "derivative_visa": "J-2",
            "filing_with": "DS-160",
            "ead_eligible": False,
            "fields_to_inherit": ["us_address", "program_sponsor"],
            "fields_to_clear": ["first_name", "last_name", "dob", "passport_number"],
            "age_cap": 21,
        },
    },
    "I-130": {
        "child": {
            "derivative_visa": "I-130",  # separate I-130 per child for IR-2/F-2A
            "filing_with": "I-130",
            "ead_eligible": False,
            "fields_to_inherit": ["petitioner_full_name", "petitioner_status"],
            "fields_to_clear": ["beneficiary_name", "beneficiary_dob", "passport_number"],
            "note": "Each child requires their own I-130 petition.",
        },
    },
    "I-485": {
        "spouse": {
            "derivative_visa": "I-485",  # derivative AOS application
            "filing_with": "I-485",
            "ead_eligible": True,
            "ead_form": "I-765",
            "advance_parole": True,
            "advance_parole_form": "I-131",
            "fields_to_inherit": ["applicant_address", "applicant_phone", "underlying_form", "underlying_receipt", "priority_date"],
            "fields_to_clear": ["applicant_name", "applicant_dob", "applicant_passport", "applicant_a_number"],
        },
        "child": {
            "derivative_visa": "I-485",
            "filing_with": "I-485",
            "ead_eligible": True,
            "ead_form": "I-765",
            "advance_parole": True,
            "advance_parole_form": "I-131",
            "fields_to_inherit": ["applicant_address", "underlying_form", "underlying_receipt", "priority_date"],
            "fields_to_clear": ["applicant_name", "applicant_dob", "applicant_passport"],
            "age_cap": 21,
            "note": "CSPA (Child Status Protection Act) age calculation may apply.",
        },
    },
}

VALID_RELATIONSHIPS = ("spouse", "child", "parent")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FamilyBundleService:
    """Manage family bundles: linked workspaces filed and tracked together."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._bundles: dict[str, dict] = {}

    # ---------- bundle lifecycle ----------
    def create_bundle(
        self,
        applicant_id: str,
        principal_workspace_id: str,
        principal_visa_type: str,
        label: str = "",
    ) -> dict:
        bundle_id = str(uuid.uuid4())
        bundle = {
            "id": bundle_id,
            "applicant_id": applicant_id,
            "principal_workspace_id": principal_workspace_id,
            "principal_visa_type": principal_visa_type,
            "label": label or f"{principal_visa_type} family",
            "members": [],   # list of {relationship, profile, derivative_workspace_id}
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "open",
        }
        self._bundles[bundle_id] = bundle
        return bundle

    def get_bundle(self, bundle_id: str) -> dict | None:
        return self._bundles.get(bundle_id)

    def list_bundles(self, applicant_id: str | None = None) -> list[dict]:
        out = list(self._bundles.values())
        if applicant_id:
            out = [b for b in out if b["applicant_id"] == applicant_id]
        return out

    def get_bundle_for_workspace(self, workspace_id: str) -> dict | None:
        for b in self._bundles.values():
            if b["principal_workspace_id"] == workspace_id:
                return b
            if any(m.get("derivative_workspace_id") == workspace_id for m in b["members"]):
                return b
        return None

    # ---------- adding family members ----------
    def add_dependent(
        self,
        bundle_id: str,
        relationship: str,
        first_name: str,
        last_name: str,
        dob: str,
        country: str = "",
        notes: str = "",
        auto_create_workspace: bool = True,
    ) -> dict:
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            raise ValueError(f"Bundle not found: {bundle_id}")
        if relationship not in VALID_RELATIONSHIPS:
            raise ValueError(f"Invalid relationship: {relationship}")

        # Check derivative rule for the principal visa
        primary = bundle["principal_visa_type"]
        rule = DERIVATIVE_RULES.get(primary, {}).get(relationship)
        if rule is None:
            raise ValueError(
                f"No derivative rule for primary={primary} relationship={relationship}. "
                "This combination may not be supported or may require a separate filing pathway."
            )

        # Age cap check
        if "age_cap" in rule and dob:
            age = self._compute_age(dob)
            if age is not None and age >= rule["age_cap"]:
                derivative = rule.get("derivative_visa")
                # Don't reject — flag it; some categories preserve eligibility under CSPA
                age_warning = f"Dependent is {age}, at or above the {rule['age_cap']}-year age cap. CSPA or aging-out analysis required."
            else:
                age_warning = None
        else:
            age_warning = None

        member = {
            "id": str(uuid.uuid4()),
            "bundle_id": bundle_id,
            "relationship": relationship,
            "profile": {
                "first_name": first_name,
                "last_name": last_name,
                "dob": dob,
                "country": country or self._principal_country(bundle),
                "notes": notes,
            },
            "derivative_visa": rule["derivative_visa"],
            "filing_with": rule.get("filing_with"),
            "ead_eligible": rule.get("ead_eligible", False),
            "ead_form": rule.get("ead_form"),
            "advance_parole_eligible": rule.get("advance_parole", False),
            "age_warning": age_warning,
            "rule_notes": rule.get("note"),
            "derivative_workspace_id": None,
            "added_at": datetime.utcnow().isoformat(),
        }

        # Auto-create workspace + derived intake
        if auto_create_workspace and self._cases:
            derivative_ws = self._spin_up_derivative_workspace(bundle, member, rule)
            if derivative_ws:
                member["derivative_workspace_id"] = derivative_ws["id"]

        bundle["members"].append(member)
        bundle["updated_at"] = datetime.utcnow().isoformat()
        return member

    def _principal_country(self, bundle: dict) -> str:
        if not self._cases:
            return ""
        ws = self._cases.get_workspace(bundle["principal_workspace_id"])
        return ws.get("country", "") if ws else ""

    def _principal_intake_answers(self, bundle: dict) -> dict:
        if not (self._cases and self._intake):
            return {}
        ws = self._cases.get_workspace(bundle["principal_workspace_id"])
        if not ws or not ws.get("intake_session_id"):
            return {}
        sess = self._intake.get_session(ws["intake_session_id"])
        return dict(sess["answers"]) if sess else {}

    def _spin_up_derivative_workspace(self, bundle: dict, member: dict, rule: dict) -> dict | None:
        """Create a workspace + derived intake session for this dependent."""
        principal_ws = self._cases.get_workspace(bundle["principal_workspace_id"])
        if not principal_ws:
            return None
        country = principal_ws.get("country", "US")
        derivative_visa = rule["derivative_visa"]
        label = f"{member['profile']['first_name']} ({member['relationship']}) — {derivative_visa}"

        # Create derived intake answers
        principal_answers = self._principal_intake_answers(bundle)
        derived_answers: dict[str, Any] = {}
        for f in rule.get("fields_to_inherit", []):
            if f in principal_answers:
                derived_answers[f] = principal_answers[f]
        derived_answers["first_name"] = member["profile"]["first_name"]
        derived_answers["last_name"] = member["profile"]["last_name"]
        derived_answers["dob"] = member["profile"]["dob"]
        derived_answers["derived_from_workspace_id"] = principal_ws["id"]
        derived_answers["relationship_to_principal"] = member["relationship"]

        # Start a new intake session if the engine supports the derivative visa
        derived_session_id = None
        if self._intake:
            try:
                if self._intake.get_visa_config(derivative_visa) is not None:
                    sess = self._intake.start_session(bundle["applicant_id"], derivative_visa)
                    self._intake.submit_answers(sess["id"], derived_answers)
                    derived_session_id = sess["id"]
            except Exception:
                derived_session_id = None

        ws = self._cases.create_workspace(
            applicant_id=bundle["applicant_id"],
            visa_type=derivative_visa,
            country=country,
            intake_session_id=derived_session_id,
            attorney_id=principal_ws.get("attorney_id"),
            case_label=label,
        )
        # Tag the workspace as part of this bundle
        ws["family_bundle_id"] = bundle["id"]
        ws["principal_workspace_id"] = principal_ws["id"]
        ws["relationship_to_principal"] = member["relationship"]
        return ws

    # ---------- bundle queries ----------
    def get_bundle_snapshot(self, bundle_id: str) -> dict:
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            raise ValueError(f"Bundle not found: {bundle_id}")
        members = []
        principal_snapshot = None
        if self._cases:
            try:
                principal_snapshot = self._cases.get_snapshot(bundle["principal_workspace_id"])
            except Exception:
                principal_snapshot = None

            for m in bundle["members"]:
                if m.get("derivative_workspace_id"):
                    try:
                        s = self._cases.get_snapshot(m["derivative_workspace_id"])
                    except Exception:
                        s = None
                    members.append({"member": m, "snapshot": s})
                else:
                    members.append({"member": m, "snapshot": None})

        # Roll-up completeness across the family
        all_pcts = []
        if principal_snapshot:
            all_pcts.append((principal_snapshot.get("completeness") or {}).get("overall_pct", 0))
        for entry in members:
            s = entry["snapshot"]
            if s:
                all_pcts.append((s.get("completeness") or {}).get("overall_pct", 0))
        family_overall = round(sum(all_pcts) / len(all_pcts)) if all_pcts else 0

        return {
            "bundle": bundle,
            "principal_snapshot": principal_snapshot,
            "members": members,
            "family_completeness_pct": family_overall,
            "computed_at": datetime.utcnow().isoformat(),
        }

    def list_required_forms_for_bundle(self, bundle_id: str) -> list[dict]:
        """Aggregate every form across the principal + derivative cases."""
        bundle = self._bundles.get(bundle_id)
        if bundle is None:
            raise ValueError(f"Bundle not found: {bundle_id}")
        forms: list[dict] = []
        forms.append({
            "workspace_id": bundle["principal_workspace_id"],
            "subject": "Principal",
            "visa_type": bundle["principal_visa_type"],
            "filing_with": bundle["principal_visa_type"],
        })
        for m in bundle["members"]:
            entry = {
                "workspace_id": m.get("derivative_workspace_id"),
                "subject": f"{m['profile']['first_name']} ({m['relationship']})",
                "visa_type": m["derivative_visa"],
                "filing_with": m.get("filing_with"),
            }
            forms.append(entry)
            if m.get("ead_eligible") and m.get("ead_form"):
                forms.append({
                    "workspace_id": m.get("derivative_workspace_id"),
                    "subject": f"{m['profile']['first_name']} ({m['relationship']}) — EAD",
                    "visa_type": "EAD",
                    "filing_with": m["ead_form"],
                })
            if m.get("advance_parole_eligible"):
                forms.append({
                    "workspace_id": m.get("derivative_workspace_id"),
                    "subject": f"{m['profile']['first_name']} ({m['relationship']}) — Advance Parole",
                    "visa_type": "Advance Parole",
                    "filing_with": "I-131",
                })
        return forms

    @staticmethod
    def _compute_age(dob: str) -> int | None:
        try:
            d = date.fromisoformat(dob)
        except (TypeError, ValueError):
            return None
        today = date.today()
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

    # ---------- introspection ----------
    @staticmethod
    def list_supported_combinations() -> list[dict]:
        out: list[dict] = []
        for primary, rels in DERIVATIVE_RULES.items():
            for rel, rule in rels.items():
                out.append({
                    "primary_visa": primary,
                    "relationship": rel,
                    "derivative_visa": rule["derivative_visa"],
                    "filing_with": rule.get("filing_with"),
                    "ead_eligible": rule.get("ead_eligible", False),
                    "age_cap": rule.get("age_cap"),
                })
        return out
