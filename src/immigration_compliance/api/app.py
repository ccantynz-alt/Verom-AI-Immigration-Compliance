"""FastAPI application for immigration compliance API."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Any

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
from immigration_compliance.services.domination_service import (
    AgenticPipelineService,
    H1BLotterySimulatorService,
    EADGapRiskService,
    PreFilingScannerService,
    USCISApiService,
)
from immigration_compliance.services.differentiation_service import (
    StrategyOptimizerService,
    SocialMediaAuditService,
    RegulatoryImpactEngine,
    CompensationPlannerService,
    TransparencyDashboardService,
)
from immigration_compliance.services.stickiness_service import (
    GamifiedScoringService,
    AttorneyAnalyticsService,
    CommunityForumService,
    BenchmarkReportService,
    PWAService,
)
from immigration_compliance.services.competitor_intel_service import CompetitorIntelService
from immigration_compliance.services.hris_deep_service import HRISDeepService
from immigration_compliance.services.benchmarking_service import BenchmarkingService
from immigration_compliance.services.flat_rate_service import FlatRateService
from immigration_compliance.services.uscis_client_service import USCISClientService
from immigration_compliance.services.crawler_service import CompetitiveCrawlerService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.rfe_predictor_service import RFEPredictorService
from immigration_compliance.services.conflict_check_service import ConflictCheckService
from immigration_compliance.services.onboarding_service import OnboardingService
from immigration_compliance.services.document_intake_service import DocumentIntakeService
from immigration_compliance.services.attorney_match_service import AttorneyMatchService
from immigration_compliance.services.form_population_service import FormPopulationService
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.calendar_sync_service import CalendarSyncService
from immigration_compliance.services.client_chatbot_service import ClientChatbotService
from immigration_compliance.services.family_bundle_service import FamilyBundleService
from immigration_compliance.services.packet_assembly_service import PacketAssemblyService
from immigration_compliance.services.regulatory_impact_service import RegulatoryImpactService
from immigration_compliance.services.migration_importer_service import MigrationImporterService
from immigration_compliance.services.petition_letter_service import PetitionLetterService
from immigration_compliance.services.rfe_response_service import RFEResponseService
from immigration_compliance.services.support_letter_service import SupportLetterService
from immigration_compliance.services.completeness_scorer_service import CompletenessScorerService
from immigration_compliance.services.soc_code_service import SocCodeService
from immigration_compliance.services.document_qa_service import DocumentQAService
from immigration_compliance.services.translation_service import TranslationService
from immigration_compliance.services.time_tracking_service import TimeTrackingService
from immigration_compliance.services.trust_accounting_service import TrustAccountingService
from immigration_compliance.services.persistent_store_service import PersistentStore, get_default_store
from immigration_compliance.services.storage_binding import bind_storage

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

# Tier 1 — Market Domination
agentic_pipeline = AgenticPipelineService()
h1b_simulator = H1BLotterySimulatorService()
ead_risk_service = EADGapRiskService()
prefiling_scanner = PreFilingScannerService()
uscis_api = USCISApiService()

# Tier 2 — Differentiation
strategy_optimizer = StrategyOptimizerService()
social_media_audit = SocialMediaAuditService()
regulatory_impact = RegulatoryImpactEngine()
compensation_planner = CompensationPlannerService()
transparency_dashboard = TransparencyDashboardService()

# Tier 3 — Stickiness
gamified_scoring = GamifiedScoringService()
attorney_analytics = AttorneyAnalyticsService()
community_forum = CommunityForumService()
benchmark_reports = BenchmarkReportService()
pwa_service = PWAService()

# Competitor Intel
competitor_intel = CompetitorIntelService()

# International Competitive Crawler
crawler = CompetitiveCrawlerService()

# Magical onboarding + AI intake engine
intake_engine = IntakeEngineService()
rfe_predictor = RFEPredictorService()
conflict_check = ConflictCheckService()
onboarding = OnboardingService()
document_intake = DocumentIntakeService()
attorney_match = AttorneyMatchService()
form_population = FormPopulationService()
case_workspace = CaseWorkspaceService(
    intake_engine=intake_engine,
    document_intake=document_intake,
    form_population=form_population,
    attorney_match=attorney_match,
    conflict_check=conflict_check,
    rfe_predictor=rfe_predictor,
)
calendar_sync = CalendarSyncService(case_workspace=case_workspace)
client_chatbot = ClientChatbotService(case_workspace=case_workspace)
family_bundle = FamilyBundleService(case_workspace=case_workspace, intake_engine=intake_engine)
packet_assembly = PacketAssemblyService(case_workspace=case_workspace, document_intake=document_intake, form_population=form_population)
regulatory_impact_engine = RegulatoryImpactService(case_workspace=case_workspace)
migration_importer = MigrationImporterService(case_workspace=case_workspace, intake_engine=intake_engine)
petition_letter = PetitionLetterService(case_workspace=case_workspace, intake_engine=intake_engine, document_intake=document_intake)
rfe_response = RFEResponseService(case_workspace=case_workspace, intake_engine=intake_engine, document_intake=document_intake)
support_letter = SupportLetterService(case_workspace=case_workspace, intake_engine=intake_engine, document_intake=document_intake)
completeness_scorer = CompletenessScorerService(case_workspace=case_workspace, intake_engine=intake_engine, document_intake=document_intake)
soc_code_service = SocCodeService()
document_qa = DocumentQAService()
translation_service = TranslationService()
time_tracking = TimeTrackingService(case_workspace=case_workspace)
trust_accounting = TrustAccountingService()

# Persistent store — reads VEROM_DB_PATH env var (default: verom_state.db). Set
# VEROM_DISABLE_PERSISTENCE=1 to fall back to in-memory only.
import os as _os  # noqa: E402
persistent_store: PersistentStore | None = None
if _os.environ.get("VEROM_DISABLE_PERSISTENCE") not in ("1", "true", "yes"):
    try:
        persistent_store = get_default_store()
    except Exception:
        persistent_store = None

# Bind the persistent store to every service so their state survives restarts.
# Each call: loads previously-saved state then wraps mutating methods with
# debounced saves. Service callers never see this — it's transparent.
if persistent_store is not None:
    for _svc in (
        intake_engine, document_intake, form_population, conflict_check,
        onboarding, family_bundle, client_chatbot, packet_assembly,
        regulatory_impact_engine, migration_importer, petition_letter,
        rfe_response, attorney_match, calendar_sync, case_workspace,
    ):
        try:
            bind_storage(_svc, persistent_store)
        except Exception:
            pass

# Gap Closers — competitive response features
hris_deep = HRISDeepService()
benchmarking = BenchmarkingService()
flat_rate = FlatRateService()
uscis_client = USCISClientService()

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

@app.get("/attorney-terms", response_class=HTMLResponse)
def serve_attorney_terms() -> HTMLResponse:
    return _serve_html(_frontend_dir / "attorney-terms.html", "Attorney terms not found.")

@app.get("/attorney-code-of-conduct", response_class=HTMLResponse)
def serve_attorney_code_of_conduct() -> HTMLResponse:
    return _serve_html(_frontend_dir / "attorney-code-of-conduct.html", "Attorney code of conduct not found.")

@app.get("/escrow-terms", response_class=HTMLResponse)
def serve_escrow_terms() -> HTMLResponse:
    return _serve_html(_frontend_dir / "escrow-terms.html", "Escrow terms not found.")

@app.get("/anti-fraud-policy", response_class=HTMLResponse)
def serve_anti_fraud_policy() -> HTMLResponse:
    return _serve_html(_frontend_dir / "anti-fraud-policy.html", "Anti-fraud policy not found.")

@app.get("/applicant-protection", response_class=HTMLResponse)
def serve_applicant_protection() -> HTMLResponse:
    return _serve_html(_frontend_dir / "applicant-protection.html", "Applicant protection policy not found.")

@app.get("/onboarding/applicant", response_class=HTMLResponse)
def serve_onboarding_applicant() -> HTMLResponse:
    return _serve_html(_frontend_dir / "onboarding-applicant.html", "Applicant onboarding not found.")

@app.get("/onboarding/attorney", response_class=HTMLResponse)
def serve_onboarding_attorney() -> HTMLResponse:
    return _serve_html(_frontend_dir / "onboarding-attorney.html", "Attorney onboarding not found.")

@app.get("/intake/documents", response_class=HTMLResponse)
def serve_document_collection() -> HTMLResponse:
    return _serve_html(_frontend_dir / "document-collection.html", "Document collection not found.")

@app.get("/forms", response_class=HTMLResponse)
def serve_forms_workspace() -> HTMLResponse:
    return _serve_html(_frontend_dir / "forms-workspace.html", "Forms workspace not found.")

@app.get("/case", response_class=HTMLResponse)
def serve_case_workspace() -> HTMLResponse:
    return _serve_html(_frontend_dir / "case-workspace.html", "Case workspace not found.")

@app.get("/workbench", response_class=HTMLResponse)
def serve_workbench() -> HTMLResponse:
    return _serve_html(_frontend_dir / "workbench.html", "Workbench not found.")

@app.get("/petition-letter", response_class=HTMLResponse)
def serve_petition_letter_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "petition-letter.html", "Petition letter UI not found.")

@app.get("/rfe-response", response_class=HTMLResponse)
def serve_rfe_response_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "rfe-response.html", "RFE response UI not found.")

@app.get("/family-bundle", response_class=HTMLResponse)
def serve_family_bundle_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "family-bundle.html", "Family bundle UI not found.")

@app.get("/calendar", response_class=HTMLResponse)
def serve_calendar_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "calendar.html", "Calendar sync UI not found.")

@app.get("/migrate", response_class=HTMLResponse)
def serve_migrate_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "migrate.html", "Migration UI not found.")

@app.get("/packets", response_class=HTMLResponse)
def serve_packets_page() -> HTMLResponse:
    return _serve_html(_frontend_dir / "packets.html", "Packets UI not found.")

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


# =============================================
# Tier 1: Agentic Pipeline endpoints
# =============================================

class PipelineRequest(BaseModel):
    case_id: str
    visa_type: str
    applicant_data: dict = {}

@app.post("/api/pipeline", status_code=201)
def create_pipeline(req: PipelineRequest):
    return agentic_pipeline.create_pipeline(req.case_id, req.visa_type, req.applicant_data)

@app.post("/api/pipeline/{pipeline_id}/advance")
def advance_pipeline(pipeline_id: str):
    try:
        return agentic_pipeline.advance_pipeline(pipeline_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/pipeline/{pipeline_id}")
def get_pipeline(pipeline_id: str):
    p = agentic_pipeline.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return p

@app.get("/api/pipeline")
def list_pipelines(attorney_id: str = ""):
    return agentic_pipeline.list_pipelines(attorney_id)


# =============================================
# Tier 1: H-1B Lottery Simulator endpoints
# =============================================

class LotterySimRequest(BaseModel):
    wage_level: int = 1
    has_us_masters: bool = False
    salary: float = 80000
    job_category: str = ""
    employer_size: str = ""

@app.post("/api/h1b-lottery/simulate")
def simulate_lottery(req: LotterySimRequest):
    return h1b_simulator.simulate(req.model_dump())

@app.post("/api/h1b-lottery/batch")
def batch_simulate_lottery(employees: list[dict]):
    return h1b_simulator.batch_simulate(employees)

@app.get("/api/h1b-lottery/historical")
def get_lottery_history():
    return h1b_simulator.get_historical_rates()


# =============================================
# Tier 1: EAD Gap Risk Manager endpoints
# =============================================

@app.post("/api/ead-risk/analyze")
def analyze_ead_risk(employee_data: dict):
    return ead_risk_service.analyze_employee(employee_data)

@app.post("/api/ead-risk/workforce")
def analyze_ead_workforce(employees: list[dict]):
    return ead_risk_service.analyze_workforce(employees)

@app.post("/api/ead-risk/generate-renewals")
def generate_ead_renewals(employee_ids: list[str]):
    return ead_risk_service.generate_renewals(employee_ids)

@app.get("/api/ead-risk/rules")
def get_ead_rules():
    return ead_risk_service.get_auto_extension_rules()


# =============================================
# Tier 1: Pre-Filing Scanner endpoints
# =============================================

@app.post("/api/prefiling/scan")
def scan_case_prefiling(case_data: dict):
    return prefiling_scanner.scan_case(case_data)

@app.post("/api/prefiling/scan-form")
def scan_form_prefiling(form_data: dict, form_type: str = "I-129"):
    return prefiling_scanner.scan_form(form_data, form_type)

@app.get("/api/prefiling/rfe-triggers/{visa_type}")
def get_rfe_triggers(visa_type: str):
    return prefiling_scanner.get_common_rfe_triggers(visa_type)


# =============================================
# Tier 1: USCIS API endpoints
# =============================================

@app.get("/api/uscis/status/{receipt_number}")
def get_uscis_status(receipt_number: str):
    return uscis_api.get_case_status(receipt_number)

@app.post("/api/uscis/bulk-status")
def bulk_uscis_status(receipt_numbers: list[str]):
    return uscis_api.bulk_status_check(receipt_numbers)

@app.post("/api/uscis/subscribe")
def subscribe_uscis_updates(receipt_number: str, callback_url: str):
    return uscis_api.subscribe_to_updates(receipt_number, callback_url)

@app.get("/api/uscis/processing-times/{form_type}")
def get_uscis_processing(form_type: str, service_center: str | None = None):
    return uscis_api.get_processing_times(form_type, service_center)

@app.get("/api/uscis/compare/{receipt_number}")
def compare_uscis_case(receipt_number: str):
    return uscis_api.compare_to_average(receipt_number)


# =============================================
# Tier 2: Strategy Optimizer endpoints
# =============================================

@app.post("/api/strategy/optimize")
def optimize_strategy(applicant_profile: dict):
    return strategy_optimizer.optimize(applicant_profile)

@app.post("/api/strategy/compare")
def compare_countries(applicant_profile: dict, countries: list[str]):
    return strategy_optimizer.compare_countries(applicant_profile, countries)

@app.get("/api/strategy/requirements/{country}/{visa_type}")
def get_strategy_requirements(country: str, visa_type: str):
    result = strategy_optimizer.get_country_requirements(country, visa_type)
    if not result:
        raise HTTPException(status_code=404, detail="Pathway not found")
    return result


# =============================================
# Tier 2: Social Media Audit endpoints
# =============================================

@app.post("/api/social-audit/audit")
def audit_social_media(applicant_id: str, platforms_data: list[dict]):
    return social_media_audit.audit_profile(applicant_id, platforms_data)

@app.post("/api/social-audit/disclosure")
def generate_disclosure(applicant_id: str, platforms_data: list[dict] | None = None):
    return social_media_audit.generate_disclosure_list(applicant_id, platforms_data)

@app.get("/api/social-audit/platforms")
def get_required_platforms():
    return social_media_audit.get_required_platforms()

@app.post("/api/social-audit/consistency")
def check_social_consistency(ds160_data: dict, actual_profiles: list[dict]):
    return social_media_audit.check_consistency(ds160_data, actual_profiles)


# =============================================
# Tier 2: Regulatory Impact Engine endpoints
# =============================================

@app.post("/api/regulatory-impact/analyze")
def analyze_regulation(regulation_data: dict):
    return regulatory_impact.analyze_regulation(regulation_data)

@app.post("/api/regulatory-impact/affected-cases")
def find_affected_cases(regulation_id: str, cases: list[dict]):
    return regulatory_impact.find_affected_cases(regulation_id, cases)

@app.post("/api/regulatory-impact/action-plan")
def generate_action_plan(regulation_id: str, case_id: str):
    return regulatory_impact.generate_action_plan(regulation_id, case_id)

@app.get("/api/regulatory-impact/pending")
def get_pending_regulations():
    return regulatory_impact.get_pending_regulations()


# =============================================
# Tier 2: Compensation Planner endpoints
# =============================================

@app.post("/api/compensation/analyze")
def analyze_compensation(employee_data: dict):
    return compensation_planner.analyze_impact(employee_data)

@app.post("/api/compensation/optimize")
def optimize_workforce_comp(employees: list[dict]):
    return compensation_planner.optimize_workforce(employees)

@app.get("/api/compensation/prevailing-wages")
def get_prevailing_wages(soc_code: str, area: str):
    result = compensation_planner.get_prevailing_wages(soc_code, area)
    if not result:
        raise HTTPException(status_code=404, detail="No data for this SOC/area")
    return result

@app.post("/api/compensation/roi")
def calculate_comp_roi(salary_increase: float, probability_increase: float):
    return compensation_planner.calculate_roi(salary_increase, probability_increase)


# =============================================
# Tier 2: Transparency Dashboard endpoints
# =============================================

@app.post("/api/transparency/submit")
def submit_processing_data(user_id: str, data: dict):
    return transparency_dashboard.submit_data_point(user_id, data)

@app.get("/api/transparency/times/{form_type}")
def get_community_times(form_type: str, service_center: str | None = None):
    return transparency_dashboard.get_community_times(form_type, service_center)

@app.get("/api/transparency/trends/{form_type}")
def get_processing_trends(form_type: str):
    return transparency_dashboard.get_trends(form_type)

@app.get("/api/transparency/anomalies")
def get_processing_anomalies():
    return transparency_dashboard.get_anomalies()

@app.get("/api/transparency/compare/{form_type}")
def compare_times(form_type: str):
    return transparency_dashboard.compare_official_vs_community(form_type)


# =============================================
# Tier 3: Gamified Scoring endpoints
# =============================================

@app.get("/api/gamification/score/{firm_id}")
def get_firm_score(firm_id: str):
    return gamified_scoring.get_firm_score(firm_id)

@app.get("/api/gamification/leaderboard")
def get_leaderboard(category: str = "overall"):
    return gamified_scoring.get_leaderboard(category)

@app.post("/api/gamification/badge")
def award_badge(firm_id: str, badge_type: str):
    try:
        return gamified_scoring.award_badge(firm_id, badge_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/gamification/streak/{firm_id}")
def get_streak(firm_id: str):
    return gamified_scoring.get_streak(firm_id)

@app.get("/api/gamification/certification/{firm_id}")
def get_certification(firm_id: str):
    return gamified_scoring.get_certification_status(firm_id)


# =============================================
# Tier 3: Attorney Analytics endpoints
# =============================================

@app.get("/api/attorney-analytics/{attorney_id}/outcomes")
def get_attorney_outcomes(attorney_id: str):
    return attorney_analytics.get_attorney_outcomes(attorney_id)

@app.get("/api/attorney-analytics/rankings/{visa_type}")
def get_attorney_rankings(visa_type: str, country: str = "US"):
    return attorney_analytics.rank_attorneys(visa_type, country)

@app.get("/api/attorney-analytics/{attorney_id}/trend")
def get_attorney_trend(attorney_id: str):
    return attorney_analytics.get_trend(attorney_id)

@app.post("/api/attorney-analytics/{attorney_id}/predict")
def predict_attorney_outcome(attorney_id: str, case_data: dict):
    return attorney_analytics.predict_outcome(attorney_id, case_data)

@app.get("/api/attorney-analytics/{attorney_id}/specializations")
def get_specializations(attorney_id: str):
    return attorney_analytics.get_specialization_depth(attorney_id)


# =============================================
# Tier 3: Community Forum endpoints
# =============================================

class ForumPostRequest(BaseModel):
    author_id: str
    title: str
    content: str
    category: str = "strategy"
    tags: list[str] = []

class ForumCommentRequest(BaseModel):
    author_id: str
    content: str

@app.post("/api/forum/posts", status_code=201)
def create_forum_post(req: ForumPostRequest):
    return community_forum.create_post(req.author_id, req.title, req.content, req.category, req.tags)

@app.get("/api/forum/posts")
def list_forum_posts(category: str | None = None, page: int = 1):
    return community_forum.list_posts(category=category, page=page)

@app.post("/api/forum/posts/{post_id}/comments")
def add_forum_comment(post_id: str, req: ForumCommentRequest):
    try:
        return community_forum.add_comment(post_id, req.author_id, req.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/forum/posts/{post_id}/vote")
def vote_forum_post(post_id: str, user_id: str, direction: int = 1):
    try:
        return community_forum.vote(post_id, user_id, direction)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/forum/trending")
def get_trending_posts():
    return community_forum.get_trending()

@app.get("/api/forum/search")
def search_forum(query: str):
    return community_forum.search_posts(query)

@app.get("/api/forum/reputation/{user_id}")
def get_forum_reputation(user_id: str):
    return community_forum.get_user_reputation(user_id)


# =============================================
# Tier 3: Benchmark Report endpoints
# =============================================

@app.get("/api/benchmark/{firm_id}/{year}")
def get_benchmark_report(firm_id: str, year: int):
    return benchmark_reports.generate_report(firm_id, year)

@app.get("/api/benchmark/industry/{year}")
def get_industry_averages(year: int):
    return benchmark_reports.get_industry_averages(year)

@app.get("/api/benchmark/{firm_id}/peers")
def compare_to_peers(firm_id: str, peer_group: str = "mid-size"):
    return benchmark_reports.compare_to_peers(firm_id, peer_group)

@app.get("/api/benchmark/{firm_id}/{year}/export")
def export_benchmark(firm_id: str, year: int, fmt: str = "json"):
    return benchmark_reports.export_report(firm_id, year, fmt)


# =============================================
# Tier 3: PWA endpoints
# =============================================

@app.get("/api/pwa/manifest")
def get_pwa_manifest():
    return pwa_service.get_manifest()

@app.get("/api/pwa/sw-config")
def get_sw_config():
    return pwa_service.get_service_worker_config()

@app.get("/api/pwa/offline-data/{user_id}")
def get_offline_data(user_id: str):
    return pwa_service.get_offline_data(user_id)

@app.post("/api/pwa/sync")
def sync_offline(user_id: str, changes: list[dict]):
    return pwa_service.sync_offline_changes(user_id, changes)

@app.post("/api/pwa/sms")
def send_sms(phone: str, message: str):
    return pwa_service.send_sms_update(phone, message)

@app.get("/api/pwa/push/{user_id}")
def get_push_config(user_id: str):
    return pwa_service.get_push_subscription(user_id)


# =============================================
# Competitor Intel endpoints (internal)
# =============================================

@app.get("/api/intel/competitors")
def get_all_competitors():
    return competitor_intel.get_all_competitors()

@app.get("/api/intel/competitors/{name}")
def get_competitor(name: str):
    result = competitor_intel.get_competitor(name)
    if not result:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return result

@app.get("/api/intel/threat-matrix")
def get_threat_matrix():
    return competitor_intel.get_threat_matrix()

@app.get("/api/intel/feature-gaps")
def get_feature_gaps():
    return competitor_intel.get_feature_gaps()

@app.get("/api/intel/advantages")
def get_advantages():
    return competitor_intel.get_advantages()


# =============================================
# Deep HRIS Integration endpoints (counter Deel)
# =============================================

@app.post("/api/hris-deep/lifecycle-event")
def handle_lifecycle_event(event: dict):
    return hris_deep.handle_lifecycle_event(event)

@app.get("/api/hris-deep/payroll-alerts")
def get_payroll_alerts(company_id: str = ""):
    return hris_deep.get_payroll_immigration_alerts(company_id)

@app.post("/api/hris-deep/screen-new-hire")
def screen_new_hire(employee_data: dict):
    return hris_deep.screen_new_hire(employee_data)

@app.get("/api/hris-deep/screening-queue")
def get_screening_queue():
    return hris_deep.get_screening_queue()

@app.get("/api/hris-deep/workforce-snapshot/{company_id}")
def get_workforce_snapshot(company_id: str):
    return hris_deep.get_workforce_immigration_snapshot(company_id)

@app.post("/api/hris-deep/import-deel")
def import_from_deel(data: list[dict]):
    return hris_deep.import_from_deel(data)

@app.get("/api/hris-deep/event-log")
def get_hris_event_log(employee_id: str = ""):
    return hris_deep.get_event_log(employee_id or None)


# =============================================
# Time-Savings Benchmarking endpoints
# =============================================

@app.get("/api/benchmarks/platform")
def get_platform_benchmarks():
    return benchmarking.get_platform_benchmarks()

@app.get("/api/benchmarks/competitor-comparison")
def get_benchmark_comparison():
    return benchmarking.get_competitor_comparison()

@app.post("/api/benchmarks/firm-roi")
def calculate_firm_roi(firm_data: dict):
    return benchmarking.calculate_firm_roi(firm_data)

@app.post("/api/benchmarks/log-task")
def log_benchmark_task(task_data: dict):
    return benchmarking.log_task_completion(task_data)

@app.get("/api/benchmarks/aggregate")
def get_aggregate_benchmarks():
    return benchmarking.get_aggregate_metrics()


# =============================================
# Flat-Rate Pricing endpoints (counter Alma)
# =============================================

@app.get("/api/pricing/templates")
def get_pricing_templates(visa_type: str = ""):
    return flat_rate.get_package_templates(visa_type or None)

@app.post("/api/pricing/packages")
def create_pricing_package(attorney_id: str, package_data: dict):
    return flat_rate.create_attorney_package(attorney_id, package_data)

@app.get("/api/pricing/packages/{attorney_id}")
def get_attorney_packages(attorney_id: str):
    return flat_rate.get_attorney_packages(attorney_id)

@app.get("/api/pricing/marketplace")
def get_marketplace_packages(visa_type: str = ""):
    return flat_rate.get_published_packages(visa_type or None)

@app.post("/api/pricing/engagements")
def create_pricing_engagement(package_id: str, applicant_id: str, attorney_id: str):
    return flat_rate.create_engagement(package_id, applicant_id, attorney_id)

@app.get("/api/pricing/engagements/{engagement_id}")
def get_pricing_engagement(engagement_id: str):
    result = flat_rate.get_engagement(engagement_id)
    if not result:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return result

@app.patch("/api/pricing/engagements/{engagement_id}/milestones/{milestone_order}")
def advance_pricing_milestone(engagement_id: str, milestone_order: int):
    result = flat_rate.advance_milestone(engagement_id, milestone_order)
    if not result:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return result

@app.get("/api/pricing/compare-models")
def compare_pricing_models():
    return flat_rate.compare_pricing_models()


# =============================================
# USCIS Client API endpoints (developer.uscis.gov)
# =============================================

@app.get("/api/uscis-client/validate/{receipt_number}")
def validate_receipt(receipt_number: str):
    return uscis_client.validate_receipt_number(receipt_number)

@app.get("/api/uscis-client/status/{receipt_number}")
def get_uscis_status(receipt_number: str):
    result = uscis_client.get_case_status(receipt_number)
    if "error" in result and "receipt_number" not in result.get("status", {}):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/uscis-client/bulk-status")
def bulk_uscis_status(receipt_numbers: list[str]):
    return uscis_client.bulk_status_check(receipt_numbers)

@app.get("/api/uscis-client/processing-times/{form_type}")
def get_uscis_processing_times(form_type: str):
    result = uscis_client.get_processing_times(form_type)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown form type: {form_type}")
    return result

@app.get("/api/uscis-client/processing-times")
def get_all_uscis_processing_times():
    return uscis_client.get_all_processing_times()

@app.post("/api/uscis-client/subscribe")
def subscribe_uscis_updates(receipt_number: str, webhook_url: str = "", email: str = ""):
    return uscis_client.subscribe_to_updates(receipt_number, webhook_url, email)

@app.get("/api/uscis-client/subscriptions")
def get_uscis_subscriptions(receipt_number: str = ""):
    return uscis_client.get_subscriptions(receipt_number or None)

@app.get("/api/uscis-client/status-categories")
def get_uscis_status_categories():
    return uscis_client.get_status_categories()

@app.post("/api/uscis-client/detect-changes")
def detect_uscis_changes():
    return uscis_client.detect_status_changes()


# =============================================
# International Competitive Intelligence Crawler
# =============================================

@app.get("/api/crawler/sources")
def get_crawl_sources(region: str = ""):
    return crawler.get_crawl_sources(region or None)

@app.get("/api/crawler/keywords")
def get_crawl_keywords():
    return crawler.get_crawl_keywords()

@app.post("/api/crawler/keywords")
def add_crawl_keyword(keyword: str):
    return crawler.add_crawl_keyword(keyword)

@app.post("/api/crawler/run")
def run_crawl(region: str = "global"):
    return crawler.run_crawl(region)

@app.get("/api/crawler/log")
def get_crawl_log(limit: int = 20):
    return crawler.get_crawl_log(limit)

@app.get("/api/crawler/signals")
def get_crawler_signals(
    region: str = "", signal_type: str = "", threat_level: str = "", status: str = "", limit: int = 50
):
    return crawler.get_signals(
        region=region or None, signal_type=signal_type or None,
        threat_level=threat_level or None, status=status or None, limit=limit,
    )

@app.post("/api/crawler/signals")
def add_crawler_signal(signal_data: dict):
    return crawler.add_signal(signal_data)

@app.patch("/api/crawler/signals/{signal_id}")
def update_crawler_signal(signal_id: str, status: str, action: str):
    result = crawler.update_signal_response(signal_id, status, action)
    if not result:
        raise HTTPException(status_code=404, detail="Signal not found")
    return result

@app.get("/api/crawler/dashboard")
def get_threat_dashboard():
    return crawler.get_threat_dashboard()

@app.get("/api/crawler/watchlist")
def get_crawler_watchlist():
    return crawler.get_watchlist()

@app.post("/api/crawler/watchlist")
def add_to_crawler_watchlist(entity_data: dict):
    return crawler.add_to_watchlist(entity_data)

@app.delete("/api/crawler/watchlist/{entity_id}")
def remove_from_crawler_watchlist(entity_id: str):
    crawler.remove_from_watchlist(entity_id)
    return {"status": "removed"}

@app.get("/api/crawler/feature-landscape")
def get_feature_landscape():
    return crawler.get_feature_landscape()


# =============================================
# AI Intake Engine endpoints (magical onboarding heart)
# =============================================

class IntakeStartRequest(BaseModel):
    visa_type: str

class IntakeAnswersRequest(BaseModel):
    answers: dict

@app.get("/api/intake/visa-types")
def list_intake_visa_types(country: str | None = None, family: str | None = None):
    return intake_engine.list_visa_types(country=country, family=family)

@app.get("/api/intake/visa-types/{visa_type}/questionnaire")
def get_intake_questionnaire(visa_type: str):
    try:
        return intake_engine.get_questionnaire(visa_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/intake/sessions", status_code=201)
def start_intake_session(req: IntakeStartRequest, user: UserOut = Depends(get_current_user)):
    try:
        return intake_engine.start_session(user.id, req.visa_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/intake/sessions/{session_id}")
def get_intake_session(session_id: str, user: UserOut = Depends(get_current_user)):
    s = intake_engine.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return s

@app.get("/api/intake/sessions")
def list_intake_sessions(user: UserOut = Depends(get_current_user)):
    return intake_engine.list_sessions(user.id)

@app.post("/api/intake/sessions/{session_id}/answers")
def submit_intake_answers(session_id: str, req: IntakeAnswersRequest, user: UserOut = Depends(get_current_user)):
    s = intake_engine.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return intake_engine.submit_answers(session_id, req.answers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/intake/validate")
def validate_intake(visa_type: str, answers: dict):
    try:
        return intake_engine.validate_answers(visa_type, answers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/intake/document-checklist")
def get_intake_document_checklist(visa_type: str, answers: dict | None = None):
    try:
        return intake_engine.get_document_checklist(visa_type, answers or {})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/intake/score-strength")
def score_intake_strength(visa_type: str, answers: dict):
    try:
        return intake_engine.score_strength(visa_type, answers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/intake/red-flags")
def detect_intake_red_flags(visa_type: str, answers: dict, applicant: dict | None = None):
    return intake_engine.detect_red_flags(visa_type, answers, applicant)

@app.get("/api/intake/sessions/{session_id}/summary")
def get_intake_summary(session_id: str, user: UserOut = Depends(get_current_user)):
    s = intake_engine.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return intake_engine.get_intake_summary(session_id)


# =============================================
# RFE Predictor endpoints
# =============================================

class RFEPredictRequest(BaseModel):
    visa_type: str
    case_profile: dict

@app.post("/api/rfe-predictor/predict")
def predict_rfe(req: RFEPredictRequest):
    return rfe_predictor.predict(req.visa_type, req.case_profile)

@app.get("/api/rfe-predictor/triggers/{visa_type}")
def list_rfe_triggers(visa_type: str):
    return rfe_predictor.list_known_triggers(visa_type)

@app.get("/api/rfe-predictor/baselines")
def get_rfe_baselines():
    return rfe_predictor.get_industry_baselines()


# =============================================
# Conflict-of-Interest Check endpoints
# =============================================

class ConflictCheckRequest(BaseModel):
    prospect: dict
    firm_id: str | None = None

class EthicsWallRequest(BaseModel):
    case_id: str
    walled_off_user_ids: list[str]
    reason: str

@app.post("/api/conflict-check/clients")
def register_conflict_client(client: dict):
    return conflict_check.register_client(client)

@app.post("/api/conflict-check/cases")
def register_conflict_case(case: dict):
    return conflict_check.register_case(case)

@app.get("/api/conflict-check/clients")
def list_conflict_clients(attorney_id: str | None = None, firm_id: str | None = None):
    return conflict_check.list_clients(attorney_id=attorney_id, firm_id=firm_id)

@app.get("/api/conflict-check/cases")
def list_conflict_cases(attorney_id: str | None = None, firm_id: str | None = None):
    return conflict_check.list_cases(attorney_id=attorney_id, firm_id=firm_id)

@app.post("/api/conflict-check/check")
def run_conflict_check(req: ConflictCheckRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return conflict_check.check_new_case(req.prospect, attorney_id=user.id, firm_id=req.firm_id)

@app.get("/api/conflict-check/log")
def get_conflict_log(attorney_id: str | None = None, firm_id: str | None = None, limit: int = 100):
    return conflict_check.get_check_log(attorney_id=attorney_id, firm_id=firm_id, limit=limit)

@app.get("/api/conflict-check/audit-summary")
def get_conflict_audit_summary():
    return conflict_check.get_audit_summary()

@app.post("/api/conflict-check/walls")
def create_ethics_wall(req: EthicsWallRequest):
    return conflict_check.create_ethics_wall(req.case_id, req.walled_off_user_ids, req.reason)

@app.get("/api/conflict-check/walls")
def list_ethics_walls(case_id: str | None = None):
    return conflict_check.list_ethics_walls(case_id=case_id)

@app.delete("/api/conflict-check/walls/{wall_id}", status_code=204)
def deactivate_ethics_wall(wall_id: str):
    if conflict_check.deactivate_ethics_wall(wall_id) is None:
        raise HTTPException(status_code=404, detail="Wall not found")


# =============================================
# Magical Onboarding endpoints
# =============================================

class OnboardingStepRequest(BaseModel):
    step_name: str
    data: dict

@app.post("/api/onboarding/applicant/start", status_code=201)
def start_applicant_onboarding(user: UserOut = Depends(get_current_user)):
    return onboarding.start_applicant_onboarding(user.id)

@app.post("/api/onboarding/attorney/start", status_code=201)
def start_attorney_onboarding(user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return onboarding.start_attorney_onboarding(user.id)

@app.get("/api/onboarding/sessions/{session_id}")
def get_onboarding_session(session_id: str, user: UserOut = Depends(get_current_user)):
    s = onboarding.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return s

@app.get("/api/onboarding/me")
def get_my_onboarding(user: UserOut = Depends(get_current_user)):
    role = "attorney" if user.role == UserRole.ATTORNEY else "applicant"
    s = onboarding.get_session_for_user(user.id, role)
    if s is None:
        if role == "attorney":
            return onboarding.start_attorney_onboarding(user.id)
        return onboarding.start_applicant_onboarding(user.id)
    return s

@app.post("/api/onboarding/sessions/{session_id}/steps")
def submit_onboarding_step(session_id: str, req: OnboardingStepRequest, user: UserOut = Depends(get_current_user)):
    s = onboarding.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return onboarding.submit_step(session_id, req.step_name, req.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.delete("/api/onboarding/sessions/{session_id}/steps/{step_name}")
def reset_onboarding_step(session_id: str, step_name: str, user: UserOut = Depends(get_current_user)):
    s = onboarding.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return onboarding.reset_step(session_id, step_name)


# =============================================
# Document Intake Pipeline endpoints
# =============================================

class DocumentUploadRequest(BaseModel):
    session_id: str | None = None
    filename: str
    size_bytes: int
    mime_type: str = ""
    declared_type: str | None = None
    page_count: int = 1
    resolution_dpi: int | None = None
    content_hash: str | None = None

class DocumentReconcileRequest(BaseModel):
    session_id: str
    visa_type: str
    intake_answers: dict | None = None

@app.get("/api/documents-intake/types")
def list_document_types():
    return DocumentIntakeService.list_supported_document_types()

@app.post("/api/documents-intake/upload", status_code=201)
def upload_document(req: DocumentUploadRequest, user: UserOut = Depends(get_current_user)):
    return document_intake.upload(
        applicant_id=user.id,
        session_id=req.session_id,
        filename=req.filename,
        size_bytes=req.size_bytes,
        mime_type=req.mime_type,
        declared_type=req.declared_type,
        page_count=req.page_count,
        resolution_dpi=req.resolution_dpi,
        content_hash=req.content_hash,
    )

@app.get("/api/documents-intake")
def list_uploaded_documents(session_id: str | None = None, user: UserOut = Depends(get_current_user)):
    return document_intake.list_documents(applicant_id=user.id, session_id=session_id)

@app.get("/api/documents-intake/{doc_id}")
def get_uploaded_document(doc_id: str, user: UserOut = Depends(get_current_user)):
    d = document_intake.get_document(doc_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if d["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return d

@app.delete("/api/documents-intake/{doc_id}", status_code=204)
def delete_uploaded_document(doc_id: str, user: UserOut = Depends(get_current_user)):
    d = document_intake.get_document(doc_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if d["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    document_intake.delete_document(doc_id)

@app.post("/api/documents-intake/reconcile")
def reconcile_documents(req: DocumentReconcileRequest, user: UserOut = Depends(get_current_user)):
    intake_session = intake_engine.get_session(req.session_id)
    if intake_session is None:
        raise HTTPException(status_code=404, detail="Intake session not found")
    if intake_session["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    answers = req.intake_answers or intake_session["answers"]
    checklist = intake_engine.get_document_checklist(req.visa_type, answers)
    return document_intake.reconcile_against_checklist(
        applicant_id=user.id,
        session_id=req.session_id,
        checklist=checklist,
        intake_answers=answers,
    )


# =============================================
# Attorney Match endpoints (intake-aware)
# =============================================

class AttorneyMatchRequest(BaseModel):
    visa_type: str
    country: str
    applicant_languages: list[str] | None = None
    red_flag_codes: list[str] | None = None
    urgency: str = "standard"
    limit: int = 5

class AttorneyMatchSessionRequest(BaseModel):
    session_id: str
    applicant_languages: list[str] | None = None
    limit: int = 5

@app.get("/api/match/attorneys")
def list_match_attorneys(country: str | None = None):
    return attorney_match.list_attorneys(country=country, verified_only=True, accepting_only=True)

@app.post("/api/match/run")
def run_attorney_match(req: AttorneyMatchRequest):
    return attorney_match.match(
        visa_type=req.visa_type,
        country=req.country,
        applicant_languages=req.applicant_languages,
        red_flag_codes=req.red_flag_codes,
        urgency=req.urgency,
        limit=req.limit,
    )

@app.post("/api/match/from-session")
def match_from_intake_session(req: AttorneyMatchSessionRequest, user: UserOut = Depends(get_current_user)):
    s = intake_engine.get_session(req.session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Intake session not found")
    if s["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    summary = intake_engine.get_intake_summary(req.session_id)
    summary["country"] = s["country"]
    return attorney_match.match_for_session(
        intake_summary=summary,
        applicant_languages=req.applicant_languages,
        limit=req.limit,
    )

@app.get("/api/match/log")
def get_match_log(limit: int = 50):
    return attorney_match.get_match_log(limit=limit)


# =============================================
# Smart Form Auto-Population endpoints
# =============================================

class FormPopulateRequest(BaseModel):
    form_id: str
    session_id: str | None = None
    intake_answers: dict | None = None
    applicant_profile: dict | None = None

class FormBundleRequest(BaseModel):
    visa_type: str
    session_id: str | None = None
    intake_answers: dict | None = None
    applicant_profile: dict | None = None

class FormFieldUpdate(BaseModel):
    field_id: str
    new_value: Any
    edited_by: str = "user"

@app.get("/api/forms")
def list_form_schemas(visa_type: str | None = None):
    return FormPopulationService.list_forms(visa_type=visa_type)

@app.get("/api/forms/{form_id}/schema")
def get_form_schema(form_id: str):
    s = FormPopulationService.get_form_schema(form_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Form not found")
    return s

@app.get("/api/forms/recommendations/{visa_type}")
def get_form_recommendations(visa_type: str):
    return {"visa_type": visa_type, "recommended_forms": FormPopulationService.list_recommended_forms_for_visa(visa_type)}

def _resolve_population_inputs(req: "FormPopulateRequest | FormBundleRequest", user: UserOut) -> tuple[dict, list[dict]]:
    """Pull answers from a session if provided, else use what was passed."""
    answers = req.intake_answers or {}
    extracted: list[dict] = []
    if req.session_id:
        s = intake_engine.get_session(req.session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Intake session not found")
        if s["applicant_id"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if not answers:
            answers = s["answers"]
        extracted = document_intake.list_documents(applicant_id=user.id, session_id=req.session_id)
    return answers, extracted

@app.post("/api/forms/populate", status_code=201)
def populate_form(req: FormPopulateRequest, user: UserOut = Depends(get_current_user)):
    answers, extracted = _resolve_population_inputs(req, user)
    try:
        return form_population.populate(
            form_id=req.form_id,
            applicant_id=user.id,
            intake_answers=answers,
            extracted_documents=extracted,
            applicant_profile=req.applicant_profile or {},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/forms/populate-bundle")
def populate_form_bundle(req: FormBundleRequest, user: UserOut = Depends(get_current_user)):
    answers, extracted = _resolve_population_inputs(req, user)
    return form_population.populate_bundle(
        applicant_id=user.id,
        visa_type=req.visa_type,
        intake_answers=answers,
        extracted_documents=extracted,
        applicant_profile=req.applicant_profile or {},
    )

@app.get("/api/forms/records")
def list_form_records(form_id: str | None = None, user: UserOut = Depends(get_current_user)):
    return form_population.list_records(applicant_id=user.id, form_id=form_id)

@app.get("/api/forms/records/{record_id}")
def get_form_record(record_id: str, user: UserOut = Depends(get_current_user)):
    rec = form_population.get_record(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Form record not found")
    if rec["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return rec

@app.patch("/api/forms/records/{record_id}/fields")
def update_form_field(record_id: str, update: FormFieldUpdate, user: UserOut = Depends(get_current_user)):
    rec = form_population.get_record(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Form record not found")
    if rec["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return form_population.update_field(record_id, update.field_id, update.new_value, edited_by=update.edited_by)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/forms/records/{record_id}/provenance")
def get_form_provenance(record_id: str, field_id: str | None = None, user: UserOut = Depends(get_current_user)):
    rec = form_population.get_record(record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Form record not found")
    if rec["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return form_population.get_provenance(record_id=record_id, field_id=field_id)


# =============================================
# Case Workspace endpoints (unified system of record)
# =============================================

class WorkspaceCreateRequest(BaseModel):
    visa_type: str
    country: str
    intake_session_id: str | None = None
    case_label: str | None = None
    attorney_id: str | None = None

class WorkspaceStatusUpdate(BaseModel):
    status: str
    reason: str = ""

class WorkspaceLinkFormRequest(BaseModel):
    form_record_id: str

class WorkspaceFilingRequest(BaseModel):
    receipt_number: str
    filed_date: str | None = None
    form_type: str | None = None
    auto_compute_deadlines: bool = True

class WorkspaceNoteRequest(BaseModel):
    body: str
    visibility: str = "internal"

class WorkspaceDeadlineRequest(BaseModel):
    label: str
    due_date: str
    kind: str = "general"

class WorkspaceAttorneyAssignRequest(BaseModel):
    attorney_id: str
    attorney_name: str = ""

class WorkspaceTimelineEventRequest(BaseModel):
    kind: str
    message: str
    metadata: dict | None = None

class WorkspaceRFEReceivedRequest(BaseModel):
    rfe_received_date: str
    response_window_days: int = 87

@app.post("/api/case-workspaces", status_code=201)
def create_case_workspace(req: WorkspaceCreateRequest, user: UserOut = Depends(get_current_user)):
    return case_workspace.create_workspace(
        applicant_id=user.id,
        visa_type=req.visa_type,
        country=req.country,
        intake_session_id=req.intake_session_id,
        attorney_id=req.attorney_id,
        case_label=req.case_label,
    )

@app.get("/api/case-workspaces")
def list_case_workspaces(status: str | None = None, user: UserOut = Depends(get_current_user)):
    if user.role == UserRole.ATTORNEY:
        return case_workspace.list_workspaces(attorney_id=user.id, status=status)
    return case_workspace.list_workspaces(applicant_id=user.id, status=status)

@app.get("/api/case-workspaces/{ws_id}")
def get_case_workspace(ws_id: str, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ws

@app.get("/api/case-workspaces/{ws_id}/snapshot")
def get_case_workspace_snapshot(ws_id: str, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.get_snapshot(ws_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.patch("/api/case-workspaces/{ws_id}/status")
def update_case_workspace_status(ws_id: str, req: WorkspaceStatusUpdate, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.update_status(ws_id, req.status, req.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/case-workspaces/{ws_id}/forms")
def link_workspace_form(ws_id: str, req: WorkspaceLinkFormRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.link_form_record(ws_id, req.form_record_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/case-workspaces/{ws_id}/attorney")
def assign_workspace_attorney(ws_id: str, req: WorkspaceAttorneyAssignRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the applicant can assign the attorney")
    try:
        return case_workspace.assign_attorney(ws_id, req.attorney_id, req.attorney_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/case-workspaces/{ws_id}/filing")
def record_workspace_filing(ws_id: str, req: WorkspaceFilingRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned attorney can record a filing")
    try:
        case_workspace.record_filing(ws_id, req.receipt_number, req.filed_date)
        if req.auto_compute_deadlines and req.form_type and req.filed_date:
            case_workspace.auto_compute_deadlines_from_filing(ws_id, req.filed_date, req.form_type)
        return case_workspace.get_workspace(ws_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/case-workspaces/{ws_id}/notes")
def add_workspace_note(ws_id: str, req: WorkspaceNoteRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.add_note(ws_id, user.id, req.body, req.visibility)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/case-workspaces/{ws_id}/notes")
def list_workspace_notes(ws_id: str, visibility: str | None = None, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return case_workspace.list_notes(ws_id, visibility=visibility)

@app.post("/api/case-workspaces/{ws_id}/deadlines")
def add_workspace_deadline(ws_id: str, req: WorkspaceDeadlineRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.add_deadline(ws_id, req.label, req.due_date, kind=req.kind, source="manual")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/case-workspaces/{ws_id}/deadlines/{deadline_id}/complete")
def complete_workspace_deadline(ws_id: str, deadline_id: str, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = case_workspace.complete_deadline(ws_id, deadline_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return result

@app.get("/api/case-workspaces/{ws_id}/deadlines")
def list_workspace_deadlines(ws_id: str, include_completed: bool = False, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return case_workspace.list_deadlines(ws_id, include_completed=include_completed)

@app.post("/api/case-workspaces/{ws_id}/timeline")
def add_workspace_timeline_event(ws_id: str, req: WorkspaceTimelineEventRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return case_workspace.add_timeline_event(ws_id, req.kind, req.message, req.metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/case-workspaces/{ws_id}/timeline")
def get_workspace_timeline(ws_id: str, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return case_workspace.get_timeline(ws_id)

@app.post("/api/case-workspaces/{ws_id}/rfe-received")
def record_workspace_rfe(ws_id: str, req: WorkspaceRFEReceivedRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.get("attorney_id") != user.id and ws["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        case_workspace.update_status(ws_id, "rfe", "RFE received")
        return case_workspace.add_rfe_response_deadline(ws_id, req.rfe_received_date, req.response_window_days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# =============================================
# Calendar Sync endpoints
# =============================================

from fastapi.responses import PlainTextResponse  # noqa: E402

class CalendarSubscriptionRequest(BaseModel):
    scope: str = "applicant"
    workspace_id: str | None = None
    label: str = ""

class CalendarOAuthConnectRequest(BaseModel):
    provider: str
    oauth_payload: dict

class CalendarPushRequest(BaseModel):
    workspace_id: str

@app.get("/api/calendar/providers")
def list_calendar_providers():
    return CalendarSyncService.list_supported_providers()

@app.post("/api/calendar/subscriptions", status_code=201)
def create_calendar_subscription(req: CalendarSubscriptionRequest, user: UserOut = Depends(get_current_user)):
    try:
        return calendar_sync.create_subscription(
            user_id=user.id,
            scope=req.scope,
            workspace_id=req.workspace_id,
            label=req.label,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/calendar/subscriptions")
def list_calendar_subscriptions(user: UserOut = Depends(get_current_user)):
    return calendar_sync.list_subscriptions(user_id=user.id)

@app.delete("/api/calendar/subscriptions/{token}", status_code=204)
def revoke_calendar_subscription(token: str, user: UserOut = Depends(get_current_user)):
    sub = calendar_sync.get_subscription(token)
    if sub is None or sub["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")
    calendar_sync.revoke_subscription(token)

@app.post("/api/calendar/subscriptions/{token}/rotate")
def rotate_calendar_subscription(token: str, user: UserOut = Depends(get_current_user)):
    sub = calendar_sync.get_subscription(token)
    if sub is None or sub["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")
    new = calendar_sync.rotate_subscription(token)
    if new is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return new

@app.get("/api/calendar/feed/{token}.ics", response_class=PlainTextResponse)
def get_calendar_feed(token: str):
    """Public ICS endpoint — calendar clients subscribe to this URL.
    Authentication is via the opaque token in the URL."""
    ics = calendar_sync.render_feed_for_token(token)
    if ics is None:
        raise HTTPException(status_code=404, detail="Subscription not found or revoked")
    return PlainTextResponse(content=ics, media_type="text/calendar; charset=utf-8")

@app.get("/api/calendar/workspace/{ws_id}.ics", response_class=PlainTextResponse)
def get_workspace_calendar_snapshot(ws_id: str, user: UserOut = Depends(get_current_user)):
    """One-shot ICS download for a single workspace (auth required, no subscription needed)."""
    ws = case_workspace.get_workspace(ws_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    deadlines = case_workspace.list_deadlines(ws_id, include_completed=False)
    ics = calendar_sync.render_workspace_calendar(ws, deadlines)
    return PlainTextResponse(content=ics, media_type="text/calendar; charset=utf-8")

@app.post("/api/calendar/connections", status_code=201)
def connect_calendar_provider(req: CalendarOAuthConnectRequest, user: UserOut = Depends(get_current_user)):
    try:
        return calendar_sync.connect_provider(user.id, req.provider, req.oauth_payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/calendar/connections")
def list_calendar_connections(user: UserOut = Depends(get_current_user)):
    return calendar_sync.list_connections(user_id=user.id)

@app.delete("/api/calendar/connections/{connection_id}", status_code=204)
def disconnect_calendar_connection(connection_id: str, user: UserOut = Depends(get_current_user)):
    conns = [c for c in calendar_sync.list_connections(user_id=user.id) if c["id"] == connection_id]
    if not conns:
        raise HTTPException(status_code=404, detail="Connection not found")
    calendar_sync.disconnect(connection_id)

@app.post("/api/calendar/connections/{connection_id}/push")
def push_to_calendar(connection_id: str, req: CalendarPushRequest, user: UserOut = Depends(get_current_user)):
    conns = [c for c in calendar_sync.list_connections(user_id=user.id) if c["id"] == connection_id]
    if not conns:
        raise HTTPException(status_code=404, detail="Connection not found")
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return calendar_sync.push_workspace_to_calendar(connection_id, req.workspace_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/calendar/connections/{connection_id}/log")
def get_calendar_push_log(connection_id: str, user: UserOut = Depends(get_current_user)):
    conns = [c for c in calendar_sync.list_connections(user_id=user.id) if c["id"] == connection_id]
    if not conns:
        raise HTTPException(status_code=404, detail="Connection not found")
    return calendar_sync.get_push_log(connection_id=connection_id)


# =============================================
# AI Client Chatbot endpoints
# =============================================

class ChatbotConvoCreateRequest(BaseModel):
    workspace_id: str

class ChatbotAskRequest(BaseModel):
    body: str

class ChatbotAttorneyMessageRequest(BaseModel):
    body: str

class ChatbotResolveHandoffRequest(BaseModel):
    response_body: str = ""

@app.get("/api/chatbot/intents")
def list_chatbot_intents():
    return ClientChatbotService.list_supported_intents()

@app.post("/api/chatbot/conversations", status_code=201)
def chatbot_get_or_create(req: ChatbotConvoCreateRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return client_chatbot.get_or_create_conversation(req.workspace_id, ws["applicant_id"])

@app.get("/api/chatbot/conversations")
def list_chatbot_conversations(workspace_id: str | None = None, user: UserOut = Depends(get_current_user)):
    if user.role == UserRole.ATTORNEY:
        # attorney sees conversations for workspaces they own
        atty_workspaces = {w["id"] for w in case_workspace.list_workspaces(attorney_id=user.id)}
        all_convos = client_chatbot.list_conversations(workspace_id=workspace_id)
        return [c for c in all_convos if c["workspace_id"] in atty_workspaces]
    return client_chatbot.list_conversations(applicant_id=user.id, workspace_id=workspace_id)

@app.get("/api/chatbot/conversations/{convo_id}/messages")
def get_chatbot_messages(convo_id: str, user: UserOut = Depends(get_current_user), limit: int = 100):
    convo = client_chatbot.get_conversation(convo_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ws = case_workspace.get_workspace(convo["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return client_chatbot.get_messages(convo_id, limit=limit)

@app.post("/api/chatbot/conversations/{convo_id}/ask")
def chatbot_ask(convo_id: str, req: ChatbotAskRequest, user: UserOut = Depends(get_current_user)):
    convo = client_chatbot.get_conversation(convo_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ws = case_workspace.get_workspace(convo["workspace_id"])
    if ws is None or ws["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the applicant can ask questions")
    try:
        return client_chatbot.ask(convo_id, req.body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/chatbot/conversations/{convo_id}/take-over")
def chatbot_attorney_take_over(convo_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    convo = client_chatbot.get_conversation(convo_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ws = case_workspace.get_workspace(convo["workspace_id"])
    if ws is None or ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned attorney")
    return client_chatbot.attorney_take_over(convo_id, user.id)

@app.post("/api/chatbot/conversations/{convo_id}/release")
def chatbot_attorney_release(convo_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    convo = client_chatbot.get_conversation(convo_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ws = case_workspace.get_workspace(convo["workspace_id"])
    if ws is None or ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned attorney")
    return client_chatbot.attorney_release(convo_id)

@app.post("/api/chatbot/conversations/{convo_id}/attorney-message")
def chatbot_attorney_post(convo_id: str, req: ChatbotAttorneyMessageRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    convo = client_chatbot.get_conversation(convo_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ws = case_workspace.get_workspace(convo["workspace_id"])
    if ws is None or ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned attorney")
    return client_chatbot.attorney_post_message(convo_id, user.id, req.body)

@app.get("/api/chatbot/handoffs")
def list_chatbot_handoffs(status: str | None = None, user: UserOut = Depends(get_current_user)):
    handoffs = client_chatbot.get_handoffs(status=status)
    if user.role == UserRole.ATTORNEY:
        atty_ws = {w["id"] for w in case_workspace.list_workspaces(attorney_id=user.id)}
        return [h for h in handoffs if h["workspace_id"] in atty_ws]
    return [h for h in handoffs if h["applicant_id"] == user.id]

@app.post("/api/chatbot/handoffs/{handoff_id}/resolve")
def resolve_chatbot_handoff(handoff_id: str, req: ChatbotResolveHandoffRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    result = client_chatbot.resolve_handoff(handoff_id, req.response_body)
    if result is None:
        raise HTTPException(status_code=404, detail="Handoff not found")
    return result


# =============================================
# Family Bundle Engine endpoints
# =============================================

class BundleCreateRequest(BaseModel):
    principal_workspace_id: str
    principal_visa_type: str
    label: str = ""

class BundleAddDependentRequest(BaseModel):
    relationship: str
    first_name: str
    last_name: str
    dob: str
    country: str = ""
    notes: str = ""

@app.get("/api/family-bundles/combinations")
def list_bundle_combinations():
    return FamilyBundleService.list_supported_combinations()

@app.post("/api/family-bundles", status_code=201)
def create_family_bundle(req: BundleCreateRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.principal_workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Principal workspace not found")
    if ws["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Only the applicant can create a family bundle")
    return family_bundle.create_bundle(
        applicant_id=user.id,
        principal_workspace_id=req.principal_workspace_id,
        principal_visa_type=req.principal_visa_type,
        label=req.label,
    )

@app.get("/api/family-bundles")
def list_family_bundles(user: UserOut = Depends(get_current_user)):
    return family_bundle.list_bundles(applicant_id=user.id)

@app.get("/api/family-bundles/{bundle_id}")
def get_family_bundle(bundle_id: str, user: UserOut = Depends(get_current_user)):
    b = family_bundle.get_bundle(bundle_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if b["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return b

@app.get("/api/family-bundles/{bundle_id}/snapshot")
def get_family_bundle_snapshot(bundle_id: str, user: UserOut = Depends(get_current_user)):
    b = family_bundle.get_bundle(bundle_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if b["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return family_bundle.get_bundle_snapshot(bundle_id)

@app.post("/api/family-bundles/{bundle_id}/dependents", status_code=201)
def add_family_dependent(bundle_id: str, req: BundleAddDependentRequest, user: UserOut = Depends(get_current_user)):
    b = family_bundle.get_bundle(bundle_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if b["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return family_bundle.add_dependent(
            bundle_id=bundle_id,
            relationship=req.relationship,
            first_name=req.first_name,
            last_name=req.last_name,
            dob=req.dob,
            country=req.country,
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/family-bundles/{bundle_id}/forms")
def list_family_bundle_forms(bundle_id: str, user: UserOut = Depends(get_current_user)):
    b = family_bundle.get_bundle(bundle_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if b["applicant_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return family_bundle.list_required_forms_for_bundle(bundle_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# =============================================
# Packet Assembly endpoints
# =============================================

from fastapi.responses import Response  # noqa: E402

class PacketAssembleRequest(BaseModel):
    workspace_id: str
    attorney_profile: dict | None = None
    include_strength_summary: bool = False

@app.post("/api/packets/assemble", status_code=201)
def assemble_packet(req: PacketAssembleRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return packet_assembly.assemble(
        workspace_id=req.workspace_id,
        attorney_profile=req.attorney_profile,
        include_strength_summary=req.include_strength_summary,
    )

@app.get("/api/packets")
def list_packets(workspace_id: str | None = None, user: UserOut = Depends(get_current_user)):
    if workspace_id:
        ws = case_workspace.get_workspace(workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return packet_assembly.list_packets(workspace_id=workspace_id)

@app.get("/api/packets/{packet_id}")
def get_packet(packet_id: str, user: UserOut = Depends(get_current_user)):
    p = packet_assembly.get_packet(packet_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Packet not found")
    ws = case_workspace.get_workspace(p["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return p

@app.get("/api/packets/{packet_id}/text", response_class=PlainTextResponse)
def get_packet_text(packet_id: str, user: UserOut = Depends(get_current_user)):
    p = packet_assembly.get_packet(packet_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Packet not found")
    ws = case_workspace.get_workspace(p["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=packet_assembly.render_text(p))

@app.get("/api/packets/{packet_id}/pdf")
def get_packet_pdf(packet_id: str, user: UserOut = Depends(get_current_user)):
    p = packet_assembly.get_packet(packet_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Packet not found")
    ws = case_workspace.get_workspace(p["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    pdf_bytes = packet_assembly.render_pdf(p)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="verom-packet-{packet_id[:8]}.pdf"'},
    )


# =============================================
# Regulatory Impact Hook endpoints
# =============================================

class RegulatoryEventIngest(BaseModel):
    title: str
    kind: str
    impact_predicate: dict
    severity: str = "advisory"
    source: str = "manual"
    effective_date: str | None = None
    summary: str = ""
    client_notification_template: str = ""
    attorney_action_template: str = ""
    link: str = ""

@app.get("/api/regulatory-impact/event-kinds")
def get_regulatory_event_kinds():
    return {"kinds": RegulatoryImpactService.list_event_kinds(), "severities": RegulatoryImpactService.list_severity_levels()}

@app.post("/api/regulatory-impact/events", status_code=201)
def ingest_regulatory_event(req: RegulatoryEventIngest, user: UserOut = Depends(get_current_user)):
    try:
        return regulatory_impact_engine.ingest_event(
            title=req.title,
            kind=req.kind,
            impact_predicate=req.impact_predicate,
            severity=req.severity,
            source=req.source,
            effective_date=req.effective_date,
            summary=req.summary,
            client_notification_template=req.client_notification_template,
            attorney_action_template=req.attorney_action_template,
            link=req.link,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/regulatory-impact/events")
def list_regulatory_events(kind: str | None = None, severity: str | None = None):
    return regulatory_impact_engine.list_events(kind=kind, severity=severity)

@app.get("/api/regulatory-impact/events/{event_id}")
def get_regulatory_event(event_id: str):
    e = regulatory_impact_engine.get_event(event_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return e

@app.post("/api/regulatory-impact/events/{event_id}/analyze")
def analyze_regulatory_event(event_id: str, only_active: bool = True, user: UserOut = Depends(get_current_user)):
    try:
        return regulatory_impact_engine.analyze_event(event_id, only_active=only_active)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/regulatory-impact/reports")
def list_regulatory_reports(user: UserOut = Depends(get_current_user)):
    if user.role == UserRole.ATTORNEY:
        return regulatory_impact_engine.list_reports(attorney_id=user.id)
    return regulatory_impact_engine.list_reports(applicant_id=user.id)

@app.get("/api/regulatory-impact/reports/{report_id}")
def get_regulatory_report(report_id: str, user: UserOut = Depends(get_current_user)):
    r = regulatory_impact_engine.get_report(report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


# =============================================
# Migration Importer endpoints
# =============================================

class MigrationPreviewRequest(BaseModel):
    csv_text: str
    profile_id: str | None = None

class MigrationImportRequest(BaseModel):
    csv_text: str
    profile_id: str | None = None
    dry_run: bool = False

@app.get("/api/migration-importer/profiles")
def list_migration_profiles():
    return MigrationImporterService.list_profiles()

@app.get("/api/migration-importer/profiles/{profile_id}")
def get_migration_profile(profile_id: str):
    p = MigrationImporterService.get_profile(profile_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

@app.post("/api/migration-importer/preview")
def preview_migration(req: MigrationPreviewRequest, user: UserOut = Depends(get_current_user)):
    return migration_importer.preview(req.csv_text, profile_id=req.profile_id)

@app.post("/api/migration-importer/import", status_code=201)
def run_migration_import(req: MigrationImportRequest, user: UserOut = Depends(get_current_user)):
    return migration_importer.run_import(
        applicant_owner_id=user.id,
        csv_text=req.csv_text,
        profile_id=req.profile_id,
        dry_run=req.dry_run,
    )

@app.get("/api/migration-importer/imports")
def list_migration_imports(user: UserOut = Depends(get_current_user)):
    return migration_importer.list_imports(owner_id=user.id)

@app.get("/api/migration-importer/imports/{import_id}")
def get_migration_import(import_id: str, user: UserOut = Depends(get_current_user)):
    r = migration_importer.get_import(import_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Import record not found")
    if r["applicant_owner_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return r


# =============================================
# Petition Letter Generator endpoints
# =============================================

class PetitionGenerateRequest(BaseModel):
    workspace_id: str
    petition_kind: str
    attorney_profile: dict | None = None
    force_include_weak_sections: bool = False

@app.get("/api/petition-letter/petitions")
def list_petitions():
    return PetitionLetterService.list_supported_petitions()

@app.get("/api/petition-letter/petitions/{petition_id}")
def get_petition_spec(petition_id: str):
    spec = PetitionLetterService.get_petition_spec(petition_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Petition spec not found")
    return spec

@app.post("/api/petition-letter/generate", status_code=201)
def generate_petition_letter(req: PetitionGenerateRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return petition_letter.generate(
            workspace_id=req.workspace_id,
            petition_kind=req.petition_kind,
            attorney_profile=req.attorney_profile,
            force_include_weak_sections=req.force_include_weak_sections,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/petition-letter/drafts")
def list_petition_drafts(workspace_id: str | None = None, user: UserOut = Depends(get_current_user)):
    if workspace_id:
        ws = case_workspace.get_workspace(workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return petition_letter.list_drafts(workspace_id=workspace_id)

@app.get("/api/petition-letter/drafts/{draft_id}")
def get_petition_draft(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = petition_letter.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return d

@app.get("/api/petition-letter/drafts/{draft_id}/text", response_class=PlainTextResponse)
def get_petition_draft_text(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = petition_letter.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=PetitionLetterService.render_text(d))

@app.get("/api/petition-letter/drafts/{draft_id}/review", response_class=PlainTextResponse)
def get_petition_draft_review(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = petition_letter.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=PetitionLetterService.render_review_text(d))


# =============================================
# RFE Response Drafter endpoints
# =============================================

class RFEResponseDraftRequest(BaseModel):
    workspace_id: str
    notice_text: str
    rfe_received_date: str | None = None
    attorney_profile: dict | None = None

class RFEParseRequest(BaseModel):
    notice_text: str

@app.get("/api/rfe-response/categories")
def list_rfe_response_categories():
    return RFEResponseService.list_categories()

@app.post("/api/rfe-response/parse")
def parse_rfe_notice(req: RFEParseRequest):
    return {"detected": RFEResponseService.parse_notice(req.notice_text)}

@app.post("/api/rfe-response/draft", status_code=201)
def draft_rfe_response(req: RFEResponseDraftRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return rfe_response.draft_response(
            workspace_id=req.workspace_id,
            notice_text=req.notice_text,
            rfe_received_date=req.rfe_received_date,
            attorney_profile=req.attorney_profile,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/rfe-response/drafts")
def list_rfe_response_drafts(workspace_id: str | None = None, user: UserOut = Depends(get_current_user)):
    if workspace_id:
        ws = case_workspace.get_workspace(workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return rfe_response.list_drafts(workspace_id=workspace_id)

@app.get("/api/rfe-response/drafts/{draft_id}")
def get_rfe_response_draft(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = rfe_response.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return d

@app.get("/api/rfe-response/drafts/{draft_id}/text", response_class=PlainTextResponse)
def get_rfe_response_text(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = rfe_response.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=RFEResponseService.render_text(d))

@app.get("/api/rfe-response/drafts/{draft_id}/review", response_class=PlainTextResponse)
def get_rfe_response_review(draft_id: str, user: UserOut = Depends(get_current_user)):
    d = rfe_response.get_draft(draft_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    ws = case_workspace.get_workspace(d["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=RFEResponseService.render_review_text(d))


# =============================================
# Storage / Audit Log endpoints
# =============================================

@app.get("/api/storage/namespaces")
def list_storage_namespaces(user: UserOut = Depends(get_current_user)):
    if persistent_store is None:
        return {"persistence_enabled": False, "namespaces": []}
    return {"persistence_enabled": True, "namespaces": persistent_store.list_namespaces()}

@app.get("/api/audit-log/persistent")
def get_persistent_audit_log(
    namespace: str | None = None,
    actor_id: str | None = None,
    target_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    user: UserOut = Depends(get_current_user),
):
    if persistent_store is None:
        return {"persistence_enabled": False, "entries": []}
    return {
        "persistence_enabled": True,
        "entries": persistent_store.get_log(
            namespace=namespace, actor_id=actor_id, target_id=target_id,
            action=action, limit=limit,
        ),
    }

@app.get("/api/audit-log/summary")
def get_persistent_audit_summary(user: UserOut = Depends(get_current_user)):
    if persistent_store is None:
        return {"persistence_enabled": False}
    return {"persistence_enabled": True, **persistent_store.get_audit_summary()}


# =============================================
# Support Letter Generator endpoints
# =============================================

class SupportLetterGenerateRequest(BaseModel):
    workspace_id: str
    letter_kind: str
    author_profile: dict | None = None
    criterion_focus: str | None = None
    custom_facts: dict | None = None

class SupportLetterBulkRequest(BaseModel):
    workspace_id: str
    plan: list[dict]

@app.get("/api/support-letter/kinds")
def list_support_letter_kinds(visa_type: str | None = None):
    return SupportLetterService.list_letter_kinds(visa_type=visa_type)

@app.get("/api/support-letter/kinds/{kind_id}")
def get_support_letter_template(kind_id: str):
    t = SupportLetterService.get_template(kind_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Letter kind not found")
    return t

@app.post("/api/support-letter/generate", status_code=201)
def generate_support_letter(req: SupportLetterGenerateRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return support_letter.generate(
            workspace_id=req.workspace_id,
            letter_kind=req.letter_kind,
            author_profile=req.author_profile,
            criterion_focus=req.criterion_focus,
            custom_facts=req.custom_facts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/support-letter/generate-bulk", status_code=201)
def generate_support_letter_bulk(req: SupportLetterBulkRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return support_letter.generate_bulk(workspace_id=req.workspace_id, plan=req.plan)

@app.get("/api/support-letter/letters")
def list_support_letters(workspace_id: str | None = None, letter_kind: str | None = None, user: UserOut = Depends(get_current_user)):
    if workspace_id:
        ws = case_workspace.get_workspace(workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return support_letter.list_letters(workspace_id=workspace_id, letter_kind=letter_kind)

@app.get("/api/support-letter/letters/{letter_id}")
def get_support_letter(letter_id: str, user: UserOut = Depends(get_current_user)):
    l = support_letter.get_letter(letter_id)
    if l is None:
        raise HTTPException(status_code=404, detail="Letter not found")
    ws = case_workspace.get_workspace(l["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return l

@app.get("/api/support-letter/letters/{letter_id}/text", response_class=PlainTextResponse)
def get_support_letter_text(letter_id: str, user: UserOut = Depends(get_current_user)):
    l = support_letter.get_letter(letter_id)
    if l is None:
        raise HTTPException(status_code=404, detail="Letter not found")
    ws = case_workspace.get_workspace(l["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=SupportLetterService.render_text(l))

@app.get("/api/support-letter/letters/{letter_id}/review", response_class=PlainTextResponse)
def get_support_letter_review(letter_id: str, user: UserOut = Depends(get_current_user)):
    l = support_letter.get_letter(letter_id)
    if l is None:
        raise HTTPException(status_code=404, detail="Letter not found")
    ws = case_workspace.get_workspace(l["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return PlainTextResponse(content=SupportLetterService.render_review_text(l))


# =============================================
# Completeness Scorer endpoints
# =============================================

class CompletenessScoreRequest(BaseModel):
    workspace_id: str
    petition_kind: str

@app.get("/api/completeness-scorer/petitions")
def list_completeness_petitions():
    return CompletenessScorerService.list_supported_petitions()

@app.get("/api/completeness-scorer/petitions/{petition_kind}/factors")
def get_completeness_factors(petition_kind: str):
    f = CompletenessScorerService.get_factor_set(petition_kind)
    if f is None:
        raise HTTPException(status_code=404, detail="Petition kind not supported")
    return f

@app.post("/api/completeness-scorer/score", status_code=201)
def score_completeness(req: CompletenessScoreRequest, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(req.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return completeness_scorer.score(req.workspace_id, req.petition_kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/completeness-scorer/reports")
def list_completeness_reports(workspace_id: str | None = None, user: UserOut = Depends(get_current_user)):
    if workspace_id:
        ws = case_workspace.get_workspace(workspace_id)
        if ws is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return completeness_scorer.list_reports(workspace_id=workspace_id)

@app.get("/api/completeness-scorer/reports/{report_id}")
def get_completeness_report(report_id: str, user: UserOut = Depends(get_current_user)):
    r = completeness_scorer.get_report(report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    ws = case_workspace.get_workspace(r["workspace_id"])
    if ws is None or (ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return r


# =============================================
# SOC Code Selection endpoints
# =============================================

class SocRecommendRequest(BaseModel):
    job_title: str
    duties: str = ""
    skills: list[str] | None = None
    prefer_managerial: bool = False
    prefer_research: bool = False
    limit: int = 5

@app.get("/api/soc-codes/catalog")
def list_soc_catalog(search: str | None = None, limit: int = 100):
    return SocCodeService.list_catalog(limit=limit, search=search)

@app.get("/api/soc-codes/{soc_code}")
def get_soc_entry(soc_code: str):
    e = SocCodeService.get_by_code(soc_code)
    if e is None:
        raise HTTPException(status_code=404, detail="SOC code not found")
    return e

@app.post("/api/soc-codes/recommend")
def recommend_soc_codes(req: SocRecommendRequest):
    return soc_code_service.recommend(
        job_title=req.job_title,
        duties=req.duties,
        skills=req.skills or [],
        prefer_managerial=req.prefer_managerial,
        prefer_research=req.prefer_research,
        limit=req.limit,
    )


# =============================================
# AI Document Q&A endpoints
# =============================================

class DocQAIngestRequest(BaseModel):
    text: str
    label: str = ""

class DocQAAskRequest(BaseModel):
    question: str

@app.get("/api/document-qa/doc-types")
def list_qa_doc_types():
    return DocumentQAService.list_supported_doc_types()

@app.get("/api/document-qa/intents")
def list_qa_intents():
    return DocumentQAService.list_supported_intents()

@app.post("/api/document-qa/ingest", status_code=201)
def ingest_qa_document(req: DocQAIngestRequest, user: UserOut = Depends(get_current_user)):
    try:
        return document_qa.ingest(text=req.text, label=req.label, uploader_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/document-qa/documents")
def list_qa_documents(user: UserOut = Depends(get_current_user)):
    return document_qa.list_documents(uploader_id=user.id)

@app.get("/api/document-qa/documents/{doc_id}")
def get_qa_document(doc_id: str, user: UserOut = Depends(get_current_user)):
    d = document_qa.get_document(doc_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if d.get("uploader_id") and d["uploader_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return d

@app.post("/api/document-qa/documents/{doc_id}/ask")
def ask_qa_document(doc_id: str, req: DocQAAskRequest, user: UserOut = Depends(get_current_user)):
    d = document_qa.get_document(doc_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if d.get("uploader_id") and d["uploader_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return document_qa.ask(doc_id, req.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/document-qa/documents/{doc_id}/history")
def get_qa_history(doc_id: str, limit: int = 100, user: UserOut = Depends(get_current_user)):
    d = document_qa.get_document(doc_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if d.get("uploader_id") and d["uploader_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return document_qa.get_history(doc_id, limit=limit)


# =============================================
# Translation Service endpoints
# =============================================

class TranslateMessageRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str
    include_disclaimer: bool = True

@app.get("/api/translation/languages")
def list_translation_languages():
    return TranslationService.list_supported_languages()

@app.get("/api/translation/disclaimers")
def list_translation_disclaimers():
    return TranslationService.list_disclaimers()

@app.get("/api/translation/ui-keys")
def list_translation_ui_keys():
    return TranslationService.list_ui_keys()

@app.get("/api/translation/ui-strings/{lang}")
def get_ui_strings(lang: str):
    try:
        return TranslationService.get_ui_strings(lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/translation/translate")
def translate_message(req: TranslateMessageRequest):
    try:
        return translation_service.translate_message(
            text=req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            include_disclaimer=req.include_disclaimer,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# =============================================
# Time Tracking endpoints
# =============================================

class TimerStartRequest(BaseModel):
    workspace_id: str | None = None
    activity_type: str = "other"
    description: str = ""

class TimerStopRequest(BaseModel):
    description_override: str | None = None

class TimeEntryRequest(BaseModel):
    minutes: float
    activity_type: str = "other"
    workspace_id: str | None = None
    description: str = ""
    billable_override: bool | None = None
    entry_date: str | None = None

class BillingRateRequest(BaseModel):
    rate_per_hour: float
    currency: str = "USD"

@app.get("/api/time-tracking/activity-types")
def list_time_activity_types():
    return TimeTrackingService.list_activity_types()

@app.post("/api/time-tracking/billing-rate")
def set_my_billing_rate(req: BillingRateRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return time_tracking.set_billing_rate(user.id, req.rate_per_hour, req.currency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/time-tracking/billing-rate")
def get_my_billing_rate(user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    rate = time_tracking.get_billing_rate(user.id)
    if rate is None:
        return {"rate_per_hour": None}
    return rate

@app.post("/api/time-tracking/timers/start")
def start_timer(req: TimerStartRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return time_tracking.start_timer(
            attorney_id=user.id,
            workspace_id=req.workspace_id,
            activity_type=req.activity_type,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/time-tracking/timers/{timer_id}/stop")
def stop_timer(timer_id: str, req: TimerStopRequest | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    desc = req.description_override if req else None
    try:
        return time_tracking.stop_timer(timer_id, description_override=desc)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/time-tracking/timers/active")
def get_active_timer(user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    t = time_tracking.get_active_timer(user.id)
    return t or {"is_running": False}

@app.post("/api/time-tracking/entries", status_code=201)
def add_time_entry(req: TimeEntryRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return time_tracking.add_entry(
            attorney_id=user.id,
            minutes=req.minutes,
            activity_type=req.activity_type,
            workspace_id=req.workspace_id,
            description=req.description,
            billable_override=req.billable_override,
            entry_date=req.entry_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/time-tracking/entries")
def list_time_entries(
    workspace_id: str | None = None, billable: bool | None = None,
    since: str | None = None, until: str | None = None,
    user: UserOut = Depends(require_role(UserRole.ATTORNEY)),
):
    return time_tracking.list_entries(
        attorney_id=user.id, workspace_id=workspace_id,
        billable=billable, since=since, until=until,
    )

@app.patch("/api/time-tracking/entries/{entry_id}")
def update_time_entry(entry_id: str, req: TimeEntryRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return time_tracking.update_entry(
            entry_id=entry_id,
            minutes=req.minutes,
            description=req.description or None,
            billable=req.billable_override,
            activity_type=req.activity_type if req.activity_type != "other" else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.delete("/api/time-tracking/entries/{entry_id}", status_code=204)
def delete_time_entry(entry_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    if not time_tracking.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")

@app.get("/api/time-tracking/workspace-summary/{workspace_id}")
def get_workspace_time_summary(workspace_id: str, user: UserOut = Depends(get_current_user)):
    ws = case_workspace.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["applicant_id"] != user.id and ws.get("attorney_id") != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return time_tracking.workspace_summary(workspace_id)

@app.get("/api/time-tracking/attorney-summary")
def get_attorney_time_summary(since: str | None = None, until: str | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return time_tracking.attorney_summary(user.id, since=since, until=until)

@app.post("/api/time-tracking/invoices", status_code=201)
def generate_invoice(workspace_id: str, since: str | None = None, until: str | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return time_tracking.generate_invoice(workspace_id=workspace_id, since=since, until=until, attorney_id=user.id)

@app.get("/api/time-tracking/invoices")
def list_my_invoices(workspace_id: str | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return time_tracking.list_invoices(workspace_id=workspace_id, attorney_id=user.id)

@app.get("/api/time-tracking/invoices/{invoice_id}")
def get_invoice(invoice_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    inv = time_tracking.get_invoice(invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.get("attorney_id") and inv["attorney_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return inv


# =============================================
# Trust Accounting (IOLTA) endpoints
# =============================================

class TrustAccountRegisterRequest(BaseModel):
    firm_id: str
    account_name: str
    bank_name: str
    account_number_last4: str
    state: str
    currency: str = "USD"

class ClientLedgerOpenRequest(BaseModel):
    client_id: str
    client_name: str
    workspace_id: str | None = None

class TrustTransactionRequest(BaseModel):
    client_id: str
    kind: str
    amount: float
    description: str = ""
    external_reference: str = ""
    approved_by: str | None = None
    reason: str | None = None

class BankBalanceRequest(BaseModel):
    balance: float
    as_of: str | None = None

@app.get("/api/trust-accounting/transaction-kinds")
def list_trust_txn_kinds():
    return TrustAccountingService.list_transaction_kinds()

@app.post("/api/trust-accounting/accounts", status_code=201)
def register_trust_account(req: TrustAccountRegisterRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return trust_accounting.register_account(
        firm_id=req.firm_id, account_name=req.account_name,
        bank_name=req.bank_name, account_number_last4=req.account_number_last4,
        state=req.state, currency=req.currency,
    )

@app.get("/api/trust-accounting/accounts")
def list_trust_accounts(firm_id: str | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return trust_accounting.list_accounts(firm_id=firm_id)

@app.get("/api/trust-accounting/accounts/{account_id}")
def get_trust_account(account_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    a = trust_accounting.get_account(account_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return a

@app.post("/api/trust-accounting/accounts/{account_id}/client-ledgers", status_code=201)
def open_client_ledger(account_id: str, req: ClientLedgerOpenRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.open_client_ledger(account_id, req.client_id, req.client_name, req.workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/trust-accounting/accounts/{account_id}/client-ledgers")
def list_client_ledgers(account_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return trust_accounting.list_client_ledgers(account_id)

@app.get("/api/trust-accounting/accounts/{account_id}/client-ledgers/{client_id}")
def get_client_ledger(account_id: str, client_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    l = trust_accounting.get_client_ledger(account_id, client_id)
    if l is None:
        raise HTTPException(status_code=404, detail="Client ledger not found")
    return l

@app.post("/api/trust-accounting/accounts/{account_id}/client-ledgers/{client_id}/close")
def close_client_ledger(account_id: str, client_id: str, reason: str = "", user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.close_client_ledger(account_id, client_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.post("/api/trust-accounting/accounts/{account_id}/transactions", status_code=201)
def post_trust_transaction(account_id: str, req: TrustTransactionRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.post_transaction(
            account_id=account_id, client_id=req.client_id, kind=req.kind,
            amount=req.amount, description=req.description,
            external_reference=req.external_reference,
            approved_by=req.approved_by or user.id, reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@app.get("/api/trust-accounting/accounts/{account_id}/transactions")
def list_trust_transactions(account_id: str, client_id: str | None = None, kind: str | None = None, since: str | None = None, until: str | None = None, limit: int = 200, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return trust_accounting.list_transactions(account_id=account_id, client_id=client_id, kind=kind, since=since, until=until, limit=limit)

@app.post("/api/trust-accounting/accounts/{account_id}/bank-balance")
def post_bank_balance(account_id: str, req: BankBalanceRequest, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.post_bank_balance(account_id, req.balance, as_of=req.as_of)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.post("/api/trust-accounting/accounts/{account_id}/reconcile")
def reconcile_trust_account(account_id: str, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.reconcile(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@app.get("/api/trust-accounting/accounts/{account_id}/reconciliations")
def list_reconciliations(account_id: str, limit: int = 50, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    return trust_accounting.list_reconciliations(account_id=account_id, limit=limit)

@app.get("/api/trust-accounting/accounts/{account_id}/client-ledgers/{client_id}/statement")
def get_client_statement(account_id: str, client_id: str, since: str | None = None, user: UserOut = Depends(require_role(UserRole.ATTORNEY))):
    try:
        return trust_accounting.get_client_statement(account_id, client_id, since=since)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
