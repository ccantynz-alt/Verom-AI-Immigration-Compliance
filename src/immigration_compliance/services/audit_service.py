"""Audit trail service and ICE audit simulation engine."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from immigration_compliance.models.audit import (
    AuditAction,
    AuditEntry,
    AuditFinding,
    AuditSeverity,
    ICEAuditFinding,
    ICEAuditReport,
)
from immigration_compliance.models.employee import Employee, VisaType


class AuditTrailService:
    """Records and retrieves audit trail entries."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(
        self,
        action: AuditAction,
        actor: str = "system",
        employee_id: str | None = None,
        case_id: str | None = None,
        document_id: str | None = None,
        details: str = "",
        metadata: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            action=action,
            actor=actor,
            employee_id=employee_id,
            case_id=case_id,
            document_id=document_id,
            details=details,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        employee_id: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = self._entries
        if employee_id:
            results = [e for e in results if e.employee_id == employee_id]
        if action:
            results = [e for e in results if e.action == action]
        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    @property
    def total_entries(self) -> int:
        return len(self._entries)


# Fine schedule based on 2024 OCAHO penalty ranges
_I9_FINE_RANGES = {
    AuditSeverity.CRITICAL: (2507.0, 2507.0),
    AuditSeverity.MAJOR: (1264.0, 2507.0),
    AuditSeverity.MINOR: (281.0, 1264.0),
    AuditSeverity.OBSERVATION: (0.0, 0.0),
}


