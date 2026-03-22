"""Authentication and user models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    APPLICANT = "applicant"
    ATTORNEY = "attorney"
    EMPLOYER = "employer"


class VerificationStatus(str, Enum):
    """Attorney verification lifecycle."""
    NOT_APPLICABLE = "not_applicable"  # Non-attorney users
    PENDING = "pending"               # Signed up, awaiting document submission
    SUBMITTED = "submitted"           # Documents uploaded, awaiting review
    VERIFIED = "verified"             # Credentials confirmed — full platform access
    REJECTED = "rejected"             # Credentials could not be verified
    SUSPENDED = "suspended"           # Previously verified, now suspended


# Jurisdictions we verify against (bar association registries)
SUPPORTED_JURISDICTIONS = {
    "US": "United States",
    "UK": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "DE": "Germany",
    "NZ": "New Zealand",
    "IE": "Ireland",
    "FR": "France",
    "NL": "Netherlands",
    "JP": "Japan",
    "SG": "Singapore",
    "AE": "UAE",
}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    role: UserRole = UserRole.APPLICANT
    # Attorney-specific fields — required when role=attorney
    bar_number: str = ""
    jurisdiction: str = ""
    years_experience: int = 0
    specializations: str = ""
    firm_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    verification_status: VerificationStatus = VerificationStatus.NOT_APPLICABLE
    bar_number: str = ""
    jurisdiction: str = ""
    years_experience: int = 0
    specializations: str = ""
    firm_name: str = ""


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: str
    role: UserRole


class VerificationDocUpload(BaseModel):
    """Documents an attorney must submit for verification."""
    bar_certificate_filename: str = ""
    government_id_filename: str = ""
    proof_of_insurance_filename: str = ""
    notes: str = ""


class VerificationDecision(BaseModel):
    """Admin decision on an attorney's verification."""
    status: VerificationStatus
    reason: str = ""
