"""Conflict-of-Interest Detection — bar-required ethics check for attorneys.

Cross-references new clients/cases against existing case database to identify:
  - Direct conflicts (same person on both sides)
  - Adverse parties (employer in beneficiary case is opposite party in another case)
  - Family/relationship conflicts
  - Imputed conflicts (firm-level)
  - Former-client conflicts (Model Rule 1.9)

Returns a structured conflict report with severity, basis, and recommended action."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


class ConflictCheckService:
    """Run conflict-of-interest checks before attorney accepts a new case."""

    def __init__(self) -> None:
        # In production this is backed by a database. In-memory store here for clarity.
        self._clients: list[dict] = []
        self._cases: list[dict] = []
        self._screens: dict[str, dict] = {}  # ethics walls
        self._check_log: list[dict] = []

    # ---------- registration ----------
    def register_client(self, client: dict) -> dict:
        """Register a client. Required: id, full_name, role (applicant/petitioner/employer),
        and optional date_of_birth, employer_name, attorney_id, firm_id, status."""
        client = {**client}
        client.setdefault("id", str(uuid.uuid4()))
        client.setdefault("registered_at", datetime.utcnow().isoformat())
        client.setdefault("status", "active")
        self._clients.append(client)
        return client

    def register_case(self, case: dict) -> dict:
        """Register a case. Required: id, client_id, attorney_id, firm_id (optional),
        applicant_name, petitioner_name (optional), employer_name (optional), case_type."""
        case = {**case}
        case.setdefault("id", str(uuid.uuid4()))
        case.setdefault("registered_at", datetime.utcnow().isoformat())
        case.setdefault("status", "active")
        self._cases.append(case)
        return case

    def list_clients(self, attorney_id: str | None = None, firm_id: str | None = None) -> list[dict]:
        clients = self._clients
        if attorney_id:
            clients = [c for c in clients if c.get("attorney_id") == attorney_id]
        if firm_id:
            clients = [c for c in clients if c.get("firm_id") == firm_id]
        return clients

    def list_cases(self, attorney_id: str | None = None, firm_id: str | None = None) -> list[dict]:
        cases = self._cases
        if attorney_id:
            cases = [c for c in cases if c.get("attorney_id") == attorney_id]
        if firm_id:
            cases = [c for c in cases if c.get("firm_id") == firm_id]
        return cases

    # ---------- core conflict check ----------
    def check_new_case(self, prospect: dict, attorney_id: str, firm_id: str | None = None) -> dict:
        """Check a prospective new case for conflicts.

        prospect should include:
          - applicant_name, applicant_dob (optional)
          - petitioner_name (optional)
          - employer_name (optional)
          - related_party_names: list[str] (optional — spouses, family, etc.)
        """
        conflicts: list[dict] = []
        prospect_norm = self._normalize_prospect(prospect)

        # 1) Direct conflict — same applicant in firm/attorney's existing cases
        for c in self._cases:
            if c.get("status") == "closed":
                continue
            if self._names_match(c.get("applicant_name"), prospect_norm["applicant_name"]):
                if c.get("attorney_id") == attorney_id:
                    conflicts.append(self._mk_conflict(
                        "DIRECT_DUPLICATE", "blocking",
                        f"Same applicant '{prospect_norm['applicant_name']}' already represented by you in case {c['id']}",
                        rule="Model Rule 1.7 — current client conflict",
                        existing_case_id=c["id"],
                    ))
                elif firm_id and c.get("firm_id") == firm_id:
                    conflicts.append(self._mk_conflict(
                        "FIRM_DUPLICATE", "high",
                        f"Same applicant already represented in firm by another attorney in case {c['id']}",
                        rule="Model Rule 1.10 — imputed conflicts",
                        existing_case_id=c["id"],
                    ))

        # 2) Adverse party — prospect's employer is an existing applicant in another case
        if prospect_norm.get("employer_name"):
            for c in self._cases:
                if c.get("status") == "closed":
                    continue
                if self._names_match(c.get("applicant_name"), prospect_norm["employer_name"]):
                    conflicts.append(self._mk_conflict(
                        "ADVERSE_PARTY",
                        "high" if c.get("attorney_id") == attorney_id else "medium",
                        f"Prospect's employer '{prospect_norm['employer_name']}' is an applicant in case {c['id']}",
                        rule="Model Rule 1.7 — adverse interests",
                        existing_case_id=c["id"],
                    ))

        # 3) Adverse party — prospect's name appears as employer/petitioner in another case
        for c in self._cases:
            if c.get("status") == "closed":
                continue
            for field in ("employer_name", "petitioner_name"):
                if c.get(field) and self._names_match(c.get(field), prospect_norm["applicant_name"]):
                    conflicts.append(self._mk_conflict(
                        "REVERSE_ADVERSE",
                        "medium",
                        f"Prospect's name appears as {field} in existing case {c['id']}",
                        rule="Model Rule 1.7",
                        existing_case_id=c["id"],
                    ))

        # 4) Related party — known spouse/family of an existing client (if disclosed)
        related = prospect_norm.get("related_party_names", [])
        for related_name in related:
            for c in self._cases:
                if c.get("status") == "closed":
                    continue
                if self._names_match(c.get("applicant_name"), related_name):
                    conflicts.append(self._mk_conflict(
                        "RELATED_PARTY",
                        "low",
                        f"Related party '{related_name}' is an existing client (case {c['id']})",
                        rule="Disclosable connection — confirm no adversity",
                        existing_case_id=c["id"],
                    ))

        # 5) Former-client conflict — Model Rule 1.9
        for c in self._cases:
            if c.get("status") != "closed":
                continue
            if self._names_match(c.get("applicant_name"), prospect_norm["applicant_name"]):
                conflicts.append(self._mk_conflict(
                    "FORMER_CLIENT",
                    "low",
                    f"Same person was a former client (case {c['id']})",
                    rule="Model Rule 1.9 — duties to former clients",
                    existing_case_id=c["id"],
                ))

        # Deduplicate by (code, existing_case_id)
        seen = set()
        unique_conflicts = []
        for cf in conflicts:
            key = (cf["code"], cf.get("existing_case_id"))
            if key in seen:
                continue
            seen.add(key)
            unique_conflicts.append(cf)

        # Decision
        any_blocking = any(c["severity"] == "blocking" for c in unique_conflicts)
        any_high = any(c["severity"] == "high" for c in unique_conflicts)
        decision = (
            "decline_unless_waived" if any_blocking else
            "review_required" if any_high else
            "proceed_with_disclosure" if unique_conflicts else
            "clear"
        )

        check_id = str(uuid.uuid4())
        result = {
            "check_id": check_id,
            "attorney_id": attorney_id,
            "firm_id": firm_id,
            "prospect": prospect_norm,
            "conflicts": unique_conflicts,
            "total_conflicts": len(unique_conflicts),
            "decision": decision,
            "checked_at": datetime.utcnow().isoformat(),
            "next_steps": self._next_steps(decision, unique_conflicts),
        }
        self._check_log.append(result)
        return result

    @staticmethod
    def _next_steps(decision: str, conflicts: list[dict]) -> list[str]:
        if decision == "decline_unless_waived":
            return [
                "Decline the engagement OR obtain informed written consent from all affected clients",
                "Document waiver and basis in the file",
                "Consider whether an ethics wall is sufficient to mitigate",
            ]
        if decision == "review_required":
            return [
                "Senior attorney / ethics partner review required before accepting",
                "Document analysis under Rule 1.7 / 1.10",
                "Consider ethics wall and informed consent",
            ]
        if decision == "proceed_with_disclosure":
            return [
                "Proceed but disclose connection to client",
                "Document the disclosure in writing",
            ]
        return ["Clear to proceed — document the negative conflict check in the file"]

    @staticmethod
    def _mk_conflict(code: str, severity: str, message: str, rule: str, existing_case_id: str | None = None) -> dict:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "rule": rule,
            "existing_case_id": existing_case_id,
        }

    @staticmethod
    def _normalize_prospect(prospect: dict) -> dict:
        return {
            "applicant_name": (prospect.get("applicant_name") or "").strip(),
            "applicant_dob": prospect.get("applicant_dob"),
            "petitioner_name": (prospect.get("petitioner_name") or "").strip() or None,
            "employer_name": (prospect.get("employer_name") or "").strip() or None,
            "related_party_names": [n.strip() for n in (prospect.get("related_party_names") or []) if n and n.strip()],
            "case_type": prospect.get("case_type"),
        }

    @staticmethod
    def _names_match(a: Any, b: Any) -> bool:
        if not a or not b:
            return False
        an = " ".join(str(a).strip().lower().split())
        bn = " ".join(str(b).strip().lower().split())
        if an == bn:
            return True
        # Soft match: surnames + first-name-initial collision
        a_parts = an.split()
        b_parts = bn.split()
        if len(a_parts) >= 2 and len(b_parts) >= 2:
            if a_parts[-1] == b_parts[-1] and a_parts[0][:1] == b_parts[0][:1]:
                return True
        return False

    # ---------- ethics walls ----------
    def create_ethics_wall(self, case_id: str, walled_off_user_ids: list[str], reason: str) -> dict:
        wall = {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "walled_off_user_ids": walled_off_user_ids,
            "reason": reason,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
        }
        self._screens[wall["id"]] = wall
        return wall

    def list_ethics_walls(self, case_id: str | None = None) -> list[dict]:
        walls = list(self._screens.values())
        if case_id:
            walls = [w for w in walls if w["case_id"] == case_id]
        return walls

    def deactivate_ethics_wall(self, wall_id: str) -> dict | None:
        wall = self._screens.get(wall_id)
        if wall:
            wall["active"] = False
            wall["deactivated_at"] = datetime.utcnow().isoformat()
        return wall

    # ---------- audit ----------
    def get_check_log(self, attorney_id: str | None = None, firm_id: str | None = None, limit: int = 100) -> list[dict]:
        log = self._check_log
        if attorney_id:
            log = [c for c in log if c["attorney_id"] == attorney_id]
        if firm_id:
            log = [c for c in log if c.get("firm_id") == firm_id]
        return log[-limit:]

    def get_audit_summary(self) -> dict:
        total = len(self._check_log)
        decisions: dict[str, int] = {}
        for c in self._check_log:
            decisions[c["decision"]] = decisions.get(c["decision"], 0) + 1
        return {
            "total_checks": total,
            "decisions_breakdown": decisions,
            "total_clients": len(self._clients),
            "total_cases": len(self._cases),
            "active_ethics_walls": sum(1 for w in self._screens.values() if w["active"]),
        }
