"""Audit trail and ICE audit simulation models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DELETED = "employee_deleted"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    CASE_CREATED = "case_created"
    CASE_STATUS_CHANGED = "case_status_changed"
    COMPLIANCE_CHECK_RUN = "compliance_check_run"
    REPORT_GENERATED = "report_generated"
    I9_COMPLETED = "i9_completed"
    I9_REVERIFIED = "i9_reverified"
    PAF_UPDATED = "paf_updated"
    ALERT_CREATED = "alert_created"
    ALERT_RESOLVED = "alert_resolved"
    USER_LOGIN = "user_login"
    SETTINGS_CHANGED = "settings_changed"


class AuditEntry(BaseModel):
    """A single entry in the audit trail."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction
    actor: str = "system"
    employee_id: str | None = None
    case_id: str | None = None
    document_id: str | None = None
    details: str = ""
    metadata: dict = Field(default_factory=dict)
    ip_address: str = ""


class AuditFinding(str, Enum):
    """Types of findings from an ICE audit simulation."""

    MISSING_I9 = "missing_i9"
    EXPIRED_I9 = "expired_i9"
    INCOMPLETE_SECTION = "incomplete_section"
    LATE_COMPLETION = "late_completion"
    MISSING_DOCUMENT = "missing_document"
    EXPIRED_DOCUMENT = "expired_document"
    UNAUTHORIZED_WORKER = "unauthorized_worker"
    WAGE_VIOLATION = "wage_violation"
    PAF_INCOMPLETE = "paf_incomplete"
    MISSING_LCA_POSTING = "missing_lca_posting"
    DATA_INCONSISTENCY = "data_inconsistency"


class AuditSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


class ICEAuditFinding(BaseModel):
    """A finding from a simulated ICE audit."""

    id: str
    finding_type: AuditFinding
    severity: AuditSeverity
    employee_id: str
    description: str
    regulation_reference: str = ""
    potential_fine: float = 0.0
    remediation_steps: str = ""
    remediation_deadline: str = ""


class ICEAuditReport(BaseModel):
    """Results of a simulated ICE audit."""

    id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_employees_audited: int = 0
    findings: list[ICEAuditFinding] = Field(default_factory=list)
    total_potential_fines: float = 0.0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    observation_count: int = 0
    overall_grade: str = "A"
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
