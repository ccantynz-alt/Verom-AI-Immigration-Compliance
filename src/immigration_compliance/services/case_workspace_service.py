"""Case Workspace — the unified system of record for a single immigration case.

This service is an orchestrator. It owns lightweight CaseWorkspace records
that link together everything the platform builds about a case: the intake
session, uploaded documents, populated forms, attorney match, conflict
checks, RFE risk assessment, deadlines, timeline events, and notes.

The point: one fetch (`get_snapshot`) returns the entire state of a case
across services. The frontend doesn't fan-out to 8 endpoints to render a
case — it asks the workspace for a snapshot and gets everything.

Design choices:
  - Workspaces are *additive* to the existing employer-centric Case model;
    we don't refactor that.
  - All references are by ID (intake_session_id, form_record_ids, etc.);
    the workspace doesn't duplicate state.
  - Timeline events are first-class so attorneys can see filing dates,
    RFE deadlines, and decisions in chronological order.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

WORKSPACE_STATUSES = (
    "intake",          # collecting intake answers
    "documents",       # uploading docs
    "review",          # ready for attorney review
    "filed",           # petition filed
    "rfe",             # RFE pending response
    "decision_pending",
    "approved",
    "denied",
    "withdrawn",
)

TIMELINE_EVENT_KINDS = (
    "case_created",
    "intake_started",
    "intake_completed",
    "document_uploaded",
    "document_reconciled",
    "forms_populated",
    "attorney_assigned",
    "conflict_check_run",
    "rfe_risk_assessed",
    "case_filed",
    "rfe_received",
    "rfe_responded",
    "decision_received",
    "deadline_added",
    "note_added",
    "status_changed",
    "milestone_reached",
)


class CaseWorkspaceService:
    """Aggregator + system of record for case workspaces."""

    def __init__(
        self,
        intake_engine: Any = None,
        document_intake: Any = None,
        form_population: Any = None,
        attorney_match: Any = None,
        conflict_check: Any = None,
        rfe_predictor: Any = None,
    ) -> None:
        # Dependency injection so tests can pass mocks; production wires real services.
        self._intake = intake_engine
        self._docs = document_intake
        self._forms = form_population
        self._match = attorney_match
        self._conflict = conflict_check
        self._rfe = rfe_predictor
        self._workspaces: dict[str, dict] = {}
        self._timeline: dict[str, list[dict]] = {}
        self._notes: dict[str, list[dict]] = {}
        self._deadlines: dict[str, list[dict]] = {}

    # ---------- creation + linking ----------
    def create_workspace(
        self,
        applicant_id: str,
        visa_type: str,
        country: str,
        intake_session_id: str | None = None,
        attorney_id: str | None = None,
        case_label: str | None = None,
    ) -> dict:
        ws_id = str(uuid.uuid4())
        ws = {
            "id": ws_id,
            "applicant_id": applicant_id,
            "attorney_id": attorney_id,
            "visa_type": visa_type,
            "country": country,
            "status": "intake",
            "label": case_label or f"{visa_type} — {applicant_id[:6]}",
            "intake_session_id": intake_session_id,
            "form_record_ids": [],
            "attorney_match_id": None,
            "conflict_check_id": None,
            "rfe_assessment_id": None,
            "filing_receipt_number": None,
            "filed_date": None,
            "decision_date": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._workspaces[ws_id] = ws
        self._timeline[ws_id] = []
        self._notes[ws_id] = []
        self._deadlines[ws_id] = []
        self._add_event(ws_id, "case_created", f"Case workspace created for {visa_type}")
        if intake_session_id:
            self._add_event(ws_id, "intake_started", f"Intake session {intake_session_id[:8]}")
        return ws

    def get_workspace(self, ws_id: str) -> dict | None:
        return self._workspaces.get(ws_id)

    def list_workspaces(
        self,
        applicant_id: str | None = None,
        attorney_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        out = list(self._workspaces.values())
        if applicant_id:
            out = [w for w in out if w["applicant_id"] == applicant_id]
        if attorney_id:
            out = [w for w in out if w.get("attorney_id") == attorney_id]
        if status:
            out = [w for w in out if w["status"] == status]
        return out

    def update_status(self, ws_id: str, new_status: str, reason: str = "") -> dict:
        if new_status not in WORKSPACE_STATUSES:
            raise ValueError(f"Unknown status: {new_status}")
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")
        old = ws["status"]
        ws["status"] = new_status
        ws["updated_at"] = datetime.utcnow().isoformat()
        self._add_event(ws_id, "status_changed", f"{old} → {new_status}" + (f": {reason}" if reason else ""))
        return ws

    def assign_attorney(self, ws_id: str, attorney_id: str, attorney_name: str = "") -> dict:
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")
        ws["attorney_id"] = attorney_id
        ws["updated_at"] = datetime.utcnow().isoformat()
        self._add_event(ws_id, "attorney_assigned", f"Attorney {attorney_name or attorney_id} assigned")
        return ws

    def link_form_record(self, ws_id: str, form_record_id: str) -> dict:
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")
        if form_record_id not in ws["form_record_ids"]:
            ws["form_record_ids"].append(form_record_id)
            ws["updated_at"] = datetime.utcnow().isoformat()
        return ws

    def record_filing(self, ws_id: str, receipt_number: str, filed_date: str | None = None) -> dict:
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")
        ws["filing_receipt_number"] = receipt_number
        ws["filed_date"] = filed_date or date.today().isoformat()
        ws["status"] = "filed"
        ws["updated_at"] = datetime.utcnow().isoformat()
        self._add_event(ws_id, "case_filed", f"Filed: {receipt_number}")
        return ws

    # ---------- snapshot ----------
    def get_snapshot(self, ws_id: str) -> dict:
        """Aggregate every linked artifact into a single response.

        Calls each linked service if available; degrades gracefully if a
        service was not wired. Frontend renders the whole workspace from
        this single payload."""
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")

        snapshot: dict[str, Any] = {
            "workspace": ws,
            "intake": None,
            "documents": None,
            "forms": None,
            "match": None,
            "conflicts": None,
            "rfe_risk": None,
            "timeline": list(reversed(self._timeline.get(ws_id, []))),
            "notes": list(reversed(self._notes.get(ws_id, []))),
            "deadlines": sorted(self._deadlines.get(ws_id, []), key=lambda d: d.get("due_date", "")),
            "completeness": {},
            "next_actions": [],
            "computed_at": datetime.utcnow().isoformat(),
        }

        # Intake summary
        if self._intake and ws.get("intake_session_id"):
            try:
                snapshot["intake"] = self._intake.get_intake_summary(ws["intake_session_id"])
            except Exception:
                snapshot["intake"] = None

        # Documents reconciliation
        if self._docs and ws.get("intake_session_id") and self._intake:
            try:
                answers = self._intake.get_session(ws["intake_session_id"])["answers"]
                checklist = self._intake.get_document_checklist(ws["visa_type"], answers)
                snapshot["documents"] = self._docs.reconcile_against_checklist(
                    applicant_id=ws["applicant_id"],
                    session_id=ws["intake_session_id"],
                    checklist=checklist,
                    intake_answers=answers,
                )
            except Exception:
                snapshot["documents"] = None

        # Forms
        if self._forms and ws["form_record_ids"]:
            try:
                form_records = [self._forms.get_record(fid) for fid in ws["form_record_ids"]]
                form_records = [f for f in form_records if f is not None]
                if form_records:
                    total_req = sum(f["required_total"] for f in form_records)
                    total_filled = sum(f["required_filled"] for f in form_records)
                    snapshot["forms"] = {
                        "records": form_records,
                        "bundle_completeness_pct": round((total_filled / total_req) * 100) if total_req else 100,
                        "total_required_fields": total_req,
                        "total_filled_fields": total_filled,
                    }
            except Exception:
                snapshot["forms"] = None

        # Attorney match (re-run to keep fresh)
        if self._match and snapshot["intake"]:
            try:
                summary = dict(snapshot["intake"])
                summary["country"] = ws["country"]
                snapshot["match"] = self._match.match_for_session(
                    intake_summary=summary, applicant_languages=["English"], limit=3,
                )
            except Exception:
                snapshot["match"] = None

        # Conflicts (replay last result)
        if self._conflict:
            try:
                log = self._conflict.get_check_log(limit=200)
                related = [c for c in log if c.get("prospect", {}).get("applicant_name") and ws.get("applicant_id")]
                # Simple heuristic: include checks where the applicant_id is referenced via prospect; in production
                # we'd persist conflict_check_id on the workspace.
                if related:
                    snapshot["conflicts"] = related[-1]
            except Exception:
                snapshot["conflicts"] = None

        # RFE risk
        if self._rfe and snapshot["intake"]:
            try:
                answers = self._intake.get_session(ws["intake_session_id"])["answers"]
                snapshot["rfe_risk"] = self._rfe.predict(ws["visa_type"], self._build_rfe_profile(answers))
            except Exception:
                snapshot["rfe_risk"] = None

        # Roll-up completeness
        snapshot["completeness"] = self._compute_completeness(snapshot)
        snapshot["next_actions"] = self._compute_next_actions(snapshot, ws)
        return snapshot

    @staticmethod
    def _build_rfe_profile(answers: dict) -> dict:
        """Translate intake answers into the shape the RFE predictor expects."""
        out = dict(answers)
        # Map a handful of common signals
        if answers.get("third_party_placement") is None:
            out["third_party_placement"] = False
        return out

    @staticmethod
    def _compute_completeness(snapshot: dict) -> dict:
        intake_pct = 0
        if snapshot.get("intake"):
            v = snapshot["intake"].get("validation", {})
            intake_pct = 100 if v.get("ok") else 50
        docs_pct = (snapshot.get("documents") or {}).get("completeness_pct") or 0
        forms_pct = (snapshot.get("forms") or {}).get("bundle_completeness_pct") or 0
        overall = round((intake_pct * 0.3) + (docs_pct * 0.4) + (forms_pct * 0.3))
        return {
            "intake_pct": intake_pct,
            "documents_pct": docs_pct,
            "forms_pct": forms_pct,
            "overall_pct": overall,
            "ready_to_file": overall >= 95
                              and (snapshot.get("intake") or {}).get("ready_to_file") is True
                              and (snapshot.get("documents") or {}).get("ready_to_file") is True,
        }

    @staticmethod
    def _compute_next_actions(snapshot: dict, ws: dict) -> list[dict]:
        actions: list[dict] = []
        intake = snapshot.get("intake") or {}
        if intake and not intake.get("validation", {}).get("ok"):
            for b in (intake.get("validation") or {}).get("blocking_issues", [])[:3]:
                actions.append({"priority": "blocking", "label": b.get("issue", "Resolve eligibility blocker")})
        docs = snapshot.get("documents") or {}
        if docs and (docs.get("completeness_pct") or 0) < 100:
            missing = [i for i in docs.get("items", []) if i["status"] == "missing" and i["required"]]
            for m in missing[:3]:
                actions.append({"priority": "high", "label": f"Upload: {m['label']}"})
            for c in docs.get("data_conflicts", [])[:2]:
                actions.append({"priority": "high", "label": c.get("explanation", "Resolve document conflict")})
        forms = snapshot.get("forms") or {}
        if forms and (forms.get("bundle_completeness_pct") or 0) < 100:
            actions.append({"priority": "medium", "label": "Review and complete remaining form fields"})
        rfe = snapshot.get("rfe_risk") or {}
        if rfe and rfe.get("risk_score", 0) >= 50:
            for t in rfe.get("fired_triggers", [])[:2]:
                actions.append({"priority": "medium", "label": f"Mitigate RFE risk: {t['title']}"})
        if not actions and ws["status"] == "review":
            actions.append({"priority": "low", "label": "Schedule attorney review"})
        return actions

    # ---------- timeline ----------
    def add_timeline_event(self, ws_id: str, kind: str, message: str, metadata: dict | None = None) -> dict:
        if ws_id not in self._workspaces:
            raise ValueError(f"Workspace not found: {ws_id}")
        return self._add_event(ws_id, kind, message, metadata)

    def _add_event(self, ws_id: str, kind: str, message: str, metadata: dict | None = None) -> dict:
        evt = {
            "id": str(uuid.uuid4()),
            "kind": kind,
            "message": message,
            "metadata": metadata or {},
            "at": datetime.utcnow().isoformat(),
        }
        self._timeline.setdefault(ws_id, []).append(evt)
        return evt

    def get_timeline(self, ws_id: str) -> list[dict]:
        return list(reversed(self._timeline.get(ws_id, [])))

    # ---------- notes ----------
    def add_note(self, ws_id: str, author_id: str, body: str, visibility: str = "internal") -> dict:
        if ws_id not in self._workspaces:
            raise ValueError(f"Workspace not found: {ws_id}")
        note = {
            "id": str(uuid.uuid4()),
            "author_id": author_id,
            "body": body,
            "visibility": visibility,  # "internal" | "client_visible"
            "at": datetime.utcnow().isoformat(),
        }
        self._notes.setdefault(ws_id, []).append(note)
        self._add_event(ws_id, "note_added", f"Note added by {author_id}")
        return note

    def list_notes(self, ws_id: str, visibility: str | None = None) -> list[dict]:
        notes = self._notes.get(ws_id, [])
        if visibility:
            notes = [n for n in notes if n["visibility"] == visibility]
        return list(reversed(notes))

    # ---------- deadlines ----------
    def add_deadline(self, ws_id: str, label: str, due_date: str, kind: str = "general", source: str = "manual") -> dict:
        if ws_id not in self._workspaces:
            raise ValueError(f"Workspace not found: {ws_id}")
        d = {
            "id": str(uuid.uuid4()),
            "label": label,
            "due_date": due_date,
            "kind": kind,
            "source": source,
            "added_at": datetime.utcnow().isoformat(),
            "completed": False,
        }
        self._deadlines.setdefault(ws_id, []).append(d)
        self._add_event(ws_id, "deadline_added", f"{label} — due {due_date}")
        return d

    def list_deadlines(self, ws_id: str, include_completed: bool = False) -> list[dict]:
        ds = self._deadlines.get(ws_id, [])
        if not include_completed:
            ds = [d for d in ds if not d["completed"]]
        return sorted(ds, key=lambda d: d["due_date"])

    def complete_deadline(self, ws_id: str, deadline_id: str) -> dict | None:
        for d in self._deadlines.get(ws_id, []):
            if d["id"] == deadline_id:
                d["completed"] = True
                d["completed_at"] = datetime.utcnow().isoformat()
                return d
        return None

    def auto_compute_deadlines_from_filing(self, ws_id: str, receipt_date: str, form_type: str) -> list[dict]:
        """Generate standard downstream deadlines from a filing."""
        ws = self._workspaces.get(ws_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {ws_id}")
        try:
            base = date.fromisoformat(receipt_date)
        except (TypeError, ValueError):
            return []
        windows: dict[str, list[tuple[str, int]]] = {
            "I-129": [
                ("Premium processing decision window closes", 15),
                ("Standard processing window closes", 180),
            ],
            "I-130": [
                ("Standard processing window closes", 365),
            ],
            "I-485": [
                ("Biometrics expected", 60),
                ("Adjustment interview window opens", 180),
            ],
            "I-765": [
                ("EAD decision window closes", 90),
            ],
            "I-131": [
                ("Travel document decision window closes", 120),
            ],
        }
        deadlines = []
        for label, days in windows.get(form_type, []):
            due = (base + timedelta(days=days)).isoformat()
            deadlines.append(self.add_deadline(ws_id, f"{form_type}: {label}", due, kind="processing", source="auto"))
        return deadlines

    def add_rfe_response_deadline(self, ws_id: str, rfe_received_date: str, response_window_days: int = 87) -> dict:
        try:
            base = date.fromisoformat(rfe_received_date)
        except (TypeError, ValueError):
            base = date.today()
        due = (base + timedelta(days=response_window_days)).isoformat()
        d = self.add_deadline(ws_id, "RFE response due", due, kind="rfe", source="auto")
        self._add_event(ws_id, "rfe_received", f"RFE received {rfe_received_date}; response due {due}")
        return d
