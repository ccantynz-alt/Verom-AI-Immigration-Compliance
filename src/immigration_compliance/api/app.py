"""FastAPI application for immigration compliance API."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from immigration_compliance.models.audit import AuditAction, AuditEntry, ICEAuditReport
from immigration_compliance.models.auth import (
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserRole,
    VerificationDecision,
    VerificationDocUpload,
    VerificationStatus,
)
from immigration_compliance.models.billing import (
    CheckoutResponse,
    ConnectOnboardRequest,
    ConnectOnboardResponse,
    CreateCheckoutRequest,
    PaymentIntentRequest,
    PaymentIntentResponse,
    PlanInfo,
)
from immigration_compliance.models.case import Case, CaseStatus
from immigration_compliance.models.compliance import ComplianceReport, RuleViolation
from immigration_compliance.models.document import Document, DocumentCategory
from immigration_compliance.models.employee import Employee
from immigration_compliance.models.consultation import (
    Consultation,
    ConsultationRequest,
    ConsultationStatus,
    ExpirationAlert,
    InterviewType,
    MockInterviewSession,
    ReceiptTracker,
    TravelAdvisory,
    TravelAdvisoryRequest,
    VaultDocument,
)
from immigration_compliance.models.global_immigration import GlobalAssignment, TravelEntry
from immigration_compliance.models.hris import HRISIntegration, HRISProvider, IntegrationStatus, SyncRecord
from immigration_compliance.models.paf import PAFDocumentType, PublicAccessFile
from immigration_compliance.models.regulatory import (
    ImpactLevel,
    RegulatoryCategory,
    RegulatoryFeed,
    RegulatoryUpdate,
)
from immigration_compliance.services.audit_service import AuditTrailService, ICEAuditSimulator
from immigration_compliance.services.auth_service import AuthService
from immigration_compliance.services.billing_service import BillingService
from immigration_compliance.services.consultation_service import ConsultationService
from immigration_compliance.services.vault_service import TravelAdvisoryService, VaultService
from immigration_compliance.services.compliance_service import ComplianceService
from immigration_compliance.services.document_service import DocumentService
from immigration_compliance.services.global_service import GlobalImmigrationService
from immigration_compliance.services.hris_service import HRISService
from immigration_compliance.services.paf_service import PAFService
from immigration_compliance.services.regulatory_service import RegulatoryService

# Resolve frontend directory
_root = Path(__file__).resolve().parent.parent.parent.parent
_frontend_dir = _root / "frontend"

app = FastAPI(
    title="Verom.ai",
    description="AI-powered student visa applications and immigration attorney matching",
    version="0.1.0",
)

# Serve static assets (CSS, JS)
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

# Service instances
auth_service = AuthService()
billing_service = BillingService()
consultation_service = ConsultationService()
vault_service = VaultService()
travel_advisor = TravelAdvisoryService()
service = ComplianceService()
_cases: dict[str, Case] = {}
doc_service = DocumentService()
audit_trail = AuditTrailService()
ice_simulator = ICEAuditSimulator()
paf_service = PAFService()
regulatory_service = RegulatoryService()
global_service = GlobalImmigrationService()
hris_service = HRISService()

# Auth dependency
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserOut:
    """Validate JWT and return the current user. Raises 401 if invalid."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_data = AuthService.decode_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = auth_service.get_user(token_data.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: UserRole):
    """Dependency factory — restrict access to specific roles."""
    def _check(user: UserOut = Depends(get_current_user)) -> UserOut:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


def require_verified_attorney(user: UserOut = Depends(get_current_user)) -> UserOut:
    """Restrict access to verified attorneys only. Unverified attorneys cannot
    access client data, case documents, or the marketplace."""
    if user.role != UserRole.ATTORNEY:
        raise HTTPException(status_code=403, detail="Attorney access required")
    if user.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=403,
            detail=f"Attorney verification required. Current status: {user.verification_status.value}",
        )
    return user


# --- Request/Response models ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"

class ComplianceCheckRequest(BaseModel):
    as_of: date | None = None

class CaseStatusUpdate(BaseModel):
    status: CaseStatus

