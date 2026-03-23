"""FastAPI application for immigration compliance API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from immigration_compliance.models.audit import AuditAction, AuditEntry, ICEAuditReport
from immigration_compliance.models.case import Case, CaseStatus
from immigration_compliance.models.compliance import ComplianceReport, RuleViolation
from immigration_compliance.models.document import Document, DocumentCategory
from immigration_compliance.models.employee import Employee
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
service = ComplianceService()
_cases: dict[str, Case] = {}
doc_service = DocumentService()
audit_trail = AuditTrailService()
ice_simulator = ICEAuditSimulator()
paf_service = PAFService()
regulatory_service = RegulatoryService()
global_service = GlobalImmigrationService()
hris_service = HRISService()


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

@app.get("/", response_class=HTMLResponse)
def serve_landing() -> HTMLResponse:
    landing_path = _frontend_dir / "landing.html"
    if landing_path.exists():
        return HTMLResponse(content=landing_path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Landing page not found.</p>")

@app.get("/app", response_class=HTMLResponse)
def serve_app() -> HTMLResponse:
    index_path = _frontend_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>App not found.</p>")

@app.get("/login", response_class=HTMLResponse)
def serve_login() -> HTMLResponse:
    path = _frontend_dir / "login.html"
    if path.exists():
        return HTMLResponse(content=path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Login page not found.</p>")

@app.get("/applicant", response_class=HTMLResponse)
def serve_applicant() -> HTMLResponse:
    path = _frontend_dir / "applicant.html"
    if path.exists():
        return HTMLResponse(content=path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Applicant portal not found.</p>")

@app.get("/attorney", response_class=HTMLResponse)
def serve_attorney() -> HTMLResponse:
    path = _frontend_dir / "attorney.html"
    if path.exists():
        return HTMLResponse(content=path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Attorney portal not found.</p>")

@app.get("/privacy", response_class=HTMLResponse)
def serve_privacy() -> HTMLResponse:
    path = _frontend_dir / "privacy.html"
    if path.exists():
        return HTMLResponse(content=path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Privacy policy not found.</p>")

@app.get("/terms", response_class=HTMLResponse)
def serve_terms() -> HTMLResponse:
    path = _frontend_dir / "terms.html"
    if path.exists():
        return HTMLResponse(content=path.read_text())
    return HTMLResponse(content="<h1>Verom.ai</h1><p>Terms of service not found.</p>")

@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


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
# Auth endpoints (demo)
# =============================================

import uuid
from datetime import datetime
from typing import Optional

_users: dict[str, dict] = {}
_sessions: dict[str, dict] = {}


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = "applicant"


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = "applicant"
    bar_number: str = ""
    jurisdiction: str = ""
    specializations: str = ""


@app.post("/api/auth/login")
def auth_login(req: LoginRequest) -> dict:
    """Demo login: accept any credentials, create session."""
    session_id = str(uuid.uuid4())
    user = _users.get(req.email, {
        "email": req.email,
        "role": req.role,
        "first_name": "Demo",
        "last_name": "User",
    })
    _sessions[session_id] = user
    return {"session_id": session_id, "user": user}


@app.post("/api/auth/register")
def auth_register(req: RegisterRequest) -> dict:
    """Demo registration: store user, create session."""
    user = {
        "email": req.email,
        "role": req.role,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "bar_number": req.bar_number,
        "jurisdiction": req.jurisdiction,
        "specializations": req.specializations,
    }
    _users[req.email] = user
    session_id = str(uuid.uuid4())
    _sessions[session_id] = user
    return {"session_id": session_id, "user": user}


# =============================================
# Attorney endpoints
# =============================================

_attorney_profile: dict = {
    "id": "att-001",
    "first_name": "Sarah",
    "last_name": "Kim",
    "email": "sarah.kim@verom.ai",
    "bar_number": "NY-2015-28394",
    "jurisdiction": "New York, NY",
    "years_experience": 12,
    "specializations": ["H-1B", "O-1", "EB-2", "F-1", "Family"],
    "bio": "Immigration attorney specializing in employment-based and student visas with 12 years of experience.",
    "capacity": 5,
    "rating": 4.9,
    "total_cases": 342,
    "success_rate": 96,
}

_attorney_cases: dict[str, dict] = {}
_attorney_browse: dict[str, dict] = {}
_attorney_calendar: dict[str, dict] = {}
_attorney_earnings: dict = {}


def _init_attorney_demo_data() -> None:
    """Populate demo data for attorney endpoints."""
    global _attorney_earnings

    cases = [
        {"id": "ac-001", "client_name": "Maria Garcia", "visa_type": "F-1", "status": "new", "country": "US", "submitted": "2026-03-20", "priority": "medium", "notes": "Undergraduate student visa application for Fall 2026."},
        {"id": "ac-002", "client_name": "Ahmed Hassan", "visa_type": "Skilled Worker", "status": "new", "country": "UK", "submitted": "2026-03-19", "priority": "high", "notes": "Software engineer role at London fintech company."},
        {"id": "ac-003", "client_name": "Raj Mehta", "visa_type": "H-1B", "status": "in_progress", "country": "US", "submitted": "2026-03-10", "priority": "high", "notes": "H-1B petition for senior data scientist position."},
        {"id": "ac-004", "client_name": "Li Wei", "visa_type": "F-1", "status": "in_progress", "country": "US", "submitted": "2026-03-08", "priority": "medium", "notes": "Graduate student visa for MS Computer Science."},
        {"id": "ac-005", "client_name": "John Lee", "visa_type": "H-1B Transfer", "status": "in_progress", "country": "US", "submitted": "2026-03-05", "priority": "high", "notes": "Employer transfer from consulting firm to tech company."},
        {"id": "ac-006", "client_name": "Priya Patel", "visa_type": "EAD Renewal", "status": "in_progress", "country": "US", "submitted": "2026-03-01", "priority": "urgent", "notes": "EAD expiring in 45 days, expedited processing requested."},
        {"id": "ac-007", "client_name": "Ana Santos", "visa_type": "O-1", "status": "rfe", "country": "US", "submitted": "2026-02-15", "priority": "urgent", "notes": "RFE received for extraordinary ability evidence. Response due April 1."},
        {"id": "ac-008", "client_name": "Yuki Tanaka", "visa_type": "O-1", "status": "approved", "country": "US", "submitted": "2026-01-20", "priority": "low", "notes": "O-1 approved for acclaimed researcher."},
        {"id": "ac-009", "client_name": "Wei Chen", "visa_type": "EB-2", "status": "approved", "country": "US", "submitted": "2026-01-05", "priority": "low", "notes": "EB-2 NIW approved for AI researcher."},
    ]
    for c in cases:
        _attorney_cases[c["id"]] = c

    browse_cases = [
        {"id": "br-001", "applicant_name": "Carlos Rivera", "visa_type": "H-1B", "country": "US", "ai_score": 92, "summary": "Software engineer with 6 years experience, MS from Stanford. Strong H-1B candidate.", "submitted": "2026-03-21", "specialization_match": True},
        {"id": "br-002", "applicant_name": "Fatima Al-Rashid", "visa_type": "O-1", "country": "US", "ai_score": 88, "summary": "Award-winning journalist seeking O-1 visa. Multiple international awards.", "submitted": "2026-03-20", "specialization_match": True},
        {"id": "br-003", "applicant_name": "Kenji Yamamoto", "visa_type": "EB-2", "country": "US", "ai_score": 95, "summary": "PhD in biomedical engineering with 15 publications. Exceptional EB-2 NIW candidate.", "submitted": "2026-03-19", "specialization_match": True},
        {"id": "br-004", "applicant_name": "Elena Petrov", "visa_type": "F-1", "country": "US", "ai_score": 85, "summary": "Graduate student admitted to Columbia University MBA program.", "submitted": "2026-03-18", "specialization_match": True},
    ]
    for b in browse_cases:
        _attorney_browse[b["id"]] = b

    calendar_events = [
        {"id": "ev-001", "title": "Ana Santos — RFE Response Deadline", "date": "2026-04-01", "type": "deadline", "case_id": "ac-007", "priority": "urgent"},
        {"id": "ev-002", "title": "Priya Patel — EAD Filing Deadline", "date": "2026-04-10", "type": "deadline", "case_id": "ac-006", "priority": "high"},
        {"id": "ev-003", "title": "Raj Mehta — H-1B Lottery Results", "date": "2026-03-31", "type": "milestone", "case_id": "ac-003", "priority": "high"},
        {"id": "ev-004", "title": "Li Wei — SEVIS Fee Payment Due", "date": "2026-04-05", "type": "deadline", "case_id": "ac-004", "priority": "medium"},
        {"id": "ev-005", "title": "John Lee — Employer Support Letter Due", "date": "2026-04-08", "type": "deadline", "case_id": "ac-005", "priority": "medium"},
        {"id": "ev-006", "title": "Maria Garcia — Initial Consultation", "date": "2026-03-25", "type": "consultation", "case_id": "ac-001", "priority": "medium"},
    ]
    for ev in calendar_events:
        _attorney_calendar[ev["id"]] = ev

    _attorney_earnings = {
        "this_month": 14250.00,
        "last_month": 18500.00,
        "ytd": 47800.00,
        "pending": 6500.00,
        "payments": [
            {"id": "pay-001", "client": "Yuki Tanaka", "amount": 5500.00, "date": "2026-03-15", "status": "paid", "description": "O-1 visa — final payment"},
            {"id": "pay-002", "client": "Wei Chen", "amount": 4750.00, "date": "2026-03-10", "status": "paid", "description": "EB-2 NIW — approval milestone"},
            {"id": "pay-003", "client": "Raj Mehta", "amount": 2000.00, "date": "2026-03-05", "status": "paid", "description": "H-1B — retainer deposit"},
            {"id": "pay-004", "client": "John Lee", "amount": 2000.00, "date": "2026-03-02", "status": "paid", "description": "H-1B Transfer — retainer deposit"},
            {"id": "pay-005", "client": "Ana Santos", "amount": 3500.00, "date": "2026-02-28", "status": "paid", "description": "O-1 — RFE response work"},
            {"id": "pay-006", "client": "Priya Patel", "amount": 1500.00, "date": "2026-03-20", "status": "pending", "description": "EAD Renewal — filing fee advance"},
            {"id": "pay-007", "client": "Maria Garcia", "amount": 2500.00, "date": "2026-03-22", "status": "pending", "description": "F-1 — initial consultation + retainer"},
            {"id": "pay-008", "client": "Ahmed Hassan", "amount": 2500.00, "date": "2026-03-22", "status": "pending", "description": "Skilled Worker — initial consultation + retainer"},
        ],
    }


_init_attorney_demo_data()


class AttorneyProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    jurisdiction: Optional[str] = None
    years_experience: Optional[int] = None
    specializations: Optional[list[str]] = None
    bio: Optional[str] = None
    capacity: Optional[int] = None


class AttorneyCaseCreate(BaseModel):
    client_name: str
    visa_type: str
    country: str = "US"
    priority: str = "medium"
    notes: str = ""


class AttorneyCaseUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class CalendarEventCreate(BaseModel):
    title: str
    date: str
    type: str = "deadline"
    case_id: str = ""
    priority: str = "medium"


@app.get("/api/attorney/profile")
def get_attorney_profile() -> dict:
    return _attorney_profile


@app.put("/api/attorney/profile")
def update_attorney_profile(update: AttorneyProfileUpdate) -> dict:
    for field, value in update.model_dump(exclude_none=True).items():
        _attorney_profile[field] = value
    return _attorney_profile


@app.get("/api/attorney/cases")
def get_attorney_cases() -> list[dict]:
    return list(_attorney_cases.values())


@app.post("/api/attorney/cases", status_code=201)
def create_attorney_case(req: AttorneyCaseCreate) -> dict:
    case_id = f"ac-{str(uuid.uuid4())[:8]}"
    case = {
        "id": case_id,
        "client_name": req.client_name,
        "visa_type": req.visa_type,
        "status": "new",
        "country": req.country,
        "submitted": datetime.utcnow().strftime("%Y-%m-%d"),
        "priority": req.priority,
        "notes": req.notes,
    }
    _attorney_cases[case_id] = case
    return case


@app.patch("/api/attorney/cases/{case_id}")
def update_attorney_case(case_id: str, update: AttorneyCaseUpdate) -> dict:
    case = _attorney_cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Attorney case {case_id} not found")
    for field, value in update.model_dump(exclude_none=True).items():
        case[field] = value
    return case


@app.get("/api/attorney/browse")
def browse_available_cases() -> list[dict]:
    return list(_attorney_browse.values())


@app.post("/api/attorney/browse/{case_id}/accept", status_code=200)
def accept_browse_case(case_id: str) -> dict:
    browse_case = _attorney_browse.pop(case_id, None)
    if browse_case is None:
        raise HTTPException(status_code=404, detail=f"Browse case {case_id} not found")
    new_id = f"ac-{str(uuid.uuid4())[:8]}"
    new_case = {
        "id": new_id,
        "client_name": browse_case["applicant_name"],
        "visa_type": browse_case["visa_type"],
        "status": "new",
        "country": browse_case["country"],
        "submitted": datetime.utcnow().strftime("%Y-%m-%d"),
        "priority": "medium",
        "notes": browse_case.get("summary", ""),
    }
    _attorney_cases[new_id] = new_case
    return new_case


@app.get("/api/attorney/calendar")
def get_attorney_calendar() -> list[dict]:
    return list(_attorney_calendar.values())


@app.post("/api/attorney/calendar", status_code=201)
def create_calendar_event(req: CalendarEventCreate) -> dict:
    event_id = f"ev-{str(uuid.uuid4())[:8]}"
    event = {
        "id": event_id,
        "title": req.title,
        "date": req.date,
        "type": req.type,
        "case_id": req.case_id,
        "priority": req.priority,
    }
    _attorney_calendar[event_id] = event
    return event


@app.delete("/api/attorney/calendar/{event_id}", status_code=204)
def delete_calendar_event(event_id: str) -> None:
    if _attorney_calendar.pop(event_id, None) is None:
        raise HTTPException(status_code=404, detail=f"Calendar event {event_id} not found")


@app.get("/api/attorney/earnings")
def get_attorney_earnings() -> dict:
    return _attorney_earnings


# =============================================
# Applicant endpoints
# =============================================

_applicant_applications: dict[str, dict] = {}
_applicant_consultations: dict[str, dict] = {}
_applicant_documents: dict[str, list[dict]] = {}
_applicant_messages: list[dict] = []

_demo_attorneys: list[dict] = [
    {
        "id": "att-001",
        "first_name": "Sarah",
        "last_name": "Kim",
        "country": "US",
        "specializations": ["Student Visas", "Work Visas"],
        "match_score": 96,
        "years_experience": 12,
        "rating": 4.9,
        "total_reviews": 215,
        "bio": "Immigration attorney specializing in employment-based and student visas with 12 years of experience in New York.",
        "availability": "Available",
    },
    {
        "id": "att-002",
        "first_name": "James",
        "last_name": "Patel",
        "country": "UK",
        "specializations": ["Skilled Worker", "ILR"],
        "match_score": 94,
        "years_experience": 8,
        "rating": 4.8,
        "total_reviews": 163,
        "bio": "UK immigration solicitor with deep expertise in Skilled Worker visas and settlement applications.",
        "availability": "Available",
    },
    {
        "id": "att-003",
        "first_name": "Maria",
        "last_name": "Lopez",
        "country": "Canada",
        "specializations": ["Express Entry", "Study Permits"],
        "match_score": 97,
        "years_experience": 15,
        "rating": 4.9,
        "total_reviews": 298,
        "bio": "Canadian immigration lawyer with 15 years of experience in Express Entry and study permit applications.",
        "availability": "Available",
    },
    {
        "id": "att-004",
        "first_name": "Daniel",
        "last_name": "Weber",
        "country": "Germany",
        "specializations": ["EU Blue Card", "Student Visa"],
        "match_score": 92,
        "years_experience": 10,
        "rating": 4.7,
        "total_reviews": 134,
        "bio": "German immigration specialist focusing on EU Blue Card applications and student residence permits.",
        "availability": "Available",
    },
]


class ApplicationCreate(BaseModel):
    visa_type: str
    destination_country: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    nationality: str = ""
    education_level: str = ""
    years_experience: int = 0
    english_proficiency: str = ""
    notes: str = ""


class ConsultationRequest(BaseModel):
    attorney_id: str
    application_id: str = ""
    preferred_date: str = ""
    preferred_time: str = ""
    notes: str = ""


class DocumentUpload(BaseModel):
    application_id: str
    document_type: str
    file_name: str
    file_size: int = 0
    notes: str = ""


class MessageCreate(BaseModel):
    recipient_id: str
    application_id: str = ""
    subject: str = ""
    body: str


@app.post("/api/applicant/applications", status_code=201)
def create_application(req: ApplicationCreate) -> dict:
    app_id = f"app-{str(uuid.uuid4())[:8]}"
    application = {
        "id": app_id,
        "visa_type": req.visa_type,
        "destination_country": req.destination_country,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "email": req.email,
        "phone": req.phone,
        "nationality": req.nationality,
        "education_level": req.education_level,
        "years_experience": req.years_experience,
        "english_proficiency": req.english_proficiency,
        "notes": req.notes,
        "status": "submitted",
        "ai_score": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _applicant_applications[app_id] = application
    return application


@app.get("/api/applicant/applications")
def list_applications() -> list[dict]:
    return list(_applicant_applications.values())


@app.get("/api/applicant/applications/{app_id}")
def get_application(app_id: str) -> dict:
    application = _applicant_applications.get(app_id)
    if application is None:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found")
    return application


@app.get("/api/applicant/attorneys")
def browse_attorneys(country: Optional[str] = None, specialization: Optional[str] = None) -> list[dict]:
    results = _demo_attorneys
    if country:
        results = [a for a in results if a["country"].lower() == country.lower()]
    if specialization:
        results = [a for a in results if any(specialization.lower() in s.lower() for s in a["specializations"])]
    return results


@app.post("/api/applicant/consultations", status_code=201)
def request_consultation(req: ConsultationRequest) -> dict:
    consult_id = f"con-{str(uuid.uuid4())[:8]}"
    consultation = {
        "id": consult_id,
        "attorney_id": req.attorney_id,
        "application_id": req.application_id,
        "preferred_date": req.preferred_date,
        "preferred_time": req.preferred_time,
        "notes": req.notes,
        "status": "requested",
        "created_at": datetime.utcnow().isoformat(),
    }
    _applicant_consultations[consult_id] = consultation
    return consultation


@app.get("/api/applicant/consultations")
def list_consultations() -> list[dict]:
    return list(_applicant_consultations.values())


@app.post("/api/applicant/documents/upload", status_code=201)
def upload_document(req: DocumentUpload) -> dict:
    doc_id = f"doc-{str(uuid.uuid4())[:8]}"
    doc = {
        "id": doc_id,
        "application_id": req.application_id,
        "document_type": req.document_type,
        "file_name": req.file_name,
        "file_size": req.file_size,
        "notes": req.notes,
        "status": "uploaded",
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    if req.application_id not in _applicant_documents:
        _applicant_documents[req.application_id] = []
    _applicant_documents[req.application_id].append(doc)
    return doc


@app.get("/api/applicant/documents/{app_id}")
def get_application_documents(app_id: str) -> list[dict]:
    return _applicant_documents.get(app_id, [])


@app.get("/api/applicant/messages")
def get_messages() -> list[dict]:
    return _applicant_messages


@app.post("/api/applicant/messages", status_code=201)
def send_message(req: MessageCreate) -> dict:
    msg_id = f"msg-{str(uuid.uuid4())[:8]}"
    message = {
        "id": msg_id,
        "recipient_id": req.recipient_id,
        "application_id": req.application_id,
        "subject": req.subject,
        "body": req.body,
        "direction": "outbound",
        "read": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    _applicant_messages.append(message)
    return message
