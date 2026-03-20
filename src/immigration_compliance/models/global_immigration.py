"""Multi-country global immigration support models."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class CountryRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"


class WorkPermitStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    RENEWAL_REQUIRED = "renewal_required"
    NOT_REQUIRED = "not_required"


class Country(BaseModel):
    """Immigration profile for a country."""

    code: str = Field(description="ISO 3166-1 alpha-2 country code")
    name: str
    risk_level: CountryRiskLevel = CountryRiskLevel.MEDIUM
    requires_work_permit: bool = True
    requires_visa: bool = True
    max_business_travel_days: int = 90
    tax_threshold_days: int = 183
    common_permit_types: list[str] = Field(default_factory=list)
    notes: str = ""


class GlobalAssignment(BaseModel):
    """An employee's international assignment or work permit."""

    id: str
    employee_id: str
    country_code: str
    country_name: str
    assignment_type: str = ""
    permit_type: str = ""
    permit_number: str = ""
    permit_status: WorkPermitStatus = WorkPermitStatus.PENDING
    start_date: date | None = None
    end_date: date | None = None
    days_in_country: int = 0
    max_days_allowed: int = 0
    tax_implications: str = ""
    sponsoring_entity: str = ""
    local_address: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def days_remaining(self) -> int | None:
        if self.end_date is None:
            return None
        return (self.end_date - date.today()).days

    @property
    def is_over_tax_threshold(self) -> bool:
        return self.days_in_country >= 183

    @property
    def travel_day_utilization(self) -> float:
        if self.max_days_allowed <= 0:
            return 0.0
        return (self.days_in_country / self.max_days_allowed) * 100.0


class TravelEntry(BaseModel):
    """A record of business travel for day-count tracking."""

    id: str
    employee_id: str
    country_code: str
    country_name: str
    entry_date: date
    exit_date: date | None = None
    purpose: str = ""
    days_counted: int = 0


class GlobalComplianceSummary(BaseModel):
    """Summary of an employee's global immigration compliance."""

    employee_id: str
    assignments: list[GlobalAssignment] = Field(default_factory=list)
    travel_history: list[TravelEntry] = Field(default_factory=list)
    countries_with_risk: list[str] = Field(default_factory=list)
    total_countries_active: int = 0
    tax_risk_countries: list[str] = Field(default_factory=list)
    permit_expiring_soon: list[GlobalAssignment] = Field(default_factory=list)