class PAFDocumentUpdate(BaseModel):
    document_type: PAFDocumentType
    is_present: bool
    title: str = ""
    notes: str = ""

class IntegrationStatusUpdate(BaseModel):
    status: IntegrationStatus
    error_message: str = ""


# --- Root / Frontend ---

def _serve_html(path: Path, fallback: str) -> HTMLResponse:
    """Serve an HTML file with cache-busting and no-cache headers."""
    if not path.exists():
        return HTMLResponse(content=f"<h1>Verom.ai</h1><p>{fallback}</p>")
    content = path.read_text()
    # Add content-hash query param to CSS/JS refs so browsers fetch fresh assets
    for ext in (".css", ".js"):
        for asset in _frontend_dir.rglob(f"*{ext}"):
            rel = f"/static/{asset.relative_to(_frontend_dir)}"
            if rel in content:
                h = hashlib.md5(asset.read_bytes()).hexdigest()[:8]  # noqa: S324
                content = content.replace(f'"{rel}"', f'"{rel}?v={h}"')
                content = content.replace(f"'{rel}'", f"'{rel}?v={h}'")
    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/", response_class=HTMLResponse)
def serve_landing() -> HTMLResponse:
    return _serve_html(_frontend_dir / "landing.html", "Landing page not found.")

@app.get("/app", response_class=HTMLResponse)
def serve_app() -> HTMLResponse:
    return _serve_html(_frontend_dir / "index.html", "App not found.")

@app.get("/login", response_class=HTMLResponse)
def serve_login() -> HTMLResponse:
    return _serve_html(_frontend_dir / "login.html", "Login page not found.")

@app.get("/applicant", response_class=HTMLResponse)
def serve_applicant() -> HTMLResponse:
    return _serve_html(_frontend_dir / "applicant.html", "Applicant portal not found.")

@app.get("/attorney", response_class=HTMLResponse)
def serve_attorney() -> HTMLResponse:
    return _serve_html(_frontend_dir / "attorney.html", "Attorney portal not found.")

@app.get("/privacy", response_class=HTMLResponse)
def serve_privacy() -> HTMLResponse:
    return _serve_html(_frontend_dir / "privacy.html", "Privacy policy not found.")

@app.get("/terms", response_class=HTMLResponse)
def serve_terms() -> HTMLResponse:
    return _serve_html(_frontend_dir / "terms.html", "Terms of service not found.")

@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


# =============================================
# Auth endpoints
# =============================================

