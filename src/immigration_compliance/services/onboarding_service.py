"""Magical Onboarding orchestrator — drives the multi-step welcome flow for both
applicants and attorneys. Tracks progress, fires AI assists at each step, and
returns a single source of truth the frontend can render.

Applicant flow:
  1. goal_selection         (visa family + destination country)
  2. visa_type_recommendation (AI-suggested visa types ranked)
  3. eligibility_questionnaire (adaptive per visa type)
  4. document_checklist     (personalized)
  5. strength_score         (with reason chain)
  6. red_flag_review        (issues to address)
  7. attorney_match         (AI-ranked attorneys)
  8. complete

Attorney flow:
  1. firm_info              (firm name, jurisdictions, AOR)
  2. credentials            (bar number, year admitted, specializations)
  3. document_upload        (bar cert, gov ID, malpractice insurance)
  4. capacity               (max cases, accepting new, languages)
  5. fee_structure          (preferred fee model, opt-in to marketplace)
  6. integration_setup      (calendar, payment processor, email)
  7. profile_review         (preview public profile)
  8. complete (queued for verification)
"""

from __future__ import annotations

import uuid
from datetime import datetime


APPLICANT_STEPS = [
    "goal_selection",
    "visa_type_recommendation",
    "eligibility_questionnaire",
    "document_checklist",
    "strength_score",
    "red_flag_review",
    "attorney_match",
    "complete",
]

ATTORNEY_STEPS = [
    "firm_info",
    "credentials",
    "document_upload",
    "capacity",
    "fee_structure",
    "integration_setup",
    "profile_review",
    "complete",
]


class OnboardingService:
    """Orchestrate magical onboarding for applicants and attorneys."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    # ---------- start / get ----------
    def start_applicant_onboarding(self, applicant_id: str) -> dict:
        return self._start(applicant_id, "applicant", APPLICANT_STEPS)

    def start_attorney_onboarding(self, attorney_id: str) -> dict:
        return self._start(attorney_id, "attorney", ATTORNEY_STEPS)

    def _start(self, user_id: str, role: str, steps: list[str]) -> dict:
        # Reuse if active session exists
        for s in self._sessions.values():
            if s["user_id"] == user_id and s["role"] == role and not s["completed"]:
                return s
        session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "role": role,
            "steps": [{"name": n, "status": "pending", "data": {}} for n in steps],
            "current_step_index": 0,
            "completed": False,
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress_pct": 0,
        }
        self._sessions[session["id"]] = session
        return session

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def get_session_for_user(self, user_id: str, role: str) -> dict | None:
        for s in self._sessions.values():
            if s["user_id"] == user_id and s["role"] == role:
                return s
        return None

    # ---------- step submission ----------
    def submit_step(self, session_id: str, step_name: str, data: dict) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        # Find step
        idx = next((i for i, s in enumerate(session["steps"]) if s["name"] == step_name), -1)
        if idx < 0:
            raise ValueError(f"Unknown step: {step_name}")
        step = session["steps"][idx]
        step["data"] = data
        step["status"] = "completed"
        step["completed_at"] = datetime.utcnow().isoformat()
        # Advance current pointer
        next_idx = next((i for i, s in enumerate(session["steps"]) if s["status"] != "completed"), len(session["steps"]) - 1)
        session["current_step_index"] = next_idx
        # Compute progress
        completed_count = sum(1 for s in session["steps"] if s["status"] == "completed")
        session["progress_pct"] = round((completed_count / len(session["steps"])) * 100)
        session["updated_at"] = datetime.utcnow().isoformat()
        # Auto-complete if final step is "complete"
        if session["steps"][-1]["name"] == "complete" and idx == len(session["steps"]) - 2:
            session["steps"][-1]["status"] = "completed"
            session["completed"] = True
            session["completed_at"] = datetime.utcnow().isoformat()
            session["progress_pct"] = 100
        return session

    def reset_step(self, session_id: str, step_name: str) -> dict | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        for s in session["steps"]:
            if s["name"] == step_name:
                s["status"] = "pending"
                s["data"] = {}
                s.pop("completed_at", None)
        completed_count = sum(1 for s in session["steps"] if s["status"] == "completed")
        session["progress_pct"] = round((completed_count / len(session["steps"])) * 100)
        session["completed"] = False
        return session

    def list_sessions(self, role: str | None = None) -> list[dict]:
        sessions = list(self._sessions.values())
        if role:
            sessions = [s for s in sessions if s["role"] == role]
        return sessions