class ICEAuditSimulator:
    """Simulates an ICE I-9 audit (Notice of Inspection) against employee records."""

    def run_audit(
        self,
        employees: list[Employee],
        documents: dict[str, list] | None = None,
        paf_data: dict[str, dict] | None = None,
        as_of: date | None = None,
    ) -> ICEAuditReport:
        ref = as_of or date.today()
        findings: list[ICEAuditFinding] = []
        docs = documents or {}
        pafs = paf_data or {}

        for emp in employees:
            findings.extend(self._audit_employee(emp, docs.get(emp.id, []), pafs.get(emp.id, {}), ref))

        critical = sum(1 for f in findings if f.severity == AuditSeverity.CRITICAL)
        major = sum(1 for f in findings if f.severity == AuditSeverity.MAJOR)
        minor = sum(1 for f in findings if f.severity == AuditSeverity.MINOR)
        observation = sum(1 for f in findings if f.severity == AuditSeverity.OBSERVATION)
        total_fines = sum(f.potential_fine for f in findings)

        grade = self._calculate_grade(len(employees), critical, major, minor)

        recommendations = self._generate_recommendations(findings)

        summary_parts = []
        if critical:
            summary_parts.append(f"{critical} critical finding(s) requiring immediate action")
        if major:
            summary_parts.append(f"{major} major finding(s)")
        if minor:
            summary_parts.append(f"{minor} minor finding(s)")
        if not findings:
            summary_parts.append("No findings - organization is audit-ready")

        return ICEAuditReport(
            id=str(uuid.uuid4()),
            total_employees_audited=len(employees),
            findings=findings,
            total_potential_fines=total_fines,
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            observation_count=observation,
            overall_grade=grade,
            summary=". ".join(summary_parts) + ".",
            recommendations=recommendations,
        )

    def _audit_employee(
        self, emp: Employee, emp_docs: list, paf: dict, ref: date
    ) -> list[ICEAuditFinding]:
        findings: list[ICEAuditFinding] = []

        # I-9 Checks
        if not emp.i9_completed:
            hire_days = (ref - emp.hire_date).days if emp.hire_date else 999
            severity = AuditSeverity.CRITICAL if hire_days > 3 else AuditSeverity.MAJOR
            fine_min, fine_max = _I9_FINE_RANGES[severity]
            findings.append(ICEAuditFinding(
                id=str(uuid.uuid4()),
                finding_type=AuditFinding.MISSING_I9,
                severity=severity,
                employee_id=emp.id,
                description=f"Form I-9 not completed for {emp.first_name} {emp.last_name}",
                regulation_reference="8 USC 1324a(b); 8 CFR 274a.2",
                potential_fine=(fine_min + fine_max) / 2,
                remediation_steps="Complete Form I-9 immediately. Retain documentation of late completion.",
                remediation_deadline="Immediately",
            ))

        # I-9 expiration / reverification
        if emp.i9_completed and emp.i9_expiration_date:
            days = (emp.i9_expiration_date - ref).days
            if days < 0:
                findings.append(ICEAuditFinding(
                    id=str(uuid.uuid4()),
                    finding_type=AuditFinding.EXPIRED_I9,
                    severity=AuditSeverity.CRITICAL,
                    employee_id=emp.id,
                    description=f"I-9 reverification overdue by {abs(days)} days",
                    regulation_reference="8 CFR 274a.2(b)(1)(vii)",
                    potential_fine=2507.0,
                    remediation_steps="Complete Section 3 reverification. Document the delay and corrective action.",
                    remediation_deadline="Immediately",
                ))

        # Work authorization
        if emp.visa_type not in (VisaType.CITIZEN, VisaType.GREEN_CARD):
            if emp.visa_expiration_date and (emp.visa_expiration_date - ref).days < 0:
                findings.append(ICEAuditFinding(
                    id=str(uuid.uuid4()),
                    finding_type=AuditFinding.UNAUTHORIZED_WORKER,
                    severity=AuditSeverity.CRITICAL,
                    employee_id=emp.id,
                    description=f"Work authorization expired on {emp.visa_expiration_date}",
                    regulation_reference="8 USC 1324a(a)(2); INA 274A",
                    potential_fine=2507.0,
                    remediation_steps="Immediately cease employment or verify valid extension/cap-gap protection.",
                    remediation_deadline="Immediately",
                ))

        # Wage compliance for LCA visa types
        if emp.visa_type in (VisaType.H1B, VisaType.H1B1, VisaType.E3):
            if emp.actual_wage is not None and emp.prevailing_wage is not None:
                if emp.actual_wage < emp.prevailing_wage:
                    findings.append(ICEAuditFinding(
                        id=str(uuid.uuid4()),
                        finding_type=AuditFinding.WAGE_VIOLATION,
                        severity=AuditSeverity.CRITICAL,
                        employee_id=emp.id,
                        description=(
                            f"Actual wage ${emp.actual_wage:,.0f} below prevailing wage "
                            f"${emp.prevailing_wage:,.0f}"
                        ),
                        regulation_reference="20 CFR 655.731; INA 212(n)",
                        potential_fine=min(
                            (emp.prevailing_wage - emp.actual_wage),
                            50000.0,
                        ),
                        remediation_steps="Adjust wage to at least prevailing wage. Calculate and pay back wages owed.",
                        remediation_deadline="Within 30 days",
                    ))

            # PAF check
            if not paf.get("complete", False):
                findings.append(ICEAuditFinding(
                    id=str(uuid.uuid4()),
                    finding_type=AuditFinding.PAF_INCOMPLETE,
                    severity=AuditSeverity.MAJOR,
                    employee_id=emp.id,
                    description="Public Access File is incomplete or missing required documents",
                    regulation_reference="20 CFR 655.760",
                    potential_fine=1886.0,
                    remediation_steps="Compile all required PAF documents: certified LCA, prevailing wage determination, actual wage memo, wage system explanation, and posting notice.",
                    remediation_deadline="Within 1 business day of request",
                ))

        return findings

    def _calculate_grade(self, total: int, critical: int, major: int, minor: int) -> str:
        if total == 0:
            return "N/A"
        error_rate = (critical * 3 + major * 2 + minor) / max(total, 1)
        if critical > 0:
            return "F" if error_rate > 2 else "D"
        if major > 0:
            return "C" if error_rate > 1 else "B-"
        if minor > 0:
            return "B+" if error_rate > 0.5 else "A-"
        return "A"

    def _generate_recommendations(self, findings: list[ICEAuditFinding]) -> list[str]:
        recs: list[str] = []
        types = {f.finding_type for f in findings}

        if AuditFinding.MISSING_I9 in types:
            recs.append("Implement mandatory I-9 completion workflow within 3 business days of hire")
        if AuditFinding.EXPIRED_I9 in types:
            recs.append("Set up automated I-9 reverification reminders 90 days before expiration")
        if AuditFinding.UNAUTHORIZED_WORKER in types:
            recs.append("Establish visa expiration tracking with escalation procedures")
        if AuditFinding.WAGE_VIOLATION in types:
            recs.append("Conduct annual wage audit to ensure compliance with LCA requirements")
        if AuditFinding.PAF_INCOMPLETE in types:
            recs.append("Create PAF checklist and assign ownership for maintaining files")
        if AuditFinding.MISSING_DOCUMENT in types:
            recs.append("Implement document management system with expiration tracking")

        if not recs:
            recs.append("Continue current compliance practices and schedule regular self-audits")

        return recs
