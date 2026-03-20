"""Public Access File (PAF) management models.

The PAF is required for every H-1B, H-1B1, and E-3 worker.
It must contain: LCA, prevailing wage determination, actual wage documentation,
a memo explaining the wage system, and evidence of LCA posting notice.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class PAFStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    NEEDS_REVIEW = "needs_review"
    EXPIRED = "expired"


class PAFDocumentType(str, Enum):
    LCA_CERTIFIED = "lca_certified"
    PREVAILING_WAGE_DETERMINATION = "prevailing_wage_determination"
    ACTUAL_WAGE_MEMO = "actual_wage_memo"
    WAGE_SYSTEM_EXPLANATION = "wage_system_explanation"
    LCA_POSTING_NOTICE = "lca_posting_notice"
    BENEFITS_SUMMARY = "benefits_summary"
    WORKING_CONDITIONS = "working_conditions"
    CORPORATE_NOTICE = "corporate_notice"
    DISPLACEMENT_SUMMARY = "displacement_summary"
    OTHER_SUPPORTING = "other_supporting"


class PAFDocument(BaseModel):
    """A document within a Public Access File."""

    id: str
    paf_id: str
    document_type: PAFDocumentType
    document_id: str | None = None
    title: str
    description: str = ""
    is_present: bool = False
    date_added: date | None = None
    notes: str = ""


class PublicAccessFile(BaseModel):
    """A Public Access File for an H-1B/H-1B1/E-3 worker."""

    id: str
    employee_id: str
    case_id: str | None = None
    lca_number: str = ""
    job_title: str = ""
    soc_code: str = ""
    worksite_address: str = ""
    wage_rate: float | None = None
    wage_unit: str = "year"
    prevailing_wage: float | None = None
    validity_start: date | None = None
    validity_end: date | None = None
    status: PAFStatus = PAFStatus.INCOMPLETE
    documents: list[PAFDocument] = Field(default_factory=list)
    last_reviewed: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""

    @computed_field
    @property
    def completeness_score(self) -> float:
        """Percentage of required documents present."""
        required = {
            PAFDocumentType.LCA_CERTIFIED,
            PAFDocumentType.PREVAILING_WAGE_DETERMINATION,
            PAFDocumentType.ACTUAL_WAGE_MEMO,
            PAFDocumentType.WAGE_SYSTEM_EXPLANATION,
            PAFDocumentType.LCA_POSTING_NOTICE,
        }
        present = {d.document_type for d in self.documents if d.is_present}
        if not required:
            return 100.0
        return (len(present & required) / len(required)) * 100.0

    @computed_field
    @property
    def missing_documents(self) -> list[PAFDocumentType]:
        required = {
            PAFDocumentType.LCA_CERTIFIED,
            PAFDocumentType.PREVAILING_WAGE_DETERMINATION,
            PAFDocumentType.ACTUAL_WAGE_MEMO,
            PAFDocumentType.WAGE_SYSTEM_EXPLANATION,
            PAFDocumentType.LCA_POSTING_NOTICE,
        }
        present = {d.document_type for d in self.documents if d.is_present}
        return sorted(required - present, key=lambda x: x.value)
