"""Attorney Match — intake-aware ranking of verified attorneys.

Ranks attorneys for an applicant using:
  - visa specialization match  (40 pts)
  - jurisdiction / country fit  (20 pts)
  - language overlap            (10 pts)
  - capacity / accepting status (10 pts)
  - red-flag handling experience (10 pts)
  - response time / SLA          ( 5 pts)
  - approval-rate signal         ( 5 pts)

Inputs come from the intake session (visa_type, country, answers, red_flags).
Output is a ranked list with explanation of every score component."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Default attorney directory — replace with database query in production
# ---------------------------------------------------------------------------

DEFAULT_ATTORNEYS: list[dict[str, Any]] = [
    {
        "id": "atty-001",
        "name": "Jennifer Park",
        "country": "US",
        "jurisdictions": ["NY", "NJ"],
        "specializations": ["H-1B", "L-1", "O-1", "EB-1", "EB-2", "F-1"],
        "languages": ["English", "Korean"],
        "years_experience": 12,
        "approval_rate": 0.96,
        "rfe_response_success_rate": 0.92,
        "avg_response_time_hours": 4,
        "active_cases": 8,
        "max_active_cases": 15,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": ["SPECIALTY_OCCUPATION_LEVEL_I", "EMPLOYER_EMPLOYEE_RELATIONSHIP", "DEGREE_FIELD_MISMATCH"],
        "bar_number": "NY-2013-58293",
    },
    {
        "id": "atty-002",
        "name": "Michael Torres",
        "country": "US",
        "jurisdictions": ["CA", "TX"],
        "specializations": ["H-1B", "I-130", "I-485", "Naturalization"],
        "languages": ["English", "Spanish"],
        "years_experience": 8,
        "approval_rate": 0.93,
        "rfe_response_success_rate": 0.85,
        "avg_response_time_hours": 8,
        "active_cases": 12,
        "max_active_cases": 20,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": ["I864_DEFICIENCY", "STATUS_VIOLATION", "INSUFFICIENT_RELATIONSHIP_EVIDENCE"],
        "bar_number": "CA-2017-19284",
    },
    {
        "id": "atty-003",
        "name": "David Kim",
        "country": "US",
        "jurisdictions": ["IL", "WI"],
        "specializations": ["H-1B", "L-1", "O-1", "EB-1", "EB-5", "TN"],
        "languages": ["English", "Korean", "Mandarin"],
        "years_experience": 15,
        "approval_rate": 0.95,
        "rfe_response_success_rate": 0.90,
        "avg_response_time_hours": 12,
        "active_cases": 14,
        "max_active_cases": 18,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": ["SPECIALTY_OCCUPATION_LEVEL_I", "INSUFFICIENT_CRITERIA_EVIDENCE", "WEAK_EXPERT_LETTERS"],
        "bar_number": "IL-2010-49183",
    },
    {
        "id": "atty-004",
        "name": "Priya Iyer",
        "country": "US",
        "jurisdictions": ["MA", "NH"],
        "specializations": ["F-1", "J-1", "H-1B", "EB-1", "O-1"],
        "languages": ["English", "Hindi", "Tamil"],
        "years_experience": 10,
        "approval_rate": 0.94,
        "rfe_response_success_rate": 0.88,
        "avg_response_time_hours": 6,
        "active_cases": 9,
        "max_active_cases": 16,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": ["SPECIALTY_OCCUPATION_LEVEL_I", "INSUFFICIENT_CRITERIA_EVIDENCE", "WEAK_TIES_TO_HOME"],
        "bar_number": "MA-2015-39281",
    },
    {
        "id": "atty-005",
        "name": "Rachel Adeyemi",
        "country": "UK",
        "jurisdictions": ["England-Wales"],
        "specializations": ["UK-Skilled-Worker", "UK-Student", "UK-Family"],
        "languages": ["English", "French"],
        "years_experience": 9,
        "approval_rate": 0.91,
        "rfe_response_success_rate": 0.86,
        "avg_response_time_hours": 6,
        "active_cases": 7,
        "max_active_cases": 14,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": [],
        "bar_number": "SRA-583920",
    },
    {
        "id": "atty-006",
        "name": "Chen Wei",
        "country": "CA",
        "jurisdictions": ["ON", "BC"],
        "specializations": ["CA-Express-Entry", "CA-Study-Permit", "PNP", "Spousal-Sponsorship"],
        "languages": ["English", "Mandarin", "Cantonese"],
        "years_experience": 11,
        "approval_rate": 0.94,
        "rfe_response_success_rate": 0.89,
        "avg_response_time_hours": 5,
        "active_cases": 10,
        "max_active_cases": 18,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": [],
        "bar_number": "LSO-72839",
    },
    {
        "id": "atty-007",
        "name": "Liam O'Connor",
        "country": "AU",
        "jurisdictions": ["VIC", "NSW"],
        "specializations": ["AU-Subclass-500", "AU-Subclass-482", "AU-189", "AU-190"],
        "languages": ["English"],
        "years_experience": 13,
        "approval_rate": 0.93,
        "rfe_response_success_rate": 0.87,
        "avg_response_time_hours": 8,
        "active_cases": 11,
        "max_active_cases": 17,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": [],
        "bar_number": "MARA-1582937",
    },
    {
        "id": "atty-008",
        "name": "Lukas Müller",
        "country": "DE",
        "jurisdictions": ["Berlin", "Bayern"],
        "specializations": ["DE-Blue-Card", "DE-Student", "Niederlassungserlaubnis"],
        "languages": ["English", "German"],
        "years_experience": 7,
        "approval_rate": 0.92,
        "rfe_response_success_rate": 0.84,
        "avg_response_time_hours": 10,
        "active_cases": 6,
        "max_active_cases": 12,
        "accepting_new_cases": True,
        "verified": True,
        "marketplace_optin": True,
        "rfe_categories_handled": [],
        "bar_number": "BRAK-583791",
    },
]


class AttorneyMatchService:
    """Match applicants with verified attorneys based on intake context."""

    def __init__(self, attorneys: list[dict] | None = None) -> None:
        self._attorneys: list[dict] = list(attorneys) if attorneys is not None else list(DEFAULT_ATTORNEYS)
        self._match_log: list[dict] = []

    # ---------- registry ----------
    def add_attorney(self, attorney: dict) -> dict:
        attorney = {**attorney}
        attorney.setdefault("id", str(uuid.uuid4()))
        self._attorneys.append(attorney)
        return attorney

    def update_attorney(self, attorney_id: str, updates: dict) -> dict | None:
        for a in self._attorneys:
            if a["id"] == attorney_id:
                a.update(updates)
                return a
        return None

    def list_attorneys(
        self,
        country: str | None = None,
        verified_only: bool = True,
        accepting_only: bool = True,
    ) -> list[dict]:
        attorneys = self._attorneys
        if country:
            attorneys = [a for a in attorneys if a.get("country") == country.upper()]
        if verified_only:
            attorneys = [a for a in attorneys if a.get("verified")]
        if accepting_only:
            attorneys = [a for a in attorneys if a.get("accepting_new_cases") and a.get("active_cases", 0) < a.get("max_active_cases", 0)]
        return attorneys

    # ---------- matching ----------
    def match(
        self,
        visa_type: str,
        country: str,
        applicant_languages: list[str] | None = None,
        red_flag_codes: list[str] | None = None,
        urgency: str = "standard",  # "standard" | "urgent"
        limit: int = 5,
    ) -> dict:
        """Return the top N attorneys for this applicant with explainable scoring."""
        applicant_languages = applicant_languages or ["English"]
        red_flag_codes = red_flag_codes or []
        candidates = self.list_attorneys(country=country)
        scored = []
        for a in candidates:
            breakdown = self._score(a, visa_type, country, applicant_languages, red_flag_codes, urgency)
            scored.append({
                "attorney_id": a["id"],
                "name": a["name"],
                "country": a["country"],
                "jurisdictions": a["jurisdictions"],
                "specializations": a["specializations"],
                "languages": a["languages"],
                "years_experience": a["years_experience"],
                "approval_rate": a["approval_rate"],
                "avg_response_time_hours": a["avg_response_time_hours"],
                "match_score": breakdown["total"],
                "score_breakdown": breakdown["components"],
                "reasons": breakdown["reasons"],
                "capacity_remaining": a.get("max_active_cases", 0) - a.get("active_cases", 0),
            })
        scored.sort(key=lambda r: -r["match_score"])
        top = scored[:limit]

        result = {
            "match_id": str(uuid.uuid4()),
            "visa_type": visa_type,
            "country": country,
            "candidates_evaluated": len(candidates),
            "results": top,
            "matched_at": datetime.utcnow().isoformat(),
        }
        self._match_log.append(result)
        return result

    def match_for_session(self, intake_summary: dict, applicant_languages: list[str] | None = None, limit: int = 5) -> dict:
        """Convenience: build inputs from an IntakeEngine summary."""
        visa_type = intake_summary.get("visa_type", "")
        country = ""
        flags = intake_summary.get("red_flags") or []
        red_flag_codes = [f.get("code") for f in flags if f.get("code")]
        # Country comes from the intake registry — derive via session if available
        # (caller typically passes in the country directly)
        country = intake_summary.get("country") or intake_summary.get("validation", {}).get("country") or "US"
        return self.match(
            visa_type=visa_type,
            country=country,
            applicant_languages=applicant_languages,
            red_flag_codes=red_flag_codes,
            limit=limit,
        )

    def get_match_log(self, limit: int = 50) -> list[dict]:
        return self._match_log[-limit:]

    # ---------- scoring ----------
    @staticmethod
    def _score(
        attorney: dict,
        visa_type: str,
        country: str,
        applicant_languages: list[str],
        red_flag_codes: list[str],
        urgency: str,
    ) -> dict:
        components = {}
        reasons = []

        # Specialization (40)
        if visa_type in attorney.get("specializations", []):
            components["specialization"] = 40
            reasons.append(f"Specializes in {visa_type}")
        elif any(s.startswith(visa_type.split("-")[0]) for s in attorney.get("specializations", [])):
            components["specialization"] = 25
            reasons.append(f"Adjacent specialization in {visa_type.split('-')[0]} family")
        else:
            components["specialization"] = 5

        # Country (20)
        if attorney.get("country", "").upper() == country.upper():
            components["country"] = 20
            reasons.append(f"Licensed in {country}")
        else:
            components["country"] = 0

        # Languages (10)
        att_langs = {l.lower() for l in attorney.get("languages", [])}
        app_langs = {l.lower() for l in applicant_languages}
        overlap = att_langs & app_langs
        if "english" in overlap and len(overlap) > 1:
            components["languages"] = 10
            non_english = sorted(l for l in overlap if l != "english")
            if non_english:
                reasons.append(f"Speaks {', '.join(non_english).title()}")
        elif overlap:
            components["languages"] = 7
        else:
            components["languages"] = 2

        # Capacity (10)
        capacity_left = attorney.get("max_active_cases", 0) - attorney.get("active_cases", 0)
        if capacity_left > 5 and attorney.get("accepting_new_cases"):
            components["capacity"] = 10
            reasons.append(f"{capacity_left} slots open")
        elif capacity_left > 0 and attorney.get("accepting_new_cases"):
            components["capacity"] = 6
            reasons.append("Limited capacity")
        else:
            components["capacity"] = 0

        # Red-flag handling experience (10)
        handled = set(attorney.get("rfe_categories_handled", []))
        flag_set = set(red_flag_codes or [])
        flag_overlap = handled & flag_set
        if flag_overlap:
            components["red_flag_experience"] = 10
            reasons.append(f"Handled similar issues: {', '.join(sorted(flag_overlap))[:80]}")
        elif red_flag_codes:
            components["red_flag_experience"] = 3
        else:
            components["red_flag_experience"] = 7

        # Response time / SLA (5)
        rt = attorney.get("avg_response_time_hours", 24)
        if urgency == "urgent" and rt <= 4:
            components["response_time"] = 5
            reasons.append("Fast response (urgent SLA)")
        elif rt <= 8:
            components["response_time"] = 5
            reasons.append("Fast response")
        elif rt <= 24:
            components["response_time"] = 3
        else:
            components["response_time"] = 1

        # Approval rate signal (5)
        rate = attorney.get("approval_rate", 0)
        if rate >= 0.95:
            components["approval_signal"] = 5
            reasons.append(f"{int(rate*100)}% approval rate")
        elif rate >= 0.90:
            components["approval_signal"] = 4
        elif rate >= 0.85:
            components["approval_signal"] = 3
        else:
            components["approval_signal"] = 1

        total = sum(components.values())
        return {"total": total, "components": components, "reasons": reasons}
