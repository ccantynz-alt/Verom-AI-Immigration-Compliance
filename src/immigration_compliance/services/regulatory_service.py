"""Regulatory intelligence service with built-in reference data."""

from __future__ import annotations

import uuid
from datetime import date

from immigration_compliance.models.regulatory import (
    ImpactLevel,
    ProcessingTime,
    RegulatoryCategory,
    RegulatoryFeed,
    RegulatoryUpdate,
    VisaBulletinEntry,
)


# Built-in regulatory reference data (would be API-fed in production)
_BUILTIN_UPDATES: list[dict] = [
    {
        "title": "USCIS Fee Schedule Update - FY2025",
        "summary": "USCIS has implemented a new fee schedule effective April 1, 2024. H-1B registration fee increased to $215. Premium processing fees adjusted across categories.",
        "category": RegulatoryCategory.FEE_CHANGE,
        "impact_level": ImpactLevel.HIGH,
        "source": "USCIS",
        "published_date": date(2024, 1, 31),
        "effective_date": date(2024, 4, 1),
        "affected_visa_types": ["H-1B", "L-1", "O-1", "EB-1", "EB-2", "EB-3"],
        "action_required": True,
        "action_description": "Update budget forecasts to reflect new filing fees.",
    },
    {
        "title": "H-1B Registration Modernization",
        "summary": "USCIS implemented beneficiary-centric H-1B registration to reduce duplicate registrations. Each beneficiary can only be registered once per fiscal year regardless of number of petitioners.",
        "category": RegulatoryCategory.USCIS_POLICY,
        "impact_level": ImpactLevel.HIGH,
        "source": "USCIS",
        "published_date": date(2024, 2, 2),
        "effective_date": date(2025, 3, 1),
        "affected_visa_types": ["H-1B"],
        "action_required": True,
        "action_description": "Update H-1B registration strategy. Ensure valid passport/travel doc for each beneficiary.",
    },
    {
        "title": "I-9 Form Update - Revised Edition Required",
        "summary": "Employers must use the latest edition of Form I-9 (Rev. 08/01/2023) for all new hires and reverifications. Previous editions are no longer valid.",
        "category": RegulatoryCategory.FORM_UPDATE,
        "impact_level": ImpactLevel.MEDIUM,
        "source": "USCIS",
        "published_date": date(2023, 8, 1),
        "effective_date": date(2023, 11, 1),
        "affected_forms": ["I-9"],
        "action_required": True,
        "action_description": "Ensure all new I-9 completions use the current form edition.",
    },
    {
        "title": "DOL Prevailing Wage Rule Changes",
        "summary": "The Department of Labor has proposed updates to the prevailing wage methodology that would increase required wage levels for H-1B and PERM applications.",
        "category": RegulatoryCategory.DOL_REGULATION,
        "impact_level": ImpactLevel.HIGH,
        "source": "DOL",
        "published_date": date(2024, 6, 15),
        "affected_visa_types": ["H-1B", "H-1B1", "E-3"],
        "action_required": True,
        "action_description": "Review current compensation against proposed new wage levels. Budget for potential wage adjustments.",
    },
    {
        "title": "Premium Processing Expansion",
        "summary": "USCIS expanded premium processing availability to additional form types including I-140 for all categories and I-539 for certain change-of-status requests.",
        "category": RegulatoryCategory.USCIS_POLICY,
        "impact_level": ImpactLevel.MEDIUM,
        "source": "USCIS",
        "published_date": date(2024, 4, 1),
        "affected_visa_types": ["EB-1", "EB-2", "EB-3"],
        "affected_forms": ["I-140", "I-539"],
        "action_required": False,
        "action_description": "",
    },
    {
        "title": "ICE Worksite Enforcement Increase",
        "summary": "Immigration and Customs Enforcement has announced increased worksite enforcement operations targeting I-9 compliance. Employers should conduct self-audits.",
        "category": RegulatoryCategory.ENFORCEMENT_ACTION,
        "impact_level": ImpactLevel.HIGH,
        "source": "ICE / DHS",
        "published_date": date(2025, 1, 20),
        "action_required": True,
        "action_description": "Conduct internal I-9 self-audit immediately. Ensure all records are complete and current.",
    },
]

