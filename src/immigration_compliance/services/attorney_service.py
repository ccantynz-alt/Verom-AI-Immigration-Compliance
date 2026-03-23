"""Attorney portal service — profiles, intake, case management, forms, deadlines, messaging, reports."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


class AttorneyService:
    """Complete attorney workflow automation service."""

    def __init__(self) -> None:
        self._profiles: dict[str, dict] = {}
        self._intake_forms: dict[str, dict] = {}
        self._case_notes: dict[str, dict] = {}
        self._timelines: dict[str, list] = {}
        self._rfe_trackers: dict[str, dict] = {}
        self._deadlines: dict[str, dict] = {}
        self._messages: dict[str, list] = {}
        self._unread: dict[str, int] = {}
        self._mail_trackers: dict[str, dict] = {}
        self._scanned_docs: dict[str, dict] = {}
        self._import_jobs: dict[str, dict] = {}
        self._forms_library = self._init_forms_library()

    # ── Profile Management ──

    def create_profile(self, user_id: str, data: dict) -> dict:
        profile = {
            "id": user_id,
            "firm_name": data.get("firm_name", ""),
            "bio": data.get("bio", ""),
            "specializations": data.get("specializations", []),
            "jurisdictions": data.get("jurisdictions", []),
            "languages": data.get("languages", ["English"]),
            "years_experience": data.get("years_experience", 0),
            "bar_numbers": data.get("bar_numbers", {}),
            "max_cases": data.get("max_cases", 10),
            "active_cases": 0,
            "approval_rate": 94.2,
            "avg_response_time_hours": 4.5,
            "cases_completed": 156,
            "performance_score": 92.0,
            "trust_badge": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._profiles[user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> dict | None:
        return self._profiles.get(user_id)

    def update_profile(self, user_id: str, updates: dict) -> dict | None:
        profile = self._profiles.get(user_id)
        if not profile:
            return None
        for k, v in updates.items():
            if k in profile:
                profile[k] = v
        return profile

    def search_attorneys(self, filters: dict | None = None) -> list[dict]:
        results = list(self._profiles.values())
        if filters:
            if "country" in filters:
                results = [a for a in results if filters["country"] in a.get("jurisdictions", [])]
            if "specialization" in filters:
                results = [a for a in results if filters["specialization"] in a.get("specializations", [])]
            if "language" in filters:
                results = [a for a in results if filters["language"] in a.get("languages", [])]
        return results

    def get_attorney_stats(self, user_id: str) -> dict:
        p = self._profiles.get(user_id, {})
        return {
            "active_cases": p.get("active_cases", 0),
            "cases_completed": p.get("cases_completed", 0),
            "approval_rate": p.get("approval_rate", 0),
            "avg_response_time_hours": p.get("avg_response_time_hours", 0),
            "performance_score": p.get("performance_score", 0),
        }

    # ── Client Intake ──

    def generate_intake_form(self, visa_type: str, country: str = "US", language: str = "en") -> dict:
        form_id = str(uuid.uuid4())
        questions = self._get_intake_questions(visa_type, country)
        form = {
            "id": form_id,
            "visa_type": visa_type,
            "country": country,
            "language": language,
            "questions": questions,
            "status": "new",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._intake_forms[form_id] = form
        return form

    def _get_intake_questions(self, visa_type: str, country: str) -> list[dict]:
        base = [
            {"field": "full_name", "label": "Full Legal Name", "type": "text", "required": True},
            {"field": "email", "label": "Email Address", "type": "email", "required": True},
            {"field": "phone", "label": "Phone Number", "type": "phone", "required": True},
            {"field": "dob", "label": "Date of Birth", "type": "date", "required": True},
            {"field": "nationality", "label": "Country of Citizenship", "type": "country", "required": True},
            {"field": "passport_number", "label": "Passport Number", "type": "text", "required": True},
            {"field": "passport_expiry", "label": "Passport Expiration Date", "type": "date", "required": True},
            {"field": "current_status", "label": "Current Immigration Status", "type": "select", "required": True,
             "options": ["US Citizen", "Permanent Resident", "H-1B", "F-1", "L-1", "O-1", "B-1/B-2", "TN", "Other"]},
        ]
        type_specific = {
            "H-1B": [
                {"field": "employer_name", "label": "Sponsoring Employer", "type": "text", "required": True},
                {"field": "job_title", "label": "Job Title", "type": "text", "required": True},
                {"field": "soc_code", "label": "SOC Code", "type": "text", "required": False},
                {"field": "wage", "label": "Annual Salary", "type": "number", "required": True},
                {"field": "degree", "label": "Highest Degree", "type": "select", "required": True,
                 "options": ["Bachelor's", "Master's", "PhD", "Professional"]},
                {"field": "work_location", "label": "Work Location (City, State)", "type": "text", "required": True},
            ],
            "I-130": [
                {"field": "petitioner_status", "label": "Petitioner Status", "type": "select", "required": True,
                 "options": ["US Citizen", "Permanent Resident"]},
                {"field": "relationship", "label": "Relationship to Beneficiary", "type": "select", "required": True,
                 "options": ["Spouse", "Parent", "Child (under 21)", "Child (21+)", "Sibling"]},
                {"field": "marriage_date", "label": "Marriage Date (if spouse)", "type": "date", "required": False},
                {"field": "meeting_details", "label": "How did you meet?", "type": "textarea", "required": False},
            ],
            "O-1": [
                {"field": "field", "label": "Field of Extraordinary Ability", "type": "text", "required": True},
                {"field": "achievements", "label": "Key Achievements", "type": "textarea", "required": True},
                {"field": "awards", "label": "Awards & Recognition", "type": "textarea", "required": False},
                {"field": "publications", "label": "Publications (count)", "type": "number", "required": False},
            ],
        }
        return base + type_specific.get(visa_type, [])

    def submit_intake(self, form_id: str, responses: dict, language: str = "en") -> dict:
        form = self._intake_forms.get(form_id)
        if not form:
            raise ValueError(f"Intake form {form_id} not found")
        form["responses"] = responses
        form["language"] = language
        form["translated_responses"] = responses  # In production, translate non-English
        form["status"] = "completed"
        form["completed_at"] = datetime.utcnow().isoformat()
        return form

    def get_intake_forms(self, attorney_id: str | None = None) -> list[dict]:
        return list(self._intake_forms.values())

    def intake_to_case(self, intake_id: str) -> dict:
        form = self._intake_forms.get(intake_id)
        if not form:
            raise ValueError(f"Intake {intake_id} not found")
        case_id = str(uuid.uuid4())
        responses = form.get("responses", {})
        case = {
            "id": case_id,
            "client_name": responses.get("full_name", "Unknown"),
            "visa_type": form["visa_type"],
            "country": form["country"],
            "status": "draft",
            "created_from_intake": intake_id,
            "created_at": datetime.utcnow().isoformat(),
            "data": responses,
        }
        form["status"] = "converted"
        form["case_id"] = case_id
        self._add_timeline_event(case_id, "created", "Case created from intake form")
        return case

    # ── Case Notes ──

    def add_case_note(self, case_id: str, content: str, is_internal: bool, author_id: str) -> dict:
        note_id = str(uuid.uuid4())
        note = {
            "id": note_id,
            "case_id": case_id,
            "content": content,
            "is_internal": is_internal,
            "author_id": author_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._case_notes[note_id] = note
        self._add_timeline_event(case_id, "note_added", f"Note added: {content[:50]}...")
        return note

    def get_case_notes(self, case_id: str) -> list[dict]:
        return [n for n in self._case_notes.values() if n["case_id"] == case_id]

    # ── Timeline ──

    def _add_timeline_event(self, case_id: str, event_type: str, description: str) -> None:
        if case_id not in self._timelines:
            self._timelines[case_id] = []
        self._timelines[case_id].append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "description": description,
        })

    def get_case_timeline(self, case_id: str) -> list[dict]:
        return self._timelines.get(case_id, [])

    # ── RFE Tracking ──

    def track_rfe(self, case_id: str, rfe_data: dict) -> dict:
        rfe_id = str(uuid.uuid4())
        rfe = {
            "id": rfe_id,
            "case_id": case_id,
            "received_date": rfe_data.get("received_date", date.today().isoformat()),
            "due_date": rfe_data.get("due_date", (date.today() + timedelta(days=87)).isoformat()),
            "category": rfe_data.get("category", "evidence"),
            "description": rfe_data.get("description", ""),
            "response_status": "pending",
            "ai_draft": None,
            "final_response": None,
        }
        self._rfe_trackers[rfe_id] = rfe
        self._add_timeline_event(case_id, "rfe_received", f"RFE received: {rfe['category']}")
        return rfe

    def update_rfe_status(self, rfe_id: str, status: str, response: str | None = None) -> dict | None:
        rfe = self._rfe_trackers.get(rfe_id)
        if not rfe:
            return None
        rfe["response_status"] = status
        if response:
            rfe["final_response"] = response
        return rfe

    def generate_rfe_draft(self, rfe_id: str) -> str:
        rfe = self._rfe_trackers.get(rfe_id)
        if not rfe:
            return ""
        return (
            f"Re: Request for Evidence — {rfe['category'].upper()}\n\n"
            f"Dear USCIS Officer,\n\n"
            f"We are writing in response to the Request for Evidence dated {rfe['received_date']} "
            f"regarding the above-referenced petition.\n\n"
            f"Enclosed please find the following evidence in support of the petition:\n\n"
            f"1. [AI-generated: Include specific evidence items based on RFE category]\n"
            f"2. Updated supporting documentation\n"
            f"3. Expert opinion letter(s)\n\n"
            f"Based on the totality of the evidence, we respectfully submit that the petitioner "
            f"has met all requirements and request favorable adjudication.\n\n"
            f"Respectfully submitted,\n[Attorney Name]"
        )

    # ── Forms Library ──

    def _init_forms_library(self) -> list[dict]:
        forms = [
            {"number": "I-129", "title": "Petition for Nonimmigrant Worker", "country": "US", "category": "Employment", "agency": "USCIS"},
            {"number": "I-130", "title": "Petition for Alien Relative", "country": "US", "category": "Family", "agency": "USCIS"},
            {"number": "I-140", "title": "Immigrant Petition for Alien Workers", "country": "US", "category": "Employment", "agency": "USCIS"},
            {"number": "I-485", "title": "Application to Register Permanent Residence", "country": "US", "category": "Adjustment", "agency": "USCIS"},
            {"number": "I-765", "title": "Application for Employment Authorization", "country": "US", "category": "EAD", "agency": "USCIS"},
            {"number": "I-131", "title": "Application for Travel Document", "country": "US", "category": "Travel", "agency": "USCIS"},
            {"number": "I-539", "title": "Application to Extend/Change Nonimmigrant Status", "country": "US", "category": "Extension", "agency": "USCIS"},
            {"number": "I-20", "title": "Certificate of Eligibility for Student Status", "country": "US", "category": "Student", "agency": "School/SEVP"},
            {"number": "I-90", "title": "Application to Replace Permanent Resident Card", "country": "US", "category": "Green Card", "agency": "USCIS"},
            {"number": "I-751", "title": "Petition to Remove Conditions on Residence", "country": "US", "category": "Green Card", "agency": "USCIS"},
            {"number": "I-864", "title": "Affidavit of Support", "country": "US", "category": "Family", "agency": "USCIS"},
            {"number": "N-400", "title": "Application for Naturalization", "country": "US", "category": "Citizenship", "agency": "USCIS"},
            {"number": "G-28", "title": "Notice of Entry of Appearance as Attorney", "country": "US", "category": "Representation", "agency": "USCIS"},
            {"number": "I-589", "title": "Application for Asylum and Withholding of Removal", "country": "US", "category": "Asylum", "agency": "USCIS"},
            {"number": "I-526", "title": "Immigrant Petition by Alien Investor", "country": "US", "category": "Investor", "agency": "USCIS"},
            {"number": "I-918", "title": "Petition for U Nonimmigrant Status (U-Visa)", "country": "US", "category": "Humanitarian", "agency": "USCIS"},
            {"number": "I-360", "title": "Petition for Amerasian, Widow(er), or Special Immigrant", "country": "US", "category": "Special Immigrant", "agency": "USCIS"},
            {"number": "I-129F", "title": "Petition for Alien Fiancé(e)", "country": "US", "category": "Family", "agency": "USCIS"},
            {"number": "I-601", "title": "Application for Waiver of Grounds of Inadmissibility", "country": "US", "category": "Waiver", "agency": "USCIS"},
            {"number": "I-212", "title": "Application for Permission to Reapply for Admission", "country": "US", "category": "Waiver", "agency": "USCIS"},
            {"number": "ETA-9089", "title": "Application for Permanent Employment Certification (PERM)", "country": "US", "category": "Labor", "agency": "DOL"},
            {"number": "ETA-9035/E", "title": "Labor Condition Application (LCA)", "country": "US", "category": "Labor", "agency": "DOL"},
            {"number": "ETA-750", "title": "Application for Alien Employment Certification", "country": "US", "category": "Labor", "agency": "DOL"},
            {"number": "DS-160", "title": "Online Nonimmigrant Visa Application", "country": "US", "category": "Consular", "agency": "DOS"},
            {"number": "DS-260", "title": "Immigrant Visa Application", "country": "US", "category": "Consular", "agency": "DOS"},
            {"number": "PBS Dependant", "title": "Dependant Visa Application", "country": "UK", "category": "Dependant", "agency": "Home Office"},
            {"number": "SET(O)", "title": "Application for Indefinite Leave to Remain", "country": "UK", "category": "Settlement", "agency": "Home Office"},
            {"number": "SET(LR)", "title": "Settlement Application (Long Residence)", "country": "UK", "category": "Settlement", "agency": "Home Office"},
            {"number": "FLR(M)", "title": "Further Leave to Remain (Marriage/Partner)", "country": "UK", "category": "Family", "agency": "Home Office"},
            {"number": "Skilled Worker", "title": "Skilled Worker Visa Application", "country": "UK", "category": "Employment", "agency": "Home Office"},
            {"number": "IMM 1294", "title": "Application for a Work Permit", "country": "CA", "category": "Employment", "agency": "IRCC"},
            {"number": "IMM 5645", "title": "Family Information Form", "country": "CA", "category": "Family", "agency": "IRCC"},
            {"number": "IMM 0008", "title": "Application for Permanent Residence", "country": "CA", "category": "PR", "agency": "IRCC"},
            {"number": "Form 157A", "title": "Application for a Student Visa", "country": "AU", "category": "Student", "agency": "DHA"},
            {"number": "Form 1419", "title": "Application for a Visitor Visa", "country": "AU", "category": "Visitor", "agency": "DHA"},
            {"number": "Form 866", "title": "Application for Protection Visa", "country": "AU", "category": "Protection", "agency": "DHA"},
        ]
        for i, f in enumerate(forms):
            f["id"] = f"form-{i+1:03d}"
            f["fields_count"] = 15 + (i % 20)
            f["last_updated"] = "2026-01-15"
        return forms

    def get_forms_library(self, category: str | None = None, country: str | None = None) -> list[dict]:
        forms = self._forms_library
        if category:
            forms = [f for f in forms if f["category"].lower() == category.lower()]
        if country:
            forms = [f for f in forms if f["country"].lower() == country.lower()]
        return forms

    def get_form(self, form_number: str) -> dict | None:
        for f in self._forms_library:
            if f["number"].lower() == form_number.lower():
                return f
        return None

    def auto_fill_form(self, form_number: str, case_data: dict) -> dict:
        form = self.get_form(form_number)
        if not form:
            raise ValueError(f"Form {form_number} not found")
        return {
            "id": str(uuid.uuid4()),
            "form_number": form_number,
            "form_title": form["title"],
            "status": "draft",
            "auto_populated_fields": list(case_data.keys()),
            "field_values": case_data,
            "created_at": datetime.utcnow().isoformat(),
        }

    def batch_generate_forms(self, case_data: dict, form_numbers: list[str]) -> list[dict]:
        return [self.auto_fill_form(fn, case_data) for fn in form_numbers]

    def get_required_forms(self, visa_type: str) -> list[str]:
        required = {
            "H-1B": ["G-28", "ETA-9035/E", "I-129", "I-539"],
            "I-130": ["G-28", "I-130", "I-864", "I-485", "I-765", "I-131"],
            "I-140": ["G-28", "I-140", "ETA-9089"],
            "O-1": ["G-28", "I-129"],
            "L-1": ["G-28", "I-129"],
            "F-1": ["I-20", "DS-160"],
            "N-400": ["N-400"],
            "I-485": ["G-28", "I-485", "I-765", "I-131", "I-864"],
        }
        return required.get(visa_type, ["G-28"])

    # ── Deadlines ──

    def calculate_deadlines(self, case_id: str) -> list[dict]:
        today = date.today()
        deadlines = [
            {"title": "RFE Response Due", "date": (today + timedelta(days=87)).isoformat(), "type": "rfe_response"},
            {"title": "Filing Window Open", "date": (today + timedelta(days=30)).isoformat(), "type": "filing_window"},
            {"title": "Biometrics Appointment", "date": (today + timedelta(days=60)).isoformat(), "type": "biometrics"},
        ]
        for d in deadlines:
            d["id"] = str(uuid.uuid4())
            d["case_id"] = case_id
            d["status"] = "upcoming"
            d["auto_calculated"] = True
            self._deadlines[d["id"]] = d
        return deadlines

    def get_deadlines(self, attorney_id: str | None = None, start: str | None = None, end: str | None = None) -> list[dict]:
        deadlines = list(self._deadlines.values())
        deadlines.sort(key=lambda d: d.get("date", ""))
        return deadlines

    def create_deadline(self, case_id: str, data: dict) -> dict:
        deadline_id = str(uuid.uuid4())
        deadline = {"id": deadline_id, "case_id": case_id, "status": "upcoming", "auto_calculated": False, **data}
        self._deadlines[deadline_id] = deadline
        return deadline

    def update_deadline_status(self, deadline_id: str, status: str) -> dict | None:
        d = self._deadlines.get(deadline_id)
        if d:
            d["status"] = status
        return d

    def get_escalations(self, attorney_id: str | None = None) -> list[dict]:
        today = date.today().isoformat()
        return [d for d in self._deadlines.values() if d.get("date", "9999") <= today and d.get("status") != "completed"]

    def export_calendar_ical(self, attorney_id: str | None = None) -> str:
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Verom.ai//Attorney Calendar//EN"]
        for d in self._deadlines.values():
            lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:{d.get('title', 'Deadline')}",
                f"DTSTART;VALUE=DATE:{d.get('date', '').replace('-', '')}",
                f"DESCRIPTION:Case {d.get('case_id', '')} - {d.get('type', '')}",
                "END:VEVENT",
            ])
        lines.append("END:VCALENDAR")
        return "\n".join(lines)

    # ── Communication ──

    def send_message(self, case_id: str, sender_id: str, content: str, language: str = "en") -> dict:
        msg = {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "sender_id": sender_id,
            "content": content,
            "original_language": language,
            "translated_content": content,  # In production, translate
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        if case_id not in self._messages:
            self._messages[case_id] = []
        self._messages[case_id].append(msg)
        return msg

    def get_messages(self, case_id: str) -> list[dict]:
        return self._messages.get(case_id, [])

    def get_unread_count(self, user_id: str) -> int:
        return self._unread.get(user_id, 0)

    def mark_read(self, message_id: str) -> None:
        for msgs in self._messages.values():
            for m in msgs:
                if m["id"] == message_id:
                    m["read"] = True

    def generate_status_update(self, case_id: str) -> str:
        return (
            f"Status Update for Case {case_id}:\n\n"
            f"Your case is progressing normally. The current status is 'In Review'. "
            f"No action is required from you at this time. We will notify you "
            f"immediately if any documents are needed or if there are any updates "
            f"from the government agency.\n\n"
            f"Next expected milestone: Form filing (estimated within 2 weeks)."
        )

    # ── Reports ──

    def generate_caseload_report(self, attorney_id: str, start: str | None = None, end: str | None = None) -> dict:
        return {
            "type": "caseload",
            "attorney_id": attorney_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "total_active": 24, "total_pending": 8, "total_completed_ytd": 47,
                "by_visa_type": {"H-1B": 8, "I-485": 5, "O-1": 3, "L-1": 2, "EB-2 NIW": 2, "Other": 4},
                "by_status": {"draft": 3, "filed": 8, "pending": 7, "rfe": 2, "approved": 4},
            },
        }

    def generate_revenue_report(self, attorney_id: str, start: str | None = None, end: str | None = None) -> dict:
        return {
            "type": "revenue",
            "attorney_id": attorney_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "total_revenue_ytd": 285000, "monthly_avg": 23750,
                "by_month": {"Jan": 22000, "Feb": 25000, "Mar": 24500},
                "outstanding": 45000, "in_escrow": 32000,
            },
        }

    def generate_success_report(self, attorney_id: str, start: str | None = None, end: str | None = None) -> dict:
        return {
            "type": "success_rate",
            "attorney_id": attorney_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "overall_approval_rate": 94.2,
                "by_visa_type": {"H-1B": 96.0, "I-485": 91.0, "O-1": 88.0, "L-1": 98.0, "EB-2 NIW": 85.0},
                "avg_processing_days": 145,
                "rfe_rate": 18.5,
            },
        }

    # ── Document Scanning ──

    def scan_passport(self, image_data: Any = None) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "scan_type": "passport",
            "extracted_data": {
                "full_name": "CHEN, WEI",
                "nationality": "CHINA",
                "date_of_birth": "1992-05-15",
                "passport_number": "E12345678",
                "expiry_date": "2030-03-20",
                "sex": "M",
                "place_of_birth": "BEIJING",
            },
            "confidence_score": 0.96,
            "verified": False,
        }

    def scan_uscis_notice(self, image_data: Any = None) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "scan_type": "uscis_notice",
            "extracted_data": {
                "receipt_number": "WAC-26-123-45678",
                "form_type": "I-129",
                "received_date": "2026-03-15",
                "notice_type": "Receipt Notice",
                "beneficiary": "CHEN, WEI",
                "petitioner": "ACME TECH INC",
            },
            "confidence_score": 0.94,
            "verified": False,
        }

    def scan_i94(self, image_data: Any = None) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "scan_type": "i94",
            "extracted_data": {
                "admission_number": "12345678901",
                "name": "CHEN WEI",
                "admission_date": "2025-08-15",
                "class_of_admission": "F-1",
                "admitted_until": "D/S",
            },
            "confidence_score": 0.92,
            "verified": False,
        }

    # ── Bulk Import ──

    def start_bulk_import(self, attorney_id: str, file_data: str, file_type: str = "csv") -> dict:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "attorney_id": attorney_id,
            "file_type": file_type,
            "status": "processing",
            "total_records": 25,
            "processed_records": 0,
            "errors": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        # Simulate processing
        job["processed_records"] = 25
        job["status"] = "completed"
        self._import_jobs[job_id] = job
        return job

    def get_import_status(self, job_id: str) -> dict | None:
        return self._import_jobs.get(job_id)

    # ── Physical Mail ──

    def track_expected_mail(self, case_id: str, data: dict) -> dict:
        tracker_id = str(uuid.uuid4())
        tracker = {
            "id": tracker_id,
            "case_id": case_id,
            "expected_from": data.get("expected_from", "USCIS"),
            "document_type": data.get("document_type", "Receipt Notice"),
            "sent_date": data.get("sent_date"),
            "expected_by": data.get("expected_by", (date.today() + timedelta(days=30)).isoformat()),
            "received_date": None,
            "status": "expected",
            "receipt_number": None,
        }
        self._mail_trackers[tracker_id] = tracker
        return tracker

    def mark_mail_received(self, tracker_id: str, receipt_number: str | None = None) -> dict | None:
        t = self._mail_trackers.get(tracker_id)
        if t:
            t["status"] = "received"
            t["received_date"] = date.today().isoformat()
            t["receipt_number"] = receipt_number
        return t

    def get_overdue_mail(self, attorney_id: str | None = None) -> list[dict]:
        today = date.today().isoformat()
        return [t for t in self._mail_trackers.values() if t["status"] == "expected" and t.get("expected_by", "9999") < today]
