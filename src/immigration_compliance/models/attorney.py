"""Attorney portal data models — profiles, intake, cases, forms, deadlines, messaging, and more."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class FieldType(str, Enum):
    TEXT = "text"
    SELECT = "select"
    MULTISELECT = "multiselect"
    DATE = "date"
    FILE = "file"
    PHONE = "phone"
    EMAIL = "email"
    NUMBER = "number"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    COUNTRY = "country"


class TimelineEventType(str, Enum):
    CREATED = "created"
    FILED = "filed"
    RFE_RECEIVED = "rfe_received"
    RFE_RESPONDED = "rfe_responded"
    APPROVED = "approved"
    DENIED = "denied"
    STATUS_CHANGE = "status_change"
    NOTE_ADDED = "note_added"
    DOCUMENT_UPLOADED = "document_uploaded"
    DEADLINE_APPROACHING = "deadline_approaching"
    PAYMENT_RECEIVED = "payment_received"


class RFEResponseStatus(str, Enum):
    PENDING = "pending"
    DRAFTING = "drafting"
    REVIEWED = "reviewed"
    SUBMITTED = "submitted"


class FormStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    FINAL = "final"
    FILED = "filed"


class DeadlineType(str, Enum):
    FILING_WINDOW = "filing_window"
    RFE_RESPONSE = "rfe_response"
    RENEWAL = "renewal"
    HEARING = "hearing"
    BIOMETRICS = "biometrics"
    INTERVIEW = "interview"
    CUSTOM = "custom"


class DeadlineStatus(str, Enum):
    UPCOMING = "upcoming"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"
    COMPLETED = "completed"


class ReportType(str, Enum):
    CASELOAD = "caseload"
    REVENUE = "revenue"
    PRODUCTIVITY = "productivity"
    SUCCESS_RATE = "success_rate"


class MailSender(str, Enum):
    USCIS = "USCIS"
    DOL = "DOL"
    EOIR = "EOIR"
    DOS = "DOS"
    COURT = "court"


class MailStatus(str, Enum):
    EXPECTED = "expected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    OVERDUE = "overdue"


class ScanType(str, Enum):
    PASSPORT = "passport"
    USCIS_NOTICE = "uscis_notice"
    I94 = "i94"
    APPROVAL_NOTICE = "approval_notice"
    ID = "id"
    OTHER = "other"


class ImportJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Attorney Profile
# ---------------------------------------------------------------------------

class AttorneyProfile(BaseModel):
    """Full attorney profile with credentials, capacity, and performance metrics."""

    id: str = Field(description="Unique attorney identifier (matches user_id)")
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    firm_name: str = ""
    bio: str = ""
    years_experience: int = 0
    website: str = ""
    photo_url: str = ""

    # Jurisdiction & specialization
    jurisdictions: list[str] = Field(default_factory=list, description="Licensed jurisdictions, e.g. ['US-CA','US-NY','UK']")
    specializations: list[str] = Field(default_factory=list, description="Visa types / areas, e.g. ['H-1B','EB-5','Family']")
    languages: list[str] = Field(default_factory=lambda: ["English"])
    bar_numbers: dict[str, str] = Field(default_factory=dict, description="State/country → bar number mapping")

    # Capacity
    active_cases_count: int = 0
    max_cases: int = 50
    accepting_new_cases: bool = True

    # Verification
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    trust_badge: bool = False
    verified_at: datetime | None = None

    # Performance
    performance_score: float = 0.0
    response_time_avg: float = 0.0  # hours
    cases_completed: int = 0
    approval_rate: float = 0.0
    total_reviews: int = 0
    average_rating: float = 0.0

    # Fees (attorney-set, platform never dictates)
    fee_schedule: dict[str, float] = Field(default_factory=dict, description="Visa type → attorney fee")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Client Intake
# ---------------------------------------------------------------------------

class IntakeQuestion(BaseModel):
    """A single question in a dynamic intake form."""

    id: str = ""
    question_text: str
    field_type: FieldType = FieldType.TEXT
    options: list[str] = Field(default_factory=list)
    required: bool = True
    conditional_on: dict[str, Any] = Field(default_factory=dict, description="Show only if another field == value")
    visa_types: list[str] = Field(default_factory=list, description="Applicable visa types; empty = all")
    language: str = "en"
    help_text: str = ""
    section: str = ""
    order: int = 0


class ClientIntakeForm(BaseModel):
    """A dynamically generated intake form tailored to visa type and country."""

    id: str = Field(description="Unique form identifier")
    attorney_id: str = ""
    visa_type: str
    country: str
    language: str = "en"
    title: str = ""
    description: str = ""
    sections: list[str] = Field(default_factory=list)
    questions: list[IntakeQuestion] = Field(default_factory=list)
    status: str = "active"  # active / completed / archived
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntakeResponse(BaseModel):
    """A completed intake form submission."""

    id: str = Field(description="Unique response identifier")
    form_id: str
    applicant_id: str = ""
    applicant_name: str = ""
    applicant_email: str = ""
    responses: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    translated_responses: dict[str, Any] = Field(default_factory=dict, description="Auto-translated to English")
    documents_uploaded: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    status: str = "submitted"  # submitted / reviewed / converted_to_case
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Case Notes & Timeline
# ---------------------------------------------------------------------------

class CaseNote(BaseModel):
    """A note attached to a case — internal or client-visible."""

    id: str = Field(description="Unique note identifier")
    case_id: str
    author_id: str
    author_name: str = ""
    content: str
    is_internal: bool = True
    attachments: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TimelineEvent(BaseModel):
    """A single event in a case timeline."""

    id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: TimelineEventType
    description: str
    actor_id: str = ""
    actor_name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseTimeline(BaseModel):
    """Ordered timeline of all events on a case."""

    id: str = ""
    case_id: str
    events: list[TimelineEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RFE Tracking
# ---------------------------------------------------------------------------

class RFETracker(BaseModel):
    """Tracks a Request for Evidence and its response lifecycle."""

    id: str = Field(description="Unique RFE tracker identifier")
    case_id: str
    receipt_number: str = ""
    received_date: date
    due_date: date
    category: str = ""
    description: str = ""
    response_status: RFEResponseStatus = RFEResponseStatus.PENDING
    ai_draft: str = ""
    final_response: str = ""
    evidence_list: list[str] = Field(default_factory=list)
    assigned_to: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Government Forms Engine
# ---------------------------------------------------------------------------

class FormField(BaseModel):
    """A field definition within a government form."""

    field_name: str
    field_type: str = "text"
    label: str = ""
    required: bool = False
    options: list[str] = Field(default_factory=list)
    page_number: int = 1
    section: str = ""
    max_length: int | None = None
    help_text: str = ""


class GovernmentForm(BaseModel):
    """A government immigration form template."""

    id: str = Field(description="Unique form template identifier")
    form_number: str = Field(description="Official form number, e.g. I-130")
    title: str
    category: str = ""
    agency: str = ""
    country: str = "US"
    url: str = ""
    fields: list[FormField] = Field(default_factory=list)
    version: str = ""
    last_updated: date | None = None
    countries: list[str] = Field(default_factory=lambda: ["US"])
    filing_fee: float = 0.0
    estimated_processing_days: int = 0
    instructions_url: str = ""


class FilledForm(BaseModel):
    """A government form populated with case/client data."""

    id: str = Field(description="Unique filled form identifier")
    form_id: str
    form_number: str = ""
    case_id: str
    field_values: dict[str, Any] = Field(default_factory=dict)
    auto_populated_fields: list[str] = Field(default_factory=list)
    manually_edited_fields: list[str] = Field(default_factory=list)
    status: FormStatus = FormStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Deadline Management
# ---------------------------------------------------------------------------

class DeadlineEntry(BaseModel):
    """A tracked deadline for a case."""

    id: str = Field(description="Unique deadline identifier")
    case_id: str
    title: str
    due_date: date
    type: DeadlineType = DeadlineType.CUSTOM
    status: DeadlineStatus = DeadlineStatus.UPCOMING
    escalation_level: int = Field(default=0, ge=0, le=3)
    assigned_to: str = ""
    auto_calculated: bool = False
    notes: str = ""
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CalendarEvent(BaseModel):
    """A calendar event for sync with external calendars."""

    id: str = Field(description="Unique event identifier")
    title: str
    start: datetime
    end: datetime
    type: str = "deadline"
    case_id: str = ""
    attendees: list[str] = Field(default_factory=list)
    external_calendar_id: str = ""
    sync_status: str = "pending"  # pending / synced / error
    location: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Messaging & Communication
# ---------------------------------------------------------------------------

class ClientMessage(BaseModel):
    """A message between attorney and client."""

    id: str = Field(description="Unique message identifier")
    case_id: str
    sender_id: str
    recipient_id: str
    sender_name: str = ""
    content: str
    original_language: str = "en"
    translated_content: str = ""
    read: bool = False
    attachments: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageThread(BaseModel):
    """A conversation thread on a case."""

    id: str = Field(description="Unique thread identifier")
    case_id: str
    participants: list[str] = Field(default_factory=list)
    messages: list[ClientMessage] = Field(default_factory=list)
    last_message_at: datetime | None = None
    unread_count: int = 0


# ---------------------------------------------------------------------------
# Reports & Analytics
# ---------------------------------------------------------------------------

class AttorneyReport(BaseModel):
    """A generated analytics report for an attorney."""

    id: str = ""
    type: ReportType
    attorney_id: str = ""
    date_range_start: date | None = None
    date_range_end: date | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str = ""


# ---------------------------------------------------------------------------
# Physical Mail Tracking
# ---------------------------------------------------------------------------

class PhysicalMailTracker(BaseModel):
    """Tracks expected physical mail from government agencies."""

    id: str = Field(description="Unique tracker identifier")
    case_id: str
    expected_from: MailSender
    document_type: str = ""
    description: str = ""
    sent_date: date | None = None
    expected_by: date | None = None
    received_date: date | None = None
    status: MailStatus = MailStatus.EXPECTED
    receipt_number: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Document Scanning / OCR
# ---------------------------------------------------------------------------

class ScannedDocument(BaseModel):
    """A scanned physical document with OCR extraction results."""

    id: str = Field(description="Unique scan identifier")
    case_id: str
    scan_type: ScanType
    file_name: str = ""
    raw_image_data: str = ""  # base64 or path reference
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    verified: bool = False
    verified_by: str = ""
    verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Bulk Import
# ---------------------------------------------------------------------------

class ImportError(BaseModel):
    """An error encountered during bulk import."""

    row: int = 0
    field: str = ""
    message: str = ""


class ImportedCase(BaseModel):
    """A single case record from a bulk import."""

    case_data: dict[str, Any] = Field(default_factory=dict)
    client_data: dict[str, Any] = Field(default_factory=dict)
    document_list: list[str] = Field(default_factory=list)
    import_status: str = "pending"  # pending / imported / error
    error_message: str = ""


class BulkImportJob(BaseModel):
    """Tracks a bulk case/client import job."""

    id: str = Field(description="Unique import job identifier")
    attorney_id: str
    file_name: str
    file_type: str = "csv"
    status: ImportJobStatus = ImportJobStatus.PENDING
    total_records: int = 0
    processed_records: int = 0
    errors: list[ImportError] = Field(default_factory=list)
    imported_cases: list[ImportedCase] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