@app.post("/api/auth/signup", response_model=Token, status_code=201)
def signup(data: UserCreate) -> Token:
    try:
        user = auth_service.create_user(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    access_token = auth_service.create_access_token(user)
    return Token(access_token=access_token, user=user)


@app.post("/api/auth/login", response_model=Token)
def login(data: UserLogin) -> Token:
    user = auth_service.authenticate(data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = auth_service.create_access_token(user)
    return Token(access_token=access_token, user=user)


@app.get("/api/auth/me", response_model=UserOut)
def get_me(user: UserOut = Depends(get_current_user)) -> UserOut:
    return user


# =============================================
# Attorney Verification endpoints
# =============================================

@app.post("/api/verification/submit", response_model=UserOut)
def submit_verification(
    docs: VerificationDocUpload,
    user: UserOut = Depends(require_role(UserRole.ATTORNEY)),
) -> UserOut:
    """Attorney submits verification documents (bar certificate, govt ID, insurance)."""
    if not docs.bar_certificate_filename:
        raise HTTPException(status_code=422, detail="Bar certificate document is required")
    if not docs.government_id_filename:
        raise HTTPException(status_code=422, detail="Government-issued ID is required")
    success = auth_service.submit_verification_docs(user.id, docs.model_dump())
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Verification documents cannot be submitted in current status",
        )
    updated = auth_service.get_user(user.id)
    audit_trail.log(
        AuditAction.COMPLIANCE_CHECK_RUN,
        details=f"Attorney verification docs submitted: {user.email}",
    )
    return updated  # type: ignore[return-value]


@app.get("/api/verification/status")
def get_verification_status(user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    """Attorney checks their own verification status."""
    docs = auth_service.get_verification_docs(user.id)
    return {
        "verification_status": user.verification_status.value,
        "documents_submitted": docs is not None,
        "documents": docs,
    }


@app.get("/api/admin/attorneys/pending", response_model=list[UserOut])
def list_pending_attorneys(user: UserOut = Depends(get_current_user)) -> list[UserOut]:
    """Admin endpoint: list attorneys awaiting verification."""
    # In production, this would check for admin role
    return auth_service.list_attorneys(status=VerificationStatus.SUBMITTED)


@app.post("/api/admin/attorneys/{attorney_id}/verify", response_model=UserOut)
def verify_attorney(
    attorney_id: str,
    decision: VerificationDecision,
    user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Admin endpoint: approve or reject an attorney's verification."""
    if decision.status not in (
        VerificationStatus.VERIFIED,
        VerificationStatus.REJECTED,
        VerificationStatus.SUSPENDED,
    ):
        raise HTTPException(status_code=422, detail="Invalid verification decision")
    result = auth_service.set_verification_status(attorney_id, decision.status, decision.reason)
    if result is None:
        raise HTTPException(status_code=404, detail="Attorney not found")
    audit_trail.log(
        AuditAction.COMPLIANCE_CHECK_RUN,
        details=f"Attorney {attorney_id} verification: {decision.status.value} — {decision.reason}",
    )
    return result


# =============================================
# Billing endpoints
# =============================================

@app.get("/api/billing/plans", response_model=list[PlanInfo])
def get_plans(role: str = "") -> list[PlanInfo]:
    return billing_service.get_plans(role)


@app.post("/api/billing/checkout", response_model=CheckoutResponse)
def create_checkout(req: CreateCheckoutRequest, user: UserOut = Depends(get_current_user)) -> CheckoutResponse:
    return billing_service.create_checkout_session(
        user_id=user.id,
        plan=req.plan,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
    )


@app.get("/api/billing/subscription")
def get_subscription(user: UserOut = Depends(get_current_user)):
    sub = billing_service.get_subscription(user.id)
    if sub is None:
        return {"subscription": None}
    return {"subscription": sub}


@app.post("/api/billing/connect/onboard", response_model=ConnectOnboardResponse)
def connect_onboard(
    req: ConnectOnboardRequest,
    user: UserOut = Depends(require_role(UserRole.ATTORNEY)),
) -> ConnectOnboardResponse:
    return billing_service.create_connect_account(
        user_id=user.id,
        return_url=req.return_url,
        refresh_url=req.refresh_url,
    )


@app.get("/api/billing/connect/status")
def connect_status(user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    account_id = billing_service.get_connect_account(user.id)
    return {"connected": account_id is not None, "account_id": account_id}


@app.post("/api/billing/payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    req: PaymentIntentRequest,
    user: UserOut = Depends(get_current_user),
) -> PaymentIntentResponse:
    return billing_service.create_payment_intent(
        applicant_user_id=user.id,
        attorney_user_id=req.attorney_user_id,
        case_id=req.case_id,
        description=req.description,
    )


# =============================================
# Video Consultation endpoints
# =============================================

@app.post("/api/consultations", response_model=Consultation, status_code=201)
def request_consultation(
    req: ConsultationRequest,
    user: UserOut = Depends(get_current_user),
) -> Consultation:
    return consultation_service.request_consultation(
        applicant_id=user.id,
        attorney_id=req.attorney_id,
        consultation_type=req.consultation_type,
        preferred_date=req.preferred_date,
        preferred_time=req.preferred_time,
        duration=req.duration_minutes,
        notes=req.notes,
        case_id=req.case_id,
    )


@app.get("/api/consultations", response_model=list[Consultation])
def list_consultations(user: UserOut = Depends(get_current_user)) -> list[Consultation]:
    role = "attorney" if user.role == UserRole.ATTORNEY else "applicant"
    return consultation_service.list_consultations(user.id, role)


@app.get("/api/consultations/{consultation_id}", response_model=Consultation)
def get_consultation_detail(
    consultation_id: str,
    user: UserOut = Depends(get_current_user),
) -> Consultation:
    c = consultation_service.get_consultation(consultation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if c.applicant_id != user.id and c.attorney_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return c


@app.patch("/api/consultations/{consultation_id}/status", response_model=Consultation)
def update_consultation_status(
    consultation_id: str,
    status: ConsultationStatus,
    user: UserOut = Depends(get_current_user),
) -> Consultation:
    c = consultation_service.update_status(consultation_id, status)
    if c is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return c


@app.get("/api/consultations/slots/{attorney_id}")
def get_attorney_slots(attorney_id: str, date: str = ""):
    return consultation_service.get_available_slots(attorney_id, date)


# =============================================
# Interview Prep endpoints
# =============================================

@app.get("/api/interview-prep/types")
def get_interview_types():
    return ConsultationService.get_interview_types()


@app.post("/api/interview-prep/start", response_model=MockInterviewSession)
def start_mock_interview(
    interview_type: InterviewType,
    user: UserOut = Depends(get_current_user),
) -> MockInterviewSession:
    return consultation_service.start_mock_interview(user.id, interview_type)


@app.get("/api/interview-prep/{session_id}", response_model=MockInterviewSession)
def get_mock_session(
    session_id: str,
    user: UserOut = Depends(get_current_user),
) -> MockInterviewSession:
    session = consultation_service.get_mock_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/interview-prep/{session_id}/complete", response_model=MockInterviewSession)
def complete_mock_interview(
    session_id: str,
    score: int = 0,
    user: UserOut = Depends(get_current_user),
) -> MockInterviewSession:
    session = consultation_service.complete_mock_interview(session_id, score)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/api/interview-prep/history/me", response_model=list[MockInterviewSession])
def list_my_mock_sessions(user: UserOut = Depends(get_current_user)) -> list[MockInterviewSession]:
    return consultation_service.list_mock_sessions(user.id)


# =============================================
# Document Vault endpoints
# =============================================

@app.post("/api/vault/documents", response_model=VaultDocument, status_code=201)
def upload_vault_document(
    doc: VaultDocument,
    user: UserOut = Depends(get_current_user),
) -> VaultDocument:
    doc_with_user = doc.model_copy(update={"user_id": user.id})
    return vault_service.add_document(doc_with_user)


@app.get("/api/vault/documents", response_model=list[VaultDocument])
def list_vault_documents(user: UserOut = Depends(get_current_user)) -> list[VaultDocument]:
    return vault_service.list_documents(user.id)


@app.delete("/api/vault/documents/{doc_id}", status_code=204)
def delete_vault_document(doc_id: str, user: UserOut = Depends(get_current_user)) -> None:
    doc = vault_service.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    vault_service.delete_document(doc_id)


@app.get("/api/vault/alerts", response_model=list[ExpirationAlert])
def get_expiration_alerts(user: UserOut = Depends(get_current_user)) -> list[ExpirationAlert]:
    return vault_service.get_expiration_alerts(user.id)


# =============================================
# Receipt Tracker endpoints
# =============================================

@app.post("/api/receipts", response_model=ReceiptTracker, status_code=201)
def add_receipt(
    tracker: ReceiptTracker,
    user: UserOut = Depends(get_current_user),
) -> ReceiptTracker:
    if not VaultService.validate_receipt_number(tracker.receipt_number):
        raise HTTPException(
            status_code=422,
            detail="Invalid receipt number format. Expected: 3 letters + 10 digits (e.g., EAC2190012345)",
        )
    tracker_with_user = tracker.model_copy(update={"user_id": user.id})
    return vault_service.add_receipt(tracker_with_user)


@app.get("/api/receipts", response_model=list[ReceiptTracker])
def list_receipts(user: UserOut = Depends(get_current_user)) -> list[ReceiptTracker]:
    return vault_service.list_receipts(user.id)


@app.post("/api/receipts/{tracker_id}/check", response_model=ReceiptTracker)
def check_receipt(
    tracker_id: str,
    user: UserOut = Depends(get_current_user),
) -> ReceiptTracker:
    result = vault_service.check_receipt_status(tracker_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Receipt tracker not found")
    return result


@app.delete("/api/receipts/{tracker_id}", status_code=204)
def delete_receipt(tracker_id: str, user: UserOut = Depends(get_current_user)) -> None:
    if not vault_service.delete_receipt(tracker_id):
        raise HTTPException(status_code=404, detail="Receipt tracker not found")


# =============================================
# Travel Advisory endpoints
# =============================================

@app.post("/api/travel-advisory", response_model=TravelAdvisory)
def get_travel_advisory(
    req: TravelAdvisoryRequest,
    pending_forms: str = "",
    has_advance_parole: bool = False,
    user: UserOut = Depends(get_current_user),
) -> TravelAdvisory:
    forms = [f.strip() for f in pending_forms.split(",") if f.strip()] if pending_forms else []
    return travel_advisor.assess_travel(
        pending_forms=forms,
        destination_country=req.destination_country,
        has_advance_parole=has_advance_parole,
    )


# =============================================
# Employee endpoints
# =============================================

@app.post("/api/employees", response_model=Employee, status_code=201)
def create_employee(employee: Employee) -> Employee:
    if service.get_employee(employee.id):
        raise HTTPException(status_code=409, detail=f"Employee {employee.id} already exists")
    emp = service.add_employee(employee)
    audit_trail.log(AuditAction.EMPLOYEE_CREATED, employee_id=emp.id, details=f"Created {emp.first_name} {emp.last_name}")
    return emp

@app.get("/api/employees", response_model=list[Employee])
def list_employees() -> list[Employee]:
    return service.list_employees()

@app.get("/api/employees/{employee_id}", response_model=Employee)
def get_employee(employee_id: str) -> Employee:
    emp = service.get_employee(employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return emp

@app.delete("/api/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: str) -> None:
    if not service.remove_employee(employee_id):
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    audit_trail.log(AuditAction.EMPLOYEE_DELETED, employee_id=employee_id)


# =============================================
# Compliance endpoints
# =============================================

@app.post("/api/compliance/check/{employee_id}", response_model=list[RuleViolation])
def check_employee_compliance(employee_id: str, request: ComplianceCheckRequest | None = None) -> list[RuleViolation]:
    as_of = request.as_of if request else None
    try:
        violations = service.check_employee(employee_id, as_of)
        audit_trail.log(AuditAction.COMPLIANCE_CHECK_RUN, employee_id=employee_id, details=f"{len(violations)} violations found")
        return violations
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/compliance/report", response_model=ComplianceReport)
def generate_compliance_report(request: ComplianceCheckRequest | None = None) -> ComplianceReport:
    as_of = request.as_of if request else None
    report = service.generate_report(as_of)
    audit_trail.log(AuditAction.REPORT_GENERATED, details=f"Report: {report.compliant_count}/{report.total_employees} compliant")
    return report


# =============================================
# Case endpoints
# =============================================

@app.post("/api/cases", response_model=Case, status_code=201)
def create_case(case: Case) -> Case:
    if case.id in _cases:
        raise HTTPException(status_code=409, detail=f"Case {case.id} already exists")
    _cases[case.id] = case
    audit_trail.log(AuditAction.CASE_CREATED, employee_id=case.employee_id, case_id=case.id, details=case.case_type)
    return case

@app.get("/api/cases", response_model=list[Case])
def list_cases() -> list[Case]:
    return list(_cases.values())

@app.get("/api/cases/{case_id}", response_model=Case)
def get_case(case_id: str) -> Case:
    case = _cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case

@app.patch("/api/cases/{case_id}/status", response_model=Case)
def update_case_status(case_id: str, update: CaseStatusUpdate) -> Case:
    case = _cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    old_status = case.status
    updated = case.model_copy(update={"status": update.status})
    _cases[case_id] = updated
    audit_trail.log(AuditAction.CASE_STATUS_CHANGED, case_id=case_id, details=f"{old_status} -> {update.status}")
    return updated

@app.delete("/api/cases/{case_id}", status_code=204)
def delete_case(case_id: str) -> None:
    if _cases.pop(case_id, None) is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")


# =============================================
# Document endpoints
# =============================================

@app.post("/api/documents", response_model=Document, status_code=201)
def create_document(doc: Document) -> Document:
    result = doc_service.add_document(doc)
    audit_trail.log(AuditAction.DOCUMENT_UPLOADED, employee_id=doc.employee_id, document_id=doc.id, details=doc.title)
    return result

@app.get("/api/documents", response_model=list[Document])
def list_documents(employee_id: str | None = None, category: DocumentCategory | None = None, case_id: str | None = None) -> list[Document]:
    return doc_service.list_documents(employee_id=employee_id, category=category, case_id=case_id)

@app.get("/api/documents/expiring", response_model=list[Document])
def get_expiring_documents(days: int = 90) -> list[Document]:
    return doc_service.get_expiring_documents(within_days=days)

@app.get("/api/documents/{doc_id}", response_model=Document)
def get_document(doc_id: str) -> Document:
    doc = doc_service.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return doc

@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str) -> None:
    if not doc_service.delete_document(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    audit_trail.log(AuditAction.DOCUMENT_DELETED, document_id=doc_id)


# =============================================
# Audit Trail endpoints
# =============================================

@app.get("/api/audit-trail", response_model=list[AuditEntry])
def get_audit_trail(employee_id: str | None = None, limit: int = 100) -> list[AuditEntry]:
    return audit_trail.get_entries(employee_id=employee_id, limit=limit)

@app.get("/api/audit-trail/stats")
def get_audit_stats() -> dict:
    entries = audit_trail.get_entries(limit=10000)
    action_counts: dict[str, int] = {}
    for e in entries:
        action_counts[e.action.value] = action_counts.get(e.action.value, 0) + 1
    return {"total_entries": audit_trail.total_entries, "action_breakdown": action_counts}


# =============================================
# ICE Audit Simulation endpoints
# =============================================

@app.post("/api/audit/ice-simulation", response_model=ICEAuditReport)
def run_ice_audit_simulation(request: ComplianceCheckRequest | None = None) -> ICEAuditReport:
    employees = service.list_employees()
    paf_data: dict[str, dict] = {}
    for emp in employees:
        pafs = paf_service.get_paf_by_employee(emp.id)
        if pafs:
            paf_data[emp.id] = {"complete": pafs[0].completeness_score >= 100.0}
    report = ice_simulator.run_audit(employees, paf_data=paf_data)
    return report


# =============================================
# PAF endpoints
# =============================================

@app.post("/api/pafs", response_model=PublicAccessFile, status_code=201)
def create_paf(paf: PublicAccessFile) -> PublicAccessFile:
    result = paf_service.create_paf(paf)
    audit_trail.log(AuditAction.PAF_UPDATED, employee_id=paf.employee_id, details=f"PAF created: {paf.id}")
    return result

@app.get("/api/pafs", response_model=list[PublicAccessFile])
def list_pafs(employee_id: str | None = None) -> list[PublicAccessFile]:
    if employee_id:
        return paf_service.get_paf_by_employee(employee_id)
    return paf_service.list_pafs()

@app.get("/api/pafs/{paf_id}", response_model=PublicAccessFile)
def get_paf(paf_id: str) -> PublicAccessFile:
    paf = paf_service.get_paf(paf_id)
    if paf is None:
        raise HTTPException(status_code=404, detail=f"PAF {paf_id} not found")
    return paf

@app.patch("/api/pafs/{paf_id}/document", response_model=PublicAccessFile)
def update_paf_document(paf_id: str, update: PAFDocumentUpdate) -> PublicAccessFile:
    result = paf_service.update_paf_document(paf_id, update.document_type, update.is_present, update.title, update.notes)
    if result is None:
        raise HTTPException(status_code=404, detail=f"PAF {paf_id} not found")
    audit_trail.log(AuditAction.PAF_UPDATED, details=f"Updated {update.document_type.value} in PAF {paf_id}")
    return result

@app.delete("/api/pafs/{paf_id}", status_code=204)
def delete_paf(paf_id: str) -> None:
    if not paf_service.delete_paf(paf_id):
        raise HTTPException(status_code=404, detail=f"PAF {paf_id} not found")


# =============================================
# Regulatory Intelligence endpoints
# =============================================

@app.get("/api/regulatory/feed", response_model=RegulatoryFeed)
def get_regulatory_feed() -> RegulatoryFeed:
    return regulatory_service.get_feed()

@app.get("/api/regulatory/updates", response_model=list[RegulatoryUpdate])
def get_regulatory_updates(
    category: RegulatoryCategory | None = None,
    impact_level: ImpactLevel | None = None,
    action_required: bool | None = None,
) -> list[RegulatoryUpdate]:
    return regulatory_service.get_updates(category=category, impact_level=impact_level, action_required=action_required)

@app.get("/api/regulatory/processing-times")
def get_processing_times(form_type: str | None = None) -> list:
    return regulatory_service.get_processing_times(form_type=form_type)

@app.get("/api/regulatory/visa-bulletin")
def get_visa_bulletin(category: str | None = None, country: str | None = None) -> list:
    return regulatory_service.get_visa_bulletin(category=category, country=country)


# =============================================
# Global Immigration endpoints
# =============================================

@app.get("/api/global/countries")
def get_countries() -> list:
    return global_service.get_countries()

@app.get("/api/global/countries/{code}")
def get_country(code: str):
    country = global_service.get_country(code)
    if country is None:
        raise HTTPException(status_code=404, detail=f"Country {code} not found")
    return country

@app.post("/api/global/assignments", response_model=GlobalAssignment, status_code=201)
def create_assignment(assignment: GlobalAssignment) -> GlobalAssignment:
    return global_service.create_assignment(assignment)

@app.get("/api/global/assignments", response_model=list[GlobalAssignment])
def list_assignments(employee_id: str | None = None) -> list[GlobalAssignment]:
    return global_service.get_assignments(employee_id=employee_id)

@app.delete("/api/global/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str) -> None:
    if not global_service.delete_assignment(assignment_id):
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

@app.post("/api/global/travel", response_model=TravelEntry, status_code=201)
def add_travel(entry: TravelEntry) -> TravelEntry:
    return global_service.add_travel(entry)

@app.get("/api/global/travel", response_model=list[TravelEntry])
def list_travel(employee_id: str | None = None) -> list[TravelEntry]:
    return global_service.get_travel(employee_id=employee_id)

@app.get("/api/global/compliance/{employee_id}")
def get_global_compliance(employee_id: str):
    return global_service.get_compliance_summary(employee_id)


# =============================================
# HRIS Integration endpoints
# =============================================

@app.get("/api/hris/providers")
def get_hris_providers() -> list:
    return hris_service.supported_providers

@app.post("/api/hris/integrations", response_model=HRISIntegration, status_code=201)
def create_integration(integration: HRISIntegration) -> HRISIntegration:
    return hris_service.create_integration(integration)

@app.get("/api/hris/integrations", response_model=list[HRISIntegration])
def list_integrations() -> list[HRISIntegration]:
    return hris_service.list_integrations()

@app.get("/api/hris/integrations/{integration_id}", response_model=HRISIntegration)
def get_integration(integration_id: str) -> HRISIntegration:
    integration = hris_service.get_integration(integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")
    return integration

@app.patch("/api/hris/integrations/{integration_id}/status", response_model=HRISIntegration)
def update_integration_status(integration_id: str, update: IntegrationStatusUpdate) -> HRISIntegration:
    result = hris_service.update_status(integration_id, update.status, update.error_message)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")
    return result

@app.post("/api/hris/integrations/{integration_id}/sync", response_model=SyncRecord)
def run_sync(integration_id: str) -> SyncRecord:
    if hris_service.get_integration(integration_id) is None:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")
    return hris_service.simulate_sync(integration_id)

@app.delete("/api/hris/integrations/{integration_id}", status_code=204)
def delete_integration(integration_id: str) -> None:
    if not hris_service.delete_integration(integration_id):
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")

@app.get("/api/hris/mappings/{provider}")
def get_default_mappings(provider: HRISProvider) -> list:
    return hris_service.get_default_mappings(provider)
