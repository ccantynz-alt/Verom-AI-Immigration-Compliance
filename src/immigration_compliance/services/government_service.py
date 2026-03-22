"""Government Portal Unification — single dashboard for USCIS, DOL, EOIR, SEVIS, UK, Canada, Australia."""

from __future__ import annotations

from datetime import date, timedelta


class GovernmentPortalService:
    """Unified government case status and processing intelligence."""

    def check_uscis_status(self, receipt_number: str) -> dict:
        statuses = {
            "WAC": {"status": "Case Was Received", "form": "I-129", "last_updated": "2026-03-18"},
            "LIN": {"status": "Request for Evidence Was Sent", "form": "I-485", "last_updated": "2026-03-15"},
            "EAC": {"status": "Case Is Being Actively Reviewed", "form": "I-140", "last_updated": "2026-03-20"},
            "SRC": {"status": "Case Was Approved", "form": "I-765", "last_updated": "2026-03-10"},
        }
        prefix = receipt_number[:3] if len(receipt_number) >= 3 else "WAC"
        data = statuses.get(prefix, statuses["WAC"])
        return {
            "receipt_number": receipt_number,
            "form_type": data["form"],
            "status": data["status"],
            "last_updated": data["last_updated"],
            "service_center": prefix,
            "next_action": "Wait for processing" if "Approved" not in data["status"] else "None — case complete",
        }

    def get_processing_times(self, form_type: str = "I-129", service_center: str | None = None) -> dict:
        times = {
            "I-129": {"regular": "6-8 months", "premium": "15 business days", "center": "California/Vermont"},
            "I-140": {"regular": "8-14 months", "premium": "15 business days", "center": "Nebraska/Texas"},
            "I-485": {"regular": "12-24 months", "premium": "N/A", "center": "National Benefits Center"},
            "I-765": {"regular": "3-7 months", "premium": "N/A", "center": "Various"},
            "I-131": {"regular": "4-8 months", "premium": "N/A", "center": "Various"},
            "I-130": {"regular": "12-24 months", "premium": "N/A", "center": "Various"},
            "N-400": {"regular": "8-14 months", "premium": "N/A", "center": "Field Office"},
        }
        data = times.get(form_type, {"regular": "6-12 months", "premium": "N/A", "center": "Various"})
        return {"form_type": form_type, "as_of": date.today().isoformat(), **data}

    def get_visa_bulletin(self, category: str | None = None, country: str | None = None) -> dict:
        return {
            "month": "April 2026",
            "employment_based": {
                "EB-1": {"all_chargeability": "Current", "china": "01JAN23", "india": "01JAN22"},
                "EB-2": {"all_chargeability": "Current", "china": "01MAR20", "india": "01JUN13"},
                "EB-3": {"all_chargeability": "Current", "china": "01JAN20", "india": "01JAN12"},
                "EB-5": {"all_chargeability": "Current", "china": "01SEP18", "india": "Current"},
            },
            "family_based": {
                "F-1": {"all_chargeability": "01DEC15", "mexico": "01MAR01", "philippines": "01APR12"},
                "F-2A": {"all_chargeability": "Current"},
                "F-2B": {"all_chargeability": "01SEP16", "mexico": "01JAN03"},
                "F-3": {"all_chargeability": "01NOV09"},
                "F-4": {"all_chargeability": "01MAR07"},
            },
        }

    def check_sevis_status(self, sevis_id: str) -> dict:
        return {
            "sevis_id": sevis_id,
            "status": "Active",
            "program_type": "F-1",
            "school": "Massachusetts Institute of Technology",
            "program_start": "2024-08-20",
            "program_end": "2026-05-15",
            "opt_status": "Not Applied",
        }

    def check_dol_status(self, case_number: str) -> dict:
        return {
            "case_number": case_number,
            "case_type": "PERM",
            "status": "In Review",
            "priority_date": "2025-11-15",
            "employer": "Tech Corp Inc.",
            "last_updated": "2026-03-10",
            "estimated_completion": "6-12 months from filing",
        }

    def check_eoir_status(self, alien_number: str) -> dict:
        return {
            "alien_number": alien_number,
            "court": "New York Immigration Court",
            "status": "Pending Hearing",
            "next_hearing": "2026-06-15",
            "judge": "Honorable J. Smith",
            "charge": "INA 212(a)(6)(A)(i)",
        }

    def check_uk_status(self, reference_number: str) -> dict:
        return {
            "reference_number": reference_number,
            "application_type": "Skilled Worker Visa",
            "status": "Awaiting Decision",
            "submitted_date": "2026-02-20",
            "expected_decision": "8-12 weeks from submission",
            "biometrics_completed": True,
        }

    def check_ircc_status(self, application_number: str) -> dict:
        return {
            "application_number": application_number,
            "application_type": "Express Entry - CEC",
            "status": "Application Received",
            "submitted_date": "2026-01-15",
            "background_check": "In Progress",
            "medical_exam": "Passed",
            "estimated_processing": "6 months",
        }

    def check_vevo_status(self, visa_grant_number: str) -> dict:
        return {
            "visa_grant_number": visa_grant_number,
            "visa_subclass": "482 - Temporary Skill Shortage",
            "status": "In Effect",
            "grant_date": "2025-09-01",
            "expiry_date": "2029-09-01",
            "work_rights": "Full work rights for nominated occupation",
            "conditions": ["8107 - Must work for sponsor", "8501 - Must maintain health insurance"],
        }

    def get_policy_alerts(self, countries: list[str] | None = None, visa_types: list[str] | None = None) -> list[dict]:
        alerts = [
            {"title": "USCIS Announces H-1B Cap Season Dates for FY2027", "date": "2026-03-15", "severity": "high",
             "countries": ["US"], "visa_types": ["H-1B"], "summary": "Registration period opens April 1-20, 2026."},
            {"title": "UK Home Office Updates Points-Based System Salary Thresholds", "date": "2026-03-10", "severity": "medium",
             "countries": ["UK"], "visa_types": ["Skilled Worker"], "summary": "Minimum salary for Skilled Worker visa increased."},
            {"title": "Canada Express Entry Draw #298 — CRS Cutoff 485", "date": "2026-03-18", "severity": "info",
             "countries": ["CA"], "visa_types": ["Express Entry"], "summary": "Latest draw invited 4,500 candidates."},
            {"title": "USCIS Fee Schedule Update Effective April 2026", "date": "2026-03-01", "severity": "high",
             "countries": ["US"], "visa_types": ["All"], "summary": "Filing fees increase for multiple form types."},
            {"title": "Australia Announces Changes to Subclass 482 Visa", "date": "2026-02-28", "severity": "medium",
             "countries": ["AU"], "visa_types": ["482"], "summary": "New occupation list and salary requirements."},
        ]
        if countries:
            alerts = [a for a in alerts if any(c in a["countries"] for c in countries)]
        return alerts

    def get_court_decisions(self, start: str | None = None, end: str | None = None) -> list[dict]:
        return [
            {"case": "Matter of Silva-Trevino III", "date": "2026-03-05", "court": "AG", "summary": "Updated categorical approach for moral turpitude analysis."},
            {"case": "Patel v. Garland", "date": "2026-02-20", "court": "Supreme Court", "summary": "Clarified scope of judicial review for discretionary relief."},
            {"case": "Niz-Chavez v. Garland", "date": "2026-01-15", "court": "Supreme Court", "summary": "NTA must contain all required information in single document."},
        ]

    def get_filing_fees(self, form_type: str) -> dict:
        fees = {
            "I-129": {"base_fee": 460, "fraud_fee": 500, "acwia_fee": 750, "premium": 2805},
            "I-130": {"base_fee": 535, "premium": None},
            "I-140": {"base_fee": 700, "premium": 2805},
            "I-485": {"base_fee": 1140, "biometrics": 85},
            "I-765": {"base_fee": 410},
            "I-131": {"base_fee": 575},
            "N-400": {"base_fee": 725, "biometrics": 85},
            "I-751": {"base_fee": 595, "biometrics": 85},
            "I-90": {"base_fee": 455, "biometrics": 85},
        }
        data = fees.get(form_type, {"base_fee": 0})
        return {"form_type": form_type, "effective_date": "2026-04-01", **data}

    def get_all_statuses(self, attorney_id: str) -> dict:
        return {
            "uscis": [
                self.check_uscis_status("WAC-26-123-45678"),
                self.check_uscis_status("LIN-26-087-12345"),
                self.check_uscis_status("EAC-26-234-56789"),
            ],
            "dol": [self.check_dol_status("A-19145-12345")],
            "sevis": [self.check_sevis_status("N0012345678")],
            "uk": [self.check_uk_status("GWF012345678")],
            "ircc": [self.check_ircc_status("E001234567")],
            "vevo": [self.check_vevo_status("1234567890")],
            "last_checked": date.today().isoformat(),
        }
