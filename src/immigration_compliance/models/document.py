"""Document management models."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    PASSPORT = "passport"
    VISA = "visa"
    I94 = "i94"
    EAD_CARD = "ead_card"
    I9_FORM = "i9_form"
    I20 = "i20"
    DS2019 = "ds2019"
    LCA = "lca"
    I129_PETITION = "i129_petition"
    I140_PETITION = "i140_petition"
    I485_APPLICATION = "i485_application"
    APPROVAL_NOTICE = "approval_notice"
    RECEIPT_NOTICE = "receipt_notice"
    RFE_NOTICE = "rfe_notice"
    DENIAL_NOTICE = "denial_notice"
    BIRTH_CERTIFICATE = "birth_certificate"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    DRIVERS_LICENSE = "drivers_license"
    SSN_CARD = "ssn_card"
    PAF_DOCUMENT = "paf_document"
    OFFER_LETTER = "offer_letter"
    PAY_STUB = "pay_stub"
    TAX_RETURN = "tax_return"
    DEGREE_DIPLOMA = "degree_diploma"
    CREDENTIAL_EVALUATION = "credential_evaluation"
    OTHER = "other"


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class Document(BaseModel):
    """A stored document associated with an employee or case."""

    id: str = Field(description="Unique document identifier")
    employee_id: str
    case_id: str | None = None
    category: DocumentCategory
    title: str
    description: str = ""
    file_name: str
    file_size: int = 0
    mime_type: str = "application/pdf"
    status: DocumentStatus = DocumentStatus.ACTIVE
    expiration_date: date | None = None
    issue_date: date | None = None
    issuing_authority: str = ""
    document_number: str = ""
    country: str = ""
    extracted_data: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    uploaded_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        if self.expiration_date is None:
            return False
        return self.expiration_date < date.today()

    def days_until_expiration(self, as_of: date | None = None) -> int | None:
        if self.expiration_date is None:
            return None
        ref = as_of or date.today()
        return (self.expiration_date - ref).days
