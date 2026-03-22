"""Video consultation, scheduling, and interview prep service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from immigration_compliance.models.consultation import (
    AvailabilityUpdate,
    Consultation,
    ConsultationStatus,
    ConsultationType,
    InterviewType,
    MockInterviewQuestion,
    MockInterviewSession,
)


# Mock interview question banks by type
_INTERVIEW_QUESTIONS: dict[InterviewType, list[MockInterviewQuestion]] = {
    InterviewType.USCIS_MARRIAGE: [
        MockInterviewQuestion(
            question="How did you and your spouse meet?",
            category="relationship",
            tip="Be specific about dates, locations, and circumstances. Vague answers raise red flags.",
            follow_up="Who introduced you? Were there mutual friends?",
        ),
        MockInterviewQuestion(
            question="When did you get married? Describe the ceremony.",
            category="relationship",
            tip="Know details: venue, guests, who officiated, what you wore.",
            follow_up="How many guests attended? Who was your best man/maid of honor?",
        ),
        MockInterviewQuestion(
            question="Where do you and your spouse currently live? Describe your home.",
            category="personal",
            tip="Both spouses should give consistent answers about layout, furniture, neighborhood.",
            follow_up="How many bedrooms? Which side of the bed do you sleep on?",
        ),
        MockInterviewQuestion(
            question="What does your spouse do for work?",
            category="employment",
            tip="Know their employer name, job title, work schedule, and commute.",
            follow_up="What is their salary range? Do they enjoy their work?",
        ),
        MockInterviewQuestion(
            question="Describe your typical morning routine together.",
            category="personal",
            tip="Daily routine questions test genuine cohabitation. Be natural and consistent.",
            follow_up="Who wakes up first? Who makes breakfast?",
        ),
        MockInterviewQuestion(
            question="What did you do for your last anniversary?",
            category="relationship",
            tip="Remember specific celebrations, gifts, and plans.",
            follow_up="What gift did you give/receive?",
        ),
        MockInterviewQuestion(
            question="Have you met your spouse's family? Describe them.",
            category="relationship",
            tip="Know names of in-laws, siblings, and where they live.",
            follow_up="How often do you see them? Do you communicate with them?",
        ),
        MockInterviewQuestion(
            question="Do you have joint bank accounts or shared finances?",
            category="personal",
            tip="Joint accounts, shared bills, and financial entanglement strengthen your case.",
            follow_up="How do you split household expenses?",
        ),
        MockInterviewQuestion(
            question="What religion does your spouse practice?",
            category="personal",
            tip="Know basic facts even if you don't share the same religion.",
            follow_up="Do you attend services together?",
        ),
        MockInterviewQuestion(
            question="Have you taken any trips together? Where?",
            category="travel",
            tip="Have photos, boarding passes, or hotel receipts as evidence.",
            follow_up="When was your last vacation? Where did you stay?",
        ),
    ],
    InterviewType.USCIS_NATURALIZATION: [
        MockInterviewQuestion(
            question="Why do you want to become a U.S. citizen?",
            category="personal",
            tip="Be genuine. Common answers: voting, travel, stability, civic duty.",
        ),
        MockInterviewQuestion(
            question="Have you ever been arrested, cited, or detained by law enforcement?",
            category="personal",
            tip="Disclose everything, even minor incidents. Lying is grounds for denial.",
        ),
        MockInterviewQuestion(
            question="Have you traveled outside the United States in the last 5 years?",
            category="travel",
            tip="Know exact dates and countries. Bring your passport.",
            follow_up="How long was each trip?",
        ),
        MockInterviewQuestion(
            question="Are you willing to take the full Oath of Allegiance?",
            category="personal",
            tip="You must affirm willingness. Religious accommodations are available.",
        ),
        MockInterviewQuestion(
            question="Have you ever claimed to be a U.S. citizen?",
            category="personal",
            tip="Answering 'yes' can be disqualifying. Be truthful.",
        ),
        MockInterviewQuestion(
            question="What is the supreme law of the land?",
            category="civics",
            tip="The Constitution. Study the 100 civics questions thoroughly.",
        ),
        MockInterviewQuestion(
            question="How many amendments does the Constitution have?",
            category="civics",
            tip="27 amendments.",
        ),
        MockInterviewQuestion(
            question="Who is the current President of the United States?",
            category="civics",
            tip="Know the current President and Vice President.",
        ),
    ],
    InterviewType.CONSULAR: [
        MockInterviewQuestion(
            question="What is the purpose of your trip to the United States?",
            category="personal",
            tip="Be concise and specific. State your exact reason (study, work, visit).",
        ),
        MockInterviewQuestion(
            question="Who is sponsoring your visa / who will you be working for?",
            category="employment",
            tip="Know your employer/university name, address, and what you'll be doing.",
        ),
        MockInterviewQuestion(
            question="How will you fund your stay?",
            category="personal",
            tip="Have bank statements, scholarship letters, or sponsor affidavits ready.",
        ),
        MockInterviewQuestion(
            question="Do you have ties to your home country? What will bring you back?",
            category="personal",
            tip="Strong ties (family, property, job) reduce visa denial risk.",
            follow_up="Do you own property? Do you have family here?",
        ),
        MockInterviewQuestion(
            question="Have you ever been denied a visa before?",
            category="travel",
            tip="Be honest. Explain circumstances if yes.",
        ),
        MockInterviewQuestion(
            question="What are your plans after your program/assignment ends?",
            category="personal",
            tip="Show intent to return home. Mention specific career plans.",
        ),
    ],
    InterviewType.USCIS_ASYLUM: [
        MockInterviewQuestion(
            question="Why are you afraid to return to your home country?",
            category="personal",
            tip="Be specific about threats, incidents, and who harmed or threatened you.",
        ),
        MockInterviewQuestion(
            question="Have you or your family been harmed or threatened?",
            category="personal",
            tip="Provide dates, locations, and details of each incident.",
            follow_up="Did you report this to police? What happened?",
        ),
        MockInterviewQuestion(
            question="Why can't your government protect you?",
            category="personal",
            tip="Explain corruption, complicity, or inability of authorities.",
        ),
        MockInterviewQuestion(
            question="Why did you choose to come to the United States?",
            category="travel",
            tip="Explain why the U.S. specifically, not just 'anywhere safe'.",
        ),
        MockInterviewQuestion(
            question="When did you enter the United States and how?",
            category="travel",
            tip="Be truthful about entry. Asylum must be filed within 1 year of arrival.",
        ),
    ],
    InterviewType.UK_HOME_OFFICE: [
        MockInterviewQuestion(
            question="What course are you studying and at which institution?",
            category="employment",
            tip="Know your course name, start date, duration, and campus location.",
        ),
        MockInterviewQuestion(
            question="How are you funding your studies and living expenses?",
            category="personal",
            tip="Have evidence of funds: bank statements, sponsor letters, scholarship proof.",
        ),
        MockInterviewQuestion(
            question="What are your plans after completing your studies?",
            category="personal",
            tip="Show awareness of Graduate visa route or plans to return home.",
        ),
        MockInterviewQuestion(
            question="Why did you choose the UK over other countries?",
            category="personal",
            tip="Mention specific reasons: university ranking, course specialization, language.",
        ),
    ],
    InterviewType.CANADA_IRCC: [
        MockInterviewQuestion(
            question="What is your purpose for coming to Canada?",
            category="personal",
            tip="Be clear and specific about study/work/PR intentions.",
        ),
        MockInterviewQuestion(
            question="How did you choose your Designated Learning Institution?",
            category="employment",
            tip="Show genuine research into the program and institution.",
        ),
        MockInterviewQuestion(
            question="How will you support yourself financially in Canada?",
            category="personal",
            tip="Know the minimum funds requirement and show proof.",
        ),
    ],
    InterviewType.EMPLOYMENT_BASED: [
        MockInterviewQuestion(
            question="Describe your current role and responsibilities.",
            category="employment",
            tip="Match your answer to what's on your petition. Consistency is key.",
        ),
        MockInterviewQuestion(
            question="What specialized skills do you bring that a U.S. worker cannot?",
            category="employment",
            tip="Be specific about your expertise, education, and unique qualifications.",
        ),
        MockInterviewQuestion(
            question="How long have you been with your current employer?",
            category="employment",
            tip="Know exact dates. Have employment verification letter ready.",
        ),
        MockInterviewQuestion(
            question="What is your educational background?",
            category="employment",
            tip="Know your degrees, institutions, graduation dates, and how they relate to the job.",
        ),
    ],
}


class ConsultationService:
    """Manages video consultations, scheduling, and interview prep."""

    def __init__(self) -> None:
        self._consultations: dict[str, Consultation] = {}
        self._availability: dict[str, list[AvailabilityUpdate]] = {}  # attorney_id -> slots
        self._mock_sessions: dict[str, MockInterviewSession] = {}

    # --- Consultations ---

    def request_consultation(
        self, applicant_id: str, attorney_id: str,
        consultation_type: ConsultationType,
        preferred_date: str, preferred_time: str,
        duration: int = 30, notes: str = "", case_id: str = "",
    ) -> Consultation:
        consultation_id = f"consult_{uuid.uuid4().hex[:12]}"
        room_id = f"room_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        scheduled = ""
        if preferred_date and preferred_time:
            scheduled = f"{preferred_date}T{preferred_time}:00Z"

        c = Consultation(
            id=consultation_id,
            applicant_id=applicant_id,
            attorney_id=attorney_id,
            consultation_type=consultation_type,
            status=ConsultationStatus.REQUESTED if not scheduled else ConsultationStatus.SCHEDULED,
            scheduled_at=scheduled,
            duration_minutes=duration,
            room_id=room_id,
            room_url=f"/consultation/room/{room_id}",
            notes=notes,
            case_id=case_id,
            created_at=now,
        )
        self._consultations[consultation_id] = c
        return c

    def get_consultation(self, consultation_id: str) -> Consultation | None:
        return self._consultations.get(consultation_id)

    def list_consultations(
        self, user_id: str, role: str = "applicant"
    ) -> list[Consultation]:
        results = []
        for c in self._consultations.values():
            if role == "applicant" and c.applicant_id == user_id:
                results.append(c)
            elif role == "attorney" and c.attorney_id == user_id:
                results.append(c)
        return results

    def update_status(
        self, consultation_id: str, status: ConsultationStatus
    ) -> Consultation | None:
        c = self._consultations.get(consultation_id)
        if c is None:
            return None
        updated = c.model_copy(update={"status": status})
        self._consultations[consultation_id] = updated
        return updated

    # --- Attorney availability ---

    def set_availability(self, attorney_id: str, slots: list[AvailabilityUpdate]) -> None:
        self._availability[attorney_id] = slots

    def get_available_slots(self, attorney_id: str, date: str) -> list[dict]:
        """Get available 30-min slots for a given attorney on a given date."""
        avail = self._availability.get(attorney_id, [])
        if not avail:
            # Default: Mon-Fri 9-5
            return [
                {"time": f"{h:02d}:{m:02d}", "available": True}
                for h in range(9, 17) for m in (0, 30)
            ]

        try:
            dt = datetime.fromisoformat(date)
            dow = dt.weekday()
        except ValueError:
            return []

        slots = []
        for a in avail:
            if a.day_of_week == dow and a.available:
                start_h, start_m = map(int, a.start_time.split(":"))
                end_h, end_m = map(int, a.end_time.split(":"))
                current = start_h * 60 + start_m
                end = end_h * 60 + end_m
                while current + 30 <= end:
                    h, m = divmod(current, 60)
                    slots.append({"time": f"{h:02d}:{m:02d}", "available": True})
                    current += 30
        return slots

    # --- Interview Prep ---

    def start_mock_interview(
        self, user_id: str, interview_type: InterviewType
    ) -> MockInterviewSession:
        session_id = f"mock_{uuid.uuid4().hex[:12]}"
        questions = list(_INTERVIEW_QUESTIONS.get(interview_type, []))
        session = MockInterviewSession(
            id=session_id,
            user_id=user_id,
            interview_type=interview_type,
            questions=questions,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._mock_sessions[session_id] = session
        return session

    def get_mock_session(self, session_id: str) -> MockInterviewSession | None:
        return self._mock_sessions.get(session_id)

    def complete_mock_interview(self, session_id: str, score: int) -> MockInterviewSession | None:
        session = self._mock_sessions.get(session_id)
        if session is None:
            return None
        updated = session.model_copy(update={"completed": True, "score": max(0, min(100, score))})
        self._mock_sessions[session_id] = updated
        return updated

    def list_mock_sessions(self, user_id: str) -> list[MockInterviewSession]:
        return [s for s in self._mock_sessions.values() if s.user_id == user_id]

    @staticmethod
    def get_interview_types() -> list[dict]:
        return [
            {"type": t.value, "label": t.value.replace("_", " ").title(),
             "question_count": len(_INTERVIEW_QUESTIONS.get(t, []))}
            for t in InterviewType
        ]
