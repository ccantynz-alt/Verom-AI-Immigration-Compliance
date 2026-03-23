"""E-Verify integration service — case creation, status, TNC resolution, bulk processing."""

from __future__ import annotations

import uuid
from datetime import date, datetime


class EVerifyService:
    """E-Verify integration for employment eligibility verification."""

    def __init__(self) -> None:
        self._cases: dict[str, dict] = {}
        self._stats: dict[str, dict] = {}

    def create_case(self, employee_data: dict) -> dict:
        case_id = str(uuid.uuid4())
        case = {
            "id": case_id,
            "employee_name": employee_data.get("name", ""),
            "ssn_last4": employee_data.get("ssn_last4", ""),
            "hire_date": employee_data.get("hire_date", date.today().isoformat()),
            "status": "initial_verification",
            "result": None,
            "created_at": datetime.utcnow().isoformat(),
            "case_number": f"EV-{uuid.uuid4().hex[:8].upper()}",
        }
        self._cases[case_id] = case
        # Simulate verification
        case["status"] = "employment_authorized"
        case["result"] = "Employment Authorized"
        return case

    def check_status(self, case_id: str) -> dict | None:
        return self._cases.get(case_id)

    def resolve_tnc(self, case_id: str, resolution: str) -> dict:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError("Case not found")
        case["tnc_resolution"] = resolution
        case["status"] = "resolved"
        case["result"] = "Employment Authorized" if resolution == "confirmed" else "Final Nonconfirmation"
        return case

    def close_case(self, case_id: str, result: str) -> dict:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError("Case not found")
        case["status"] = "closed"
        case["result"] = result
        case["closed_at"] = datetime.utcnow().isoformat()
        return case

    def bulk_verify(self, employee_list: list[dict]) -> list[dict]:
        return [self.create_case(emp) for emp in employee_list]

    def get_stats(self, employer_id: str) -> dict:
        total = len(self._cases)
        authorized = sum(1 for c in self._cases.values() if c.get("result") == "Employment Authorized")
        return {
            "employer_id": employer_id,
            "total_cases": total,
            "authorized": authorized,
            "tnc_issued": 0,
            "final_nonconfirmation": 0,
            "pending": total - authorized,
            "compliance_rate": (authorized / total * 100) if total > 0 else 100,
        }

    def generate_i9_section2(self, employee_data: dict) -> dict:
        return {
            "employee_name": employee_data.get("name", ""),
            "section2": {
                "document_title": employee_data.get("document_title", "US Passport"),
                "issuing_authority": employee_data.get("issuing_authority", "US Department of State"),
                "document_number": employee_data.get("document_number", ""),
                "expiration_date": employee_data.get("document_expiry", ""),
                "employer_name": employee_data.get("employer_name", ""),
                "verification_date": date.today().isoformat(),
            },
            "status": "completed",
            "remote_verification": True,
        }

    def bulk_process_i9(self, employee_list: list[dict]) -> list[dict]:
        return [self.generate_i9_section2(emp) for emp in employee_list]
