"""Global immigration and travel tracking service."""

from __future__ import annotations

import uuid
from datetime import date

from immigration_compliance.models.global_immigration import (
    Country,
    CountryRiskLevel,
    GlobalAssignment,
    GlobalComplianceSummary,
    TravelEntry,
    WorkPermitStatus,
)


# Built-in country profiles
_COUNTRIES: dict[str, dict] = {
    "US": {"name": "United States", "risk_level": "low", "max_business_travel_days": 365, "tax_threshold_days": 183, "common_permit_types": ["H-1B", "L-1", "O-1", "TN", "E-2"]},
    "GB": {"name": "United Kingdom", "risk_level": "low", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Skilled Worker", "Global Talent", "ICT"]},
    "CA": {"name": "Canada", "risk_level": "low", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Work Permit", "LMIA", "ICT"]},
    "DE": {"name": "Germany", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["EU Blue Card", "ICT", "Work Permit"]},
    "FR": {"name": "France", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Talent Passport", "ICT", "Work Permit"]},
    "JP": {"name": "Japan", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Engineer/Specialist", "Intra-company Transfer", "HSP"]},
    "AU": {"name": "Australia", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["TSS 482", "ENS 186", "Business 408"]},
    "SG": {"name": "Singapore", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Employment Pass", "S Pass", "EntrePass"]},
    "IN": {"name": "India", "risk_level": "medium", "max_business_travel_days": 180, "tax_threshold_days": 182, "common_permit_types": ["Employment Visa", "Business Visa"]},
    "CN": {"name": "China", "risk_level": "medium", "max_business_travel_days": 30, "tax_threshold_days": 183, "common_permit_types": ["Z Visa / Work Permit", "R Visa"]},
    "BR": {"name": "Brazil", "risk_level": "medium", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Work Visa (VITEM V)", "Technical Visa"]},
    "AE": {"name": "United Arab Emirates", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Employment Visa", "Golden Visa"]},
    "NL": {"name": "Netherlands", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Highly Skilled Migrant", "EU Blue Card", "ICT"]},
    "IE": {"name": "Ireland", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Critical Skills", "General Employment", "ICT"]},
    "KR": {"name": "South Korea", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["E-7", "D-7", "D-8"]},
    "MX": {"name": "Mexico", "risk_level": "medium", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Temporary Resident Work Visa"]},
    "IL": {"name": "Israel", "risk_level": "medium", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["B-1 Work Visa", "Expert Visa"]},
    "CH": {"name": "Switzerland", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["L Permit", "B Permit"]},
}


class GlobalImmigrationService:
    """Manages global assignments, travel tracking, and multi-country compliance."""

    def __init__(self) -> None:
        self._assignments: dict[str, GlobalAssignment] = {}
        self._travel: dict[str, TravelEntry] = {}

    def get_countries(self) -> list[Country]:
        return [
            Country(
                code=code,
                name=data["name"],
                risk_level=CountryRiskLevel(data["risk_level"]),
                max_business_travel_days=data["max_business_travel_days"],
                tax_threshold_days=data["tax_threshold_days"],
                common_permit_types=data["common_permit_types"],
            )
            for code, data in sorted(_COUNTRIES.items(), key=lambda x: x[1]["name"])
        ]

    def get_country(self, code: str) -> Country | None:
        data = _COUNTRIES.get(code.upper())
        if data is None:
            return None
        return Country(
            code=code.upper(),
            name=data["name"],
            risk_level=CountryRiskLevel(data["risk_level"]),
            max_business_travel_days=data["max_business_travel_days"],
            tax_threshold_days=data["tax_threshold_days"],
            common_permit_types=data["common_permit_types"],
        )

    # Assignments
    def create_assignment(self, assignment: GlobalAssignment) -> GlobalAssignment:
        self._assignments[assignment.id] = assignment
        return assignment

    def get_assignments(self, employee_id: str | None = None) -> list[GlobalAssignment]:
        assignments = list(self._assignments.values())
        if employee_id:
            assignments = [a for a in assignments if a.employee_id == employee_id]
        return assignments

    def delete_assignment(self, assignment_id: str) -> bool:
        return self._assignments.pop(assignment_id, None) is not None

    # Travel
    def add_travel(self, entry: TravelEntry) -> TravelEntry:
        if entry.entry_date and entry.exit_date:
            entry.days_counted = (entry.exit_date - entry.entry_date).days + 1
        self._travel[entry.id] = entry
        return entry

    def get_travel(self, employee_id: str | None = None) -> list[TravelEntry]:
        entries = list(self._travel.values())
        if employee_id:
            entries = [t for t in entries if t.employee_id == employee_id]
        return sorted(entries, key=lambda t: t.entry_date, reverse=True)

    def delete_travel(self, entry_id: str) -> bool:
        return self._travel.pop(entry_id, None) is not None

    # Compliance summary
    def get_compliance_summary(self, employee_id: str) -> GlobalComplianceSummary:
        assignments = self.get_assignments(employee_id)
        travel = self.get_travel(employee_id)

        # Aggregate days by country
        country_days: dict[str, int] = {}
        for t in travel:
            country_days[t.country_code] = country_days.get(t.country_code, 0) + t.days_counted

        risk_countries = []
        tax_risk = []
        expiring = []

        for a in assignments:
            country = _COUNTRIES.get(a.country_code, {})
            if a.days_remaining is not None and 0 < a.days_remaining <= 90:
                expiring.append(a)
            total_days = country_days.get(a.country_code, 0) + a.days_in_country
            threshold = country.get("tax_threshold_days", 183)
            if total_days >= threshold:
                tax_risk.append(a.country_name)
            max_days = country.get("max_business_travel_days", 90)
            if total_days > max_days:
                risk_countries.append(a.country_name)

        return GlobalComplianceSummary(
            employee_id=employee_id,
            assignments=assignments,
            travel_history=travel,
            countries_with_risk=risk_countries,
            total_countries_active=len({a.country_code for a in assignments}),
            tax_risk_countries=tax_risk,
            permit_expiring_soon=expiring,
        )
