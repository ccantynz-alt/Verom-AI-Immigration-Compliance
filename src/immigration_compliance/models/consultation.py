"""Video consultation and scheduling models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConsultationStatus(str, Enum):
    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ConsultationType(str, Enum):
    INITIAL = "initial_consultation"
    CASE_REVIEW = "case_review"
    DOCUMENT_REVIEW = "document_review"
    INTERVIEW_PREP = "interview_prep"
    STATUS_UPDATE = "status_update"
    EMERGENCY = "emergency"


class Consultation(BaseModel):
    id: str = ""
    applicant_id: str
    attorney_id: str
    consultation_type: ConsultationType = ConsultationType.INITIAL
    status: ConsultationStatus = ConsultationStatus.REQUESTED
    scheduled_at: str = ""  # ISO datetime
    duration_minutes: int = 30
    room_id: str = ""
    room_url: str = ""  # Join URL for video
    notes: str = ""
    case_id: str = ""  # Linked case, if any
    created_at: str = ""


class ConsultationRequest(BaseModel):
    attorney_id: str
    consultation_type: ConsultationType = ConsultationType.INITIAL
    preferred_date: str = ""  # ISO date
    preferred_time: str = ""  # HH:MM
    duration_minutes: int = Field(default=30, ge=15, le=120)
    notes: str = ""
    case_id: str = ""


class ScheduleSlot(BaseModel):
    date: str  # ISO date
    time: str  # HH:MM
    available: bool = True


class AvailabilityUpdate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)  # 0=Monday, 6=Sunday
    start_time: str = "09:00"
    end_time: str = "17:00"
    available: bool = True


# --- Interview Prep ---

class InterviewType(str, Enum):
    USCIS_MARRIAGE = "uscis_marriage_interview"
    USCIS_NATURALIZATION = "uscis_naturalization"
    USCIS_ASYLUM = "uscis_asylum"
    UK_HOME_OFFICE = "uk_home_office"
    CANADA_IRCC = "canada_ircc"
    CONSULAR = "consular_interview"
    EMPLOYMENT_BASED = "employment_based"


class MockInterviewQuestion(BaseModel):
    question: str
    category: str  # e.g. "personal", "relationship", "employment", "travel"
    tip: str = ""
    follow_up: str = ""


class MockInterviewSession(BaseModel):
    id: str = ""
    user_id: str
    interview_type: InterviewType
    questions: list[MockInterviewQuestion] = []
    started_at: str = ""
    completed: bool = False
    score: int = 0  # 0-100 readiness score


# --- Document Vault ---

class VaultDocument(BaseModel):
    id: str = ""
    user_id: str
    filename: str
    document_type: str  # passport, visa, i94, ead, approval_notice, etc.
    country: str = ""
    expiration_date: str = ""  # ISO date, empty if no expiry
    uploaded_at: str = ""
    notes: str = ""


class ExpirationAlert(BaseModel):
    document_id: str
    document_type: str
    filename: str
    expiration_date: str
    days_remaining: int
    urgency: str  # "expired", "critical", "warning", "info"


# --- Travel Advisory ---

class TravelAdvisoryRequest(BaseModel):
    destination_country: str
    departure_date: str = ""
    return_date: str = ""


class TravelAdvisory(BaseModel):
    can_travel: bool
    risk_level: str  # "safe", "caution", "risky", "blocked"
    warnings: list[str] = []
    recommendations: list[str] = []
    pending_cases_impact: list[str] = []


# --- Receipt Tracker ---

class ReceiptTracker(BaseModel):
    id: str = ""
    user_id: str
    receipt_number: str  # e.g. EAC-XX-XXX-XXXXX, IOE-XXXX-XXXXXX
    form_type: str = ""  # I-130, I-485, I-765, etc.
    case_status: str = ""
    last_checked: str = ""
    last_updated: str = ""
    status_history: list[dict] = []
    alerts_enabled: bool = True
