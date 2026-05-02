"""Bar Ethics Endorsement Registry — UPL safe harbor + bar-blessed credibility.

Tracks formal endorsements / no-action letters / advisory opinions from state
bar associations confirming the platform doesn't cross UPL (unauthorized
practice of law) lines. Each endorsement is the legal-team's gold for the
verified-attorney pipeline:
  - When an attorney from State X considers Verom, the endorsement reassures
    them their bar isn't going to come after them for using a tech platform.
  - When a state bar considers a complaint about the platform, the existing
    endorsements show the platform took the regulatory work seriously.
  - Marketing benefit: "Endorsed by N state bars" is a paid-search defensible
    claim.

Each endorsement carries:
  - Issuing bar (state, country, full name)
  - Endorsement type (no_action_letter / advisory_opinion / formal_approval / informal_blessing)
  - Issued-on date, expiry-on date
  - Scope (which platform features the bar reviewed)
  - Public document URL (the bar's letter)
  - Internal contact / liaison

Application tracker: when the legal team is pursuing an endorsement, the
service tracks where each application stands so legal can manage the pipeline.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


ENDORSEMENT_TYPES = (
    "no_action_letter",       # bar formally won't take action
    "advisory_opinion",       # bar issued an opinion blessing the model
    "formal_approval",        # explicit approval (rare)
    "informal_blessing",      # ethics counsel email or call notes
    "white_paper_response",   # bar published response to platform white paper
)

APPLICATION_STAGES = (
    "research",               # legal team scoping the requirement
    "drafting_application",   # writing the petition / submission
    "submitted",              # filed with the bar
    "under_review",           # bar is reviewing
    "follow_up",              # bar requested more information
    "granted",                # endorsement issued
    "denied",                 # bar declined to endorse
    "withdrawn",              # platform withdrew the application
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class BarEndorsementService:
    """Track formal bar endorsements + the application pipeline."""

    def __init__(self) -> None:
        self._endorsements: dict[str, dict] = {}
        self._applications: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_endorsement_types() -> list[str]:
        return list(ENDORSEMENT_TYPES)

    @staticmethod
    def list_application_stages() -> list[str]:
        return list(APPLICATION_STAGES)

    # ---------- record an endorsement ----------
    def record_endorsement(
        self,
        bar_jurisdiction: str,
        bar_full_name: str,
        endorsement_type: str,
        issued_date: str,
        scope: list[str],
        public_url: str = "",
        expires_date: str | None = None,
        internal_contact: dict | None = None,
        notes: str = "",
    ) -> dict:
        if endorsement_type not in ENDORSEMENT_TYPES:
            raise ValueError(f"Unknown endorsement type: {endorsement_type}")
        if not scope:
            raise ValueError("Scope is required (which features did the bar review?)")
        try:
            datetime.fromisoformat(issued_date)
        except ValueError as e:
            raise ValueError("issued_date must be ISO format (YYYY-MM-DD)") from e
        if expires_date:
            try:
                datetime.fromisoformat(expires_date)
            except ValueError as e:
                raise ValueError("expires_date must be ISO format (YYYY-MM-DD)") from e
        record = {
            "id": str(uuid.uuid4()),
            "bar_jurisdiction": bar_jurisdiction.upper(),
            "bar_full_name": bar_full_name,
            "endorsement_type": endorsement_type,
            "issued_date": issued_date,
            "expires_date": expires_date,
            "scope": list(scope),
            "public_url": public_url,
            "internal_contact": internal_contact or {},
            "notes": notes,
            "active": True,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        self._endorsements[record["id"]] = record
        return record

    def revoke_endorsement(self, endorsement_id: str, reason: str = "") -> dict:
        record = self._endorsements.get(endorsement_id)
        if record is None:
            raise ValueError("Endorsement not found")
        record["active"] = False
        record["revoked_at"] = datetime.utcnow().isoformat()
        record["revocation_reason"] = reason
        return record

    def list_endorsements(
        self,
        bar_jurisdiction: str | None = None,
        endorsement_type: str | None = None,
        active_only: bool = True,
        scope: str | None = None,
    ) -> list[dict]:
        out = list(self._endorsements.values())
        if bar_jurisdiction:
            out = [e for e in out if e["bar_jurisdiction"] == bar_jurisdiction.upper()]
        if endorsement_type:
            out = [e for e in out if e["endorsement_type"] == endorsement_type]
        if active_only:
            today = date.today().isoformat()
            out = [
                e for e in out
                if e["active"] and (not e.get("expires_date") or e["expires_date"] >= today)
            ]
        if scope:
            out = [e for e in out if scope in e["scope"]]
        return out

    def get_endorsement(self, endorsement_id: str) -> dict | None:
        return self._endorsements.get(endorsement_id)

    def is_attorney_safe_harbor_covered(
        self, bar_jurisdiction: str, scope: str | None = None,
    ) -> dict:
        """Return whether an attorney from the given bar has UPL safe-harbor
        coverage from a recorded endorsement for the requested scope."""
        endorsements = self.list_endorsements(
            bar_jurisdiction=bar_jurisdiction, scope=scope, active_only=True,
        )
        if not endorsements:
            return {
                "bar_jurisdiction": bar_jurisdiction,
                "scope": scope,
                "covered": False,
                "endorsements": [],
            }
        return {
            "bar_jurisdiction": bar_jurisdiction,
            "scope": scope,
            "covered": True,
            "endorsements": endorsements,
            "strongest_type": _strongest_type([e["endorsement_type"] for e in endorsements]),
        }

    # ---------- application pipeline ----------
    def open_application(
        self,
        bar_jurisdiction: str,
        bar_full_name: str,
        endorsement_type_target: str,
        scope_target: list[str],
        owner_user_id: str | None = None,
    ) -> dict:
        if endorsement_type_target not in ENDORSEMENT_TYPES:
            raise ValueError(f"Unknown endorsement type: {endorsement_type_target}")
        record = {
            "id": str(uuid.uuid4()),
            "bar_jurisdiction": bar_jurisdiction.upper(),
            "bar_full_name": bar_full_name,
            "endorsement_type_target": endorsement_type_target,
            "scope_target": list(scope_target),
            "owner_user_id": owner_user_id,
            "stage": "research",
            "stage_history": [{"stage": "research", "at": datetime.utcnow().isoformat()}],
            "documents": [],
            "communications": [],
            "opened_at": datetime.utcnow().isoformat(),
        }
        self._applications[record["id"]] = record
        return record

    def transition_stage(self, application_id: str, new_stage: str, note: str = "") -> dict:
        if new_stage not in APPLICATION_STAGES:
            raise ValueError(f"Unknown stage: {new_stage}")
        app = self._applications.get(application_id)
        if app is None:
            raise ValueError("Application not found")
        old = app["stage"]
        app["stage"] = new_stage
        app["stage_history"].append({
            "stage": new_stage, "at": datetime.utcnow().isoformat(), "note": note,
        })
        if new_stage == "granted":
            # Auto-create the endorsement record
            ep = self.record_endorsement(
                bar_jurisdiction=app["bar_jurisdiction"],
                bar_full_name=app["bar_full_name"],
                endorsement_type=app["endorsement_type_target"],
                issued_date=date.today().isoformat(),
                scope=app["scope_target"],
                notes=f"Auto-recorded from application {application_id}",
            )
            app["resulting_endorsement_id"] = ep["id"]
        return app

    def attach_application_document(
        self, application_id: str, doc_label: str, doc_url: str = "", notes: str = "",
    ) -> dict:
        app = self._applications.get(application_id)
        if app is None:
            raise ValueError("Application not found")
        attachment = {
            "id": str(uuid.uuid4()),
            "label": doc_label, "url": doc_url, "notes": notes,
            "attached_at": datetime.utcnow().isoformat(),
        }
        app["documents"].append(attachment)
        return attachment

    def log_application_communication(
        self, application_id: str, kind: str, body: str,
        actor_user_id: str | None = None,
    ) -> dict:
        app = self._applications.get(application_id)
        if app is None:
            raise ValueError("Application not found")
        comm = {
            "id": str(uuid.uuid4()),
            "kind": kind, "body": body,
            "actor_user_id": actor_user_id,
            "at": datetime.utcnow().isoformat(),
        }
        app["communications"].append(comm)
        return comm

    def list_applications(
        self, stage: str | None = None,
        bar_jurisdiction: str | None = None,
    ) -> list[dict]:
        out = list(self._applications.values())
        if stage:
            out = [a for a in out if a["stage"] == stage]
        if bar_jurisdiction:
            out = [a for a in out if a["bar_jurisdiction"] == bar_jurisdiction.upper()]
        return sorted(out, key=lambda a: a["opened_at"], reverse=True)

    def get_application(self, application_id: str) -> dict | None:
        return self._applications.get(application_id)

    # ---------- coverage matrix ----------
    def coverage_matrix(self) -> dict:
        """Return a coverage map: which jurisdictions have which endorsement types."""
        matrix: dict[str, list[str]] = {}
        for e in self.list_endorsements(active_only=True):
            matrix.setdefault(e["bar_jurisdiction"], []).append(e["endorsement_type"])
        return {
            "covered_jurisdictions": list(matrix.keys()),
            "by_jurisdiction": matrix,
            "total_active_endorsements": sum(len(v) for v in matrix.values()),
            "computed_at": datetime.utcnow().isoformat(),
        }


def _strongest_type(types: list[str]) -> str:
    rank = {t: i for i, t in enumerate(ENDORSEMENT_TYPES)}
    # ENDORSEMENT_TYPES is ordered roughly weakest-last; reverse for "strongest"
    # Actually order is: no_action_letter > advisory_opinion > formal_approval
    #   > informal_blessing > white_paper_response (intent: formal_approval is best)
    # Treat formal_approval as strongest, then advisory, no_action, white_paper, informal
    strength = {
        "formal_approval": 5,
        "advisory_opinion": 4,
        "no_action_letter": 3,
        "white_paper_response": 2,
        "informal_blessing": 1,
    }
    return max(types, key=lambda t: strength.get(t, 0))
