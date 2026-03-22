"""Authentication service — user management, password hashing, JWT tokens."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from immigration_compliance.models.auth import (
    SUPPORTED_JURISDICTIONS,
    TokenData,
    UserCreate,
    UserOut,
    UserRole,
    VerificationStatus,
)

# JWT configuration — use env var in production, fallback for dev
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "verom-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def _hash_password(password: str) -> str:
    """Hash a password with a random salt using SHA-256. Production should use bcrypt."""
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash."""
    salt, expected = stored.split(":", 1)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(actual, expected)


def _validate_bar_number(bar_number: str) -> bool:
    """Basic bar number format validation. Must be alphanumeric, 3-20 chars."""
    return bool(re.match(r'^[A-Za-z0-9\-]{3,20}$', bar_number))


class AuthService:
    """In-memory user store with password hashing and JWT tokens."""

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}  # user_id -> user data (with hashed password)
        self._email_index: dict[str, str] = {}  # email -> user_id
        self._verification_docs: dict[str, dict] = {}  # user_id -> uploaded doc metadata

    def create_user(self, data: UserCreate) -> UserOut:
        email_lower = data.email.lower()
        if email_lower in self._email_index:
            raise ValueError("An account with this email already exists")

        # Attorney-specific validation
        if data.role == UserRole.ATTORNEY:
            if not data.bar_number or not data.bar_number.strip():
                raise ValueError("Bar number is required for attorney registration")
            if not _validate_bar_number(data.bar_number.strip()):
                raise ValueError("Bar number must be 3-20 alphanumeric characters")
            if not data.jurisdiction or data.jurisdiction not in SUPPORTED_JURISDICTIONS:
                raise ValueError(
                    f"Valid jurisdiction is required. Supported: {', '.join(SUPPORTED_JURISDICTIONS.keys())}"
                )
            if not data.specializations or not data.specializations.strip():
                raise ValueError("At least one specialization is required for attorney registration")

        user_id = str(uuid.uuid4())
        hashed = _hash_password(data.password)

        # Attorneys start as "pending" until verified; others are "not_applicable"
        verification = (
            VerificationStatus.PENDING
            if data.role == UserRole.ATTORNEY
            else VerificationStatus.NOT_APPLICABLE
        )

        user_record = {
            "id": user_id,
            "email": email_lower,
            "hashed_password": hashed,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "role": data.role,
            "verification_status": verification,
            "bar_number": data.bar_number.strip(),
            "jurisdiction": data.jurisdiction,
            "years_experience": data.years_experience,
            "specializations": data.specializations,
            "firm_name": data.firm_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._users[user_id] = user_record
        self._email_index[email_lower] = user_id

        return self._to_user_out(user_record)

    def authenticate(self, email: str, password: str) -> UserOut | None:
        email_lower = email.lower()
        user_id = self._email_index.get(email_lower)
        if user_id is None:
            return None
        user = self._users[user_id]
        if not _verify_password(password, user["hashed_password"]):
            return None
        return self._to_user_out(user)

    def get_user(self, user_id: str) -> UserOut | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        return self._to_user_out(user)

    def list_attorneys(self, status: VerificationStatus | None = None) -> list[UserOut]:
        """List all attorney accounts, optionally filtered by verification status."""
        attorneys = []
        for record in self._users.values():
            if record["role"] != UserRole.ATTORNEY:
                continue
            if status and record["verification_status"] != status:
                continue
            attorneys.append(self._to_user_out(record))
        return attorneys

    def submit_verification_docs(self, user_id: str, docs: dict) -> bool:
        """Attorney submits verification documents. Moves status to 'submitted'."""
        user = self._users.get(user_id)
        if user is None or user["role"] != UserRole.ATTORNEY:
            return False
        if user["verification_status"] not in (
            VerificationStatus.PENDING,
            VerificationStatus.REJECTED,  # Allow re-submission after rejection
        ):
            return False
        self._verification_docs[user_id] = {
            **docs,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        user["verification_status"] = VerificationStatus.SUBMITTED
        return True

    def get_verification_docs(self, user_id: str) -> dict | None:
        """Get verification documents metadata for an attorney."""
        return self._verification_docs.get(user_id)

    def set_verification_status(
        self, user_id: str, status: VerificationStatus, reason: str = ""
    ) -> UserOut | None:
        """Admin sets verification status (verify, reject, suspend)."""
        user = self._users.get(user_id)
        if user is None or user["role"] != UserRole.ATTORNEY:
            return None
        user["verification_status"] = status
        user["verification_reason"] = reason
        return self._to_user_out(user)

    def is_verified_attorney(self, user_id: str) -> bool:
        """Check if a user is a verified attorney. Used as a gate for sensitive operations."""
        user = self._users.get(user_id)
        if user is None or user["role"] != UserRole.ATTORNEY:
            return False
        return user["verification_status"] == VerificationStatus.VERIFIED

    def create_access_token(self, user: UserOut) -> str:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": user.id,
            "role": user.role.value,
            "exp": expire,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> TokenData | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str | None = payload.get("sub")
            role: str | None = payload.get("role")
            if user_id is None or role is None:
                return None
            return TokenData(user_id=user_id, role=UserRole(role))
        except jwt.PyJWTError:
            return None

    @staticmethod
    def _to_user_out(record: dict) -> UserOut:
        return UserOut(
            id=record["id"],
            email=record["email"],
            first_name=record["first_name"],
            last_name=record["last_name"],
            role=record["role"],
            verification_status=record.get("verification_status", VerificationStatus.NOT_APPLICABLE),
            bar_number=record.get("bar_number", ""),
            jurisdiction=record.get("jurisdiction", ""),
            years_experience=record.get("years_experience", 0),
            specializations=record.get("specializations", ""),
            firm_name=record.get("firm_name", ""),
        )
