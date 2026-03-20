"""Regulatory intelligence models."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RegulatoryCategory(str, Enum):
    USCIS_POLICY = "uscis_policy"
    DOL_REGULATION = "dol_regulation"
    DOS_UPDATE = "dos_update"
    EXECUTIVE_ORDER = "executive_order"
    COURT_DECISION = "court_decision"
    FEE_CHANGE = "fee_change"
    PROCESSING_TIME = "processing_time"
    FORM_UPDATE = "form_update"
    VISA_BULLETIN = "visa_bulletin"
    ENFORCEMENT_ACTION = "enforcement_action"
    LEGISLATIVE = "legislative"


class ImpactLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class RegulatoryUpdate(BaseModel):
    """A regulatory update or policy change."""

    id: str
    title: str
    summary: str
    category: RegulatoryCategory
    impact_level: ImpactLevel
    source: str = ""
    source_url: str = ""
    published_date: date
    effective_date: date | None = None
    affected_visa_types: list[str] = Field(default_factory=list)
    affected_forms: list[str] = Field(default_factory=list)
    action_required: bool = False
    action_description: str = ""
    full_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingTime(BaseModel):
    """USCIS processing time for a specific form/category."""

    id: str
    form_type: str
    category: str = ""
    service_center: str = ""
    processing_range_min_days: int = 0
    processing_range_max_days: int = 0
    last_updated: date = Field(default_factory=date.today)
    trend: str = ""


class VisaBulletinEntry(BaseModel):
    """A single entry from the monthly visa bulletin."""

    id: str
    bulletin_month: str
    bulletin_year: int
    category: str
    country: str
    final_action_date: str = ""
    dates_for_filing: str = ""
    last_updated: date = Field(default_factory=date.today)


class RegulatoryFeed(BaseModel):
    """Aggregated regulatory intelligence feed."""

    updates: list[RegulatoryUpdate] = Field(default_factory=list)
    processing_times: list[ProcessingTime] = Field(default_factory=list)
    visa_bulletin: list[VisaBulletinEntry] = Field(default_factory=list)
    last_refreshed: datetime = Field(default_factory=datetime.utcnow)
