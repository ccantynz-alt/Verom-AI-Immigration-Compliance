"""FastAPI application for immigration compliance API."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from immigration_compliance.models.case import Case, CaseStatus
from immigration_compliance.models.compliance import ComplianceReport, RuleViolation
from immigration_compliance.models.employee import Employee
from immigration_compliance.services.compliance_service import ComplianceService

# Resolve frontend directory
_root = Path(__file__).resolve().parent.parent.parent.parent
_frontend_dir = _root / "frontend"

app = FastAPI(
    title="AI Immigration Compliance",
    description="AI-powered immigration compliance monitoring and risk assessment",
    version="0.1.0",
)

# Serve static assets (CSS, JS)
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

# In-memory service instance (swap for DI in production)
service = ComplianceService()

# In-memory case store
_cases: dict[str, Case] = {}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ComplianceCheckRequest(BaseModel):
    as_of: date | None = None


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


# --- Root / Frontend ---


@app.get("/", response_class=HTMLResponse)
def serve_frontend() -> HTMLResponse:
    index_path = _frontend_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>ImmigrationAI</h1><p>Frontend not found.</p>")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


# --- Employee endpoints (under /api prefix for frontend) ---


@app.post("/api/employees", response_model=Employee, status_code=201)
def create_employee(employee: Employee) -> Employee:
    if service.get_employee(employee.id):
        raise HTTPException(status_code=409, detail=f"Employee {employee.id} already exists")
    return service.add_employee(employee)


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


# --- Compliance endpoints ---


@app.post("/api/compliance/check/{employee_id}", response_model=list[RuleViolation])
def check_employee_compliance(
    employee_id: str, request: ComplianceCheckRequest | None = None
) -> list[RuleViolation]:
    as_of = request.as_of if request else None
    try:
        return service.check_employee(employee_id, as_of)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/compliance/report", response_model=ComplianceReport)
def generate_compliance_report(
    request: ComplianceCheckRequest | None = None,
) -> ComplianceReport:
    as_of = request.as_of if request else None
    return service.generate_report(as_of)


# --- Case endpoints ---


@app.post("/api/cases", response_model=Case, status_code=201)
def create_case(case: Case) -> Case:
    if case.id in _cases:
        raise HTTPException(status_code=409, detail=f"Case {case.id} already exists")
    _cases[case.id] = case
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
    updated = case.model_copy(update={"status": update.status})
    _cases[case_id] = updated
    return updated


@app.delete("/api/cases/{case_id}", status_code=204)
def delete_case(case_id: str) -> None:
    if _cases.pop(case_id, None) is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