_BUILTIN_PROCESSING_TIMES: list[dict] = [
    {"form_type": "I-129", "category": "H-1B", "service_center": "California", "processing_range_min_days": 30, "processing_range_max_days": 180, "trend": "increasing"},
    {"form_type": "I-129", "category": "H-1B", "service_center": "Vermont", "processing_range_min_days": 30, "processing_range_max_days": 210, "trend": "stable"},
    {"form_type": "I-129", "category": "L-1A", "service_center": "California", "processing_range_min_days": 30, "processing_range_max_days": 150, "trend": "stable"},
    {"form_type": "I-129", "category": "L-1B", "service_center": "California", "processing_range_min_days": 30, "processing_range_max_days": 180, "trend": "increasing"},
    {"form_type": "I-129", "category": "O-1", "service_center": "California", "processing_range_min_days": 30, "processing_range_max_days": 120, "trend": "stable"},
    {"form_type": "I-129", "category": "TN", "service_center": "California", "processing_range_min_days": 15, "processing_range_max_days": 90, "trend": "decreasing"},
    {"form_type": "I-140", "category": "EB-1", "service_center": "Texas", "processing_range_min_days": 120, "processing_range_max_days": 365, "trend": "stable"},
    {"form_type": "I-140", "category": "EB-2", "service_center": "Texas", "processing_range_min_days": 240, "processing_range_max_days": 545, "trend": "increasing"},
    {"form_type": "I-140", "category": "EB-3", "service_center": "Texas", "processing_range_min_days": 240, "processing_range_max_days": 545, "trend": "increasing"},
    {"form_type": "I-765", "category": "EAD", "service_center": "National Benefits Center", "processing_range_min_days": 120, "processing_range_max_days": 300, "trend": "decreasing"},
    {"form_type": "I-485", "category": "Adjustment of Status", "service_center": "National Benefits Center", "processing_range_min_days": 365, "processing_range_max_days": 730, "trend": "stable"},
    {"form_type": "PERM", "category": "Labor Certification", "service_center": "DOL Atlanta", "processing_range_min_days": 270, "processing_range_max_days": 450, "trend": "increasing"},
]

_BUILTIN_VISA_BULLETIN: list[dict] = [
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-1", "country": "All Chargeability", "final_action_date": "Current", "dates_for_filing": "Current"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-1", "country": "China", "final_action_date": "01FEB23", "dates_for_filing": "01JUN23"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-1", "country": "India", "final_action_date": "01FEB22", "dates_for_filing": "01JUN23"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-2", "country": "All Chargeability", "final_action_date": "Current", "dates_for_filing": "Current"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-2", "country": "China", "final_action_date": "15APR20", "dates_for_filing": "01MAR21"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-2", "country": "India", "final_action_date": "15JAN13", "dates_for_filing": "01DEC14"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-3", "country": "All Chargeability", "final_action_date": "01SEP22", "dates_for_filing": "01JAN23"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-3", "country": "China", "final_action_date": "22JUN20", "dates_for_filing": "01NOV21"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-3", "country": "India", "final_action_date": "01JUN12", "dates_for_filing": "15MAR13"},
    {"bulletin_month": "March", "bulletin_year": 2026, "category": "EB-3", "country": "Philippines", "final_action_date": "01MAR22", "dates_for_filing": "Current"},
]


class RegulatoryService:
    """Provides regulatory intelligence and reference data."""

    def __init__(self) -> None:
        self._custom_updates: list[RegulatoryUpdate] = []

    def get_feed(self) -> RegulatoryFeed:
        updates = self._get_all_updates()
        processing_times = self._get_processing_times()
        visa_bulletin = self._get_visa_bulletin()
        return RegulatoryFeed(
            updates=updates,
            processing_times=processing_times,
            visa_bulletin=visa_bulletin,
        )

    def get_updates(
        self,
        category: RegulatoryCategory | None = None,
        impact_level: ImpactLevel | None = None,
        action_required: bool | None = None,
    ) -> list[RegulatoryUpdate]:
        updates = self._get_all_updates()
        if category:
            updates = [u for u in updates if u.category == category]
        if impact_level:
            updates = [u for u in updates if u.impact_level == impact_level]
        if action_required is not None:
            updates = [u for u in updates if u.action_required == action_required]
        return updates

    def add_update(self, update: RegulatoryUpdate) -> RegulatoryUpdate:
        self._custom_updates.append(update)
        return update

    def get_processing_times(self, form_type: str | None = None) -> list[ProcessingTime]:
        times = self._get_processing_times()
        if form_type:
            times = [t for t in times if t.form_type == form_type]
        return times

    def get_visa_bulletin(self, category: str | None = None, country: str | None = None) -> list[VisaBulletinEntry]:
        entries = self._get_visa_bulletin()
        if category:
            entries = [e for e in entries if e.category == category]
        if country:
            entries = [e for e in entries if e.country.lower() == country.lower()]
        return entries

    def _get_all_updates(self) -> list[RegulatoryUpdate]:
        builtin = [
            RegulatoryUpdate(id=str(uuid.uuid4()), **data)
            for data in _BUILTIN_UPDATES
        ]
        return sorted(
            builtin + self._custom_updates,
            key=lambda u: u.published_date,
            reverse=True,
        )

    def _get_processing_times(self) -> list[ProcessingTime]:
        return [
            ProcessingTime(id=str(uuid.uuid4()), **data)
            for data in _BUILTIN_PROCESSING_TIMES
        ]

    def _get_visa_bulletin(self) -> list[VisaBulletinEntry]:
        return [
            VisaBulletinEntry(id=str(uuid.uuid4()), **data)
            for data in _BUILTIN_VISA_BULLETIN
        ]
