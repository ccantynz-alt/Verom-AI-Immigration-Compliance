"""Team Management + Role-Based Access Control.

Firm-level multi-user organization with permission-aware case visibility.
The mechanism that makes Verom usable by mid-market and enterprise law
firms (where the existing employer-managed Case model isn't enough).

Concepts:
  - Firm           — top-level organization (single state bar)
  - Member         — user belonging to a firm with a role
  - Role           — bundles permissions; either built-in (admin, partner,
                     attorney, paralegal, legal_assistant, observer) or
                     custom (firm-defined)
  - Office         — physical office / location for multi-office firms
  - Permission     — capability string (e.g. "case.view", "case.assign",
                     "billing.view", "trust.post_transaction")
  - Task           — assignable unit of work with priority + deadline
  - Workload       — per-member case + task load aggregation

Role permission grants (built-ins):
  admin            — everything (firm + system management)
  partner          — case visibility firm-wide + delete + reassign
  attorney         — own cases + assigned cases + billing for own cases
  paralegal        — assigned cases (read/update), no delete
  legal_assistant  — task queue + document upload only
  observer         — read-only on assigned cases (auditor / consultant)

Permission checking:
  has_permission(member_id, permission) — single permission check
  filter_visible_cases(member_id, all_cases) — returns cases the member
      can see based on assignment + role
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Built-in roles + permissions
# ---------------------------------------------------------------------------

ALL_PERMISSIONS = (
    # Case
    "case.view", "case.create", "case.update", "case.delete", "case.assign",
    "case.view_all", "case.update_all",
    # Document
    "document.view", "document.upload", "document.delete",
    # Forms
    "form.view", "form.populate", "form.update", "form.submit",
    # Billing / time / trust
    "time.log", "time.view", "time.view_all",
    "billing.view", "billing.create_invoice", "billing.view_all",
    "trust.view", "trust.post_transaction", "trust.reconcile",
    # Communication
    "chatbot.respond", "message.send",
    # Filing
    "efiling.submit", "efiling.view",
    # Drafting
    "drafting.petition_letter", "drafting.rfe_response", "drafting.support_letter",
    # Conflict + ethics
    "conflict.check", "conflict.manage_walls",
    # Firm admin
    "firm.manage_members", "firm.manage_roles", "firm.manage_offices",
    "firm.view_audit_log",
    # Tasks
    "task.create", "task.assign", "task.update_own", "task.update_all",
)

BUILTIN_ROLES: dict[str, dict[str, Any]] = {
    "admin": {
        "label": "Firm Administrator",
        "permissions": list(ALL_PERMISSIONS),
        "case_visibility": "all",
    },
    "partner": {
        "label": "Partner",
        "permissions": [p for p in ALL_PERMISSIONS if p not in (
            "firm.manage_members", "firm.manage_roles",
        )],
        "case_visibility": "all",
    },
    "attorney": {
        "label": "Attorney",
        "permissions": [
            "case.view", "case.create", "case.update", "case.assign",
            "document.view", "document.upload",
            "form.view", "form.populate", "form.update", "form.submit",
            "time.log", "time.view", "billing.view", "billing.create_invoice",
            "trust.view", "trust.post_transaction",
            "chatbot.respond", "message.send",
            "efiling.submit", "efiling.view",
            "drafting.petition_letter", "drafting.rfe_response", "drafting.support_letter",
            "conflict.check",
            "task.create", "task.assign", "task.update_own",
        ],
        "case_visibility": "assigned",
    },
    "paralegal": {
        "label": "Paralegal",
        "permissions": [
            "case.view", "case.update",
            "document.view", "document.upload",
            "form.view", "form.populate", "form.update",
            "time.log", "time.view",
            "message.send",
            "task.update_own",
        ],
        "case_visibility": "assigned",
    },
    "legal_assistant": {
        "label": "Legal Assistant",
        "permissions": [
            "case.view",
            "document.view", "document.upload",
            "form.view",
            "task.update_own",
        ],
        "case_visibility": "assigned",
    },
    "observer": {
        "label": "Observer",
        "permissions": [
            "case.view",
            "document.view",
            "form.view",
            "billing.view",
            "trust.view",
            "task.update_own",
        ],
        "case_visibility": "assigned",
    },
}

VISIBILITY_KINDS = ("all", "assigned", "own")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TeamManagementService:
    """Firm + member management with RBAC."""

    def __init__(self, case_workspace: Any | None = None) -> None:
        self._cases = case_workspace
        self._firms: dict[str, dict] = {}
        self._members: dict[str, dict] = {}              # member_id → record
        self._members_by_user: dict[str, str] = {}       # user_id → member_id (latest active)
        self._custom_roles: dict[str, dict] = {}         # firm_id::role_id → record
        self._offices: dict[str, dict] = {}
        self._tasks: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_builtin_roles() -> list[dict]:
        return [
            {
                "id": k, "label": v["label"],
                "permissions": v["permissions"],
                "case_visibility": v["case_visibility"],
                "permission_count": len(v["permissions"]),
            }
            for k, v in BUILTIN_ROLES.items()
        ]

    @staticmethod
    def list_all_permissions() -> list[str]:
        return list(ALL_PERMISSIONS)

    # ---------- firms ----------
    def register_firm(
        self, name: str, primary_state: str, primary_attorney_user_id: str,
        bar_number: str | None = None, **kwargs: Any,
    ) -> dict:
        firm_id = str(uuid.uuid4())
        record = {
            "id": firm_id, "name": name,
            "primary_state": primary_state,
            "primary_attorney_user_id": primary_attorney_user_id,
            "bar_number": bar_number,
            "registered_at": datetime.utcnow().isoformat(),
            "active": True,
            **kwargs,
        }
        self._firms[firm_id] = record
        # Auto-create the founding member as admin
        self.add_member(firm_id, primary_attorney_user_id, role="admin", display_name=name + " Admin")
        return record

    def get_firm(self, firm_id: str) -> dict | None:
        return self._firms.get(firm_id)

    def list_firms(self, active_only: bool = True) -> list[dict]:
        out = list(self._firms.values())
        if active_only:
            out = [f for f in out if f.get("active")]
        return out

    # ---------- members ----------
    def add_member(
        self, firm_id: str, user_id: str, role: str = "attorney",
        display_name: str = "", office_id: str | None = None,
    ) -> dict:
        if firm_id not in self._firms:
            raise ValueError(f"Firm not found: {firm_id}")
        # Validate role
        if role not in BUILTIN_ROLES and not self._get_custom_role(firm_id, role):
            raise ValueError(f"Unknown role: {role}")
        member_id = str(uuid.uuid4())
        record = {
            "id": member_id,
            "firm_id": firm_id,
            "user_id": user_id,
            "role": role,
            "display_name": display_name,
            "office_id": office_id,
            "active": True,
            "joined_at": datetime.utcnow().isoformat(),
        }
        self._members[member_id] = record
        self._members_by_user[user_id] = member_id
        return record

    def get_member(self, member_id: str) -> dict | None:
        return self._members.get(member_id)

    def get_member_for_user(self, user_id: str) -> dict | None:
        member_id = self._members_by_user.get(user_id)
        return self._members.get(member_id) if member_id else None

    def list_members(self, firm_id: str | None = None, role: str | None = None, active_only: bool = True) -> list[dict]:
        out = list(self._members.values())
        if firm_id:
            out = [m for m in out if m["firm_id"] == firm_id]
        if role:
            out = [m for m in out if m["role"] == role]
        if active_only:
            out = [m for m in out if m["active"]]
        return out

    def update_member_role(self, member_id: str, new_role: str) -> dict:
        member = self._members.get(member_id)
        if member is None:
            raise ValueError("Member not found")
        if new_role not in BUILTIN_ROLES and not self._get_custom_role(member["firm_id"], new_role):
            raise ValueError(f"Unknown role: {new_role}")
        member["role"] = new_role
        member["role_updated_at"] = datetime.utcnow().isoformat()
        return member

    def deactivate_member(self, member_id: str, reason: str = "") -> dict:
        member = self._members.get(member_id)
        if member is None:
            raise ValueError("Member not found")
        member["active"] = False
        member["deactivated_at"] = datetime.utcnow().isoformat()
        member["deactivation_reason"] = reason
        # Clear user→member shortcut if it pointed here
        if self._members_by_user.get(member["user_id"]) == member_id:
            self._members_by_user.pop(member["user_id"], None)
        return member

    # ---------- custom roles ----------
    def create_custom_role(
        self, firm_id: str, role_id: str, label: str,
        permissions: list[str], case_visibility: str = "assigned",
    ) -> dict:
        if firm_id not in self._firms:
            raise ValueError("Firm not found")
        if case_visibility not in VISIBILITY_KINDS:
            raise ValueError(f"Unknown case visibility: {case_visibility}")
        for p in permissions:
            if p not in ALL_PERMISSIONS:
                raise ValueError(f"Unknown permission: {p}")
        if role_id in BUILTIN_ROLES:
            raise ValueError(f"Cannot override built-in role: {role_id}")
        key = f"{firm_id}::{role_id}"
        record = {
            "id": role_id, "firm_id": firm_id, "label": label,
            "permissions": permissions, "case_visibility": case_visibility,
            "created_at": datetime.utcnow().isoformat(), "is_custom": True,
        }
        self._custom_roles[key] = record
        return record

    def list_roles_for_firm(self, firm_id: str) -> list[dict]:
        out = list(BUILTIN_ROLES.items())
        result = [
            {"id": k, "label": v["label"], "permissions": v["permissions"],
             "case_visibility": v["case_visibility"], "is_custom": False}
            for k, v in out
        ]
        for key, role in self._custom_roles.items():
            if role["firm_id"] == firm_id:
                result.append(role)
        return result

    def _get_custom_role(self, firm_id: str, role_id: str) -> dict | None:
        return self._custom_roles.get(f"{firm_id}::{role_id}")

    def _resolve_role_permissions(self, firm_id: str, role_id: str) -> tuple[list[str], str]:
        if role_id in BUILTIN_ROLES:
            spec = BUILTIN_ROLES[role_id]
            return spec["permissions"], spec["case_visibility"]
        custom = self._get_custom_role(firm_id, role_id)
        if custom:
            return custom["permissions"], custom["case_visibility"]
        return [], "assigned"

    # ---------- permission checks ----------
    def has_permission(self, user_id: str, permission: str) -> bool:
        member = self.get_member_for_user(user_id)
        if member is None or not member["active"]:
            return False
        perms, _ = self._resolve_role_permissions(member["firm_id"], member["role"])
        return permission in perms

    def get_user_permissions(self, user_id: str) -> list[str]:
        member = self.get_member_for_user(user_id)
        if member is None or not member["active"]:
            return []
        perms, _ = self._resolve_role_permissions(member["firm_id"], member["role"])
        return list(perms)

    def filter_visible_cases(self, user_id: str, cases: list[dict]) -> list[dict]:
        member = self.get_member_for_user(user_id)
        if member is None:
            return [c for c in cases if c.get("applicant_id") == user_id]
        _, visibility = self._resolve_role_permissions(member["firm_id"], member["role"])
        if visibility == "all":
            # Firm-wide visibility — only this firm's cases
            return [c for c in cases if c.get("firm_id") == member["firm_id"] or c.get("attorney_id") == user_id]
        if visibility == "assigned":
            return [c for c in cases if c.get("attorney_id") == user_id]
        # "own" — applicant view
        return [c for c in cases if c.get("applicant_id") == user_id]

    # ---------- offices ----------
    def add_office(self, firm_id: str, name: str, address: str = "", state: str = "") -> dict:
        if firm_id not in self._firms:
            raise ValueError("Firm not found")
        office_id = str(uuid.uuid4())
        record = {
            "id": office_id, "firm_id": firm_id,
            "name": name, "address": address, "state": state,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
        }
        self._offices[office_id] = record
        return record

    def list_offices(self, firm_id: str | None = None) -> list[dict]:
        out = list(self._offices.values())
        if firm_id:
            out = [o for o in out if o["firm_id"] == firm_id]
        return out

    # ---------- tasks ----------
    def create_task(
        self, firm_id: str, title: str,
        assigned_to_member_id: str | None = None,
        workspace_id: str | None = None,
        priority: str = "normal",
        due_date: str | None = None,
        description: str = "",
        created_by_user_id: str | None = None,
    ) -> dict:
        if firm_id not in self._firms:
            raise ValueError("Firm not found")
        if priority not in ("low", "normal", "high", "urgent"):
            raise ValueError("Invalid priority")
        task_id = str(uuid.uuid4())
        record = {
            "id": task_id, "firm_id": firm_id, "title": title,
            "description": description,
            "assigned_to_member_id": assigned_to_member_id,
            "workspace_id": workspace_id,
            "priority": priority, "due_date": due_date,
            "created_by_user_id": created_by_user_id,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }
        self._tasks[task_id] = record
        return record

    def update_task(
        self, task_id: str,
        status: str | None = None,
        assigned_to_member_id: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        description: str | None = None,
        title: str | None = None,
    ) -> dict:
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError("Task not found")
        if status is not None:
            if status not in ("open", "in_progress", "completed", "blocked", "cancelled"):
                raise ValueError("Invalid status")
            task["status"] = status
            if status == "completed":
                task["completed_at"] = datetime.utcnow().isoformat()
        if assigned_to_member_id is not None:
            task["assigned_to_member_id"] = assigned_to_member_id
        if priority is not None:
            task["priority"] = priority
        if due_date is not None:
            task["due_date"] = due_date
        if description is not None:
            task["description"] = description
        if title is not None:
            task["title"] = title
        task["updated_at"] = datetime.utcnow().isoformat()
        return task

    def list_tasks(
        self, firm_id: str | None = None,
        assigned_to_member_id: str | None = None,
        workspace_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        out = list(self._tasks.values())
        if firm_id:
            out = [t for t in out if t["firm_id"] == firm_id]
        if assigned_to_member_id:
            out = [t for t in out if t.get("assigned_to_member_id") == assigned_to_member_id]
        if workspace_id:
            out = [t for t in out if t.get("workspace_id") == workspace_id]
        if status:
            out = [t for t in out if t["status"] == status]
        return out

    # ---------- workload aggregation ----------
    def get_workload_for_member(self, member_id: str) -> dict:
        member = self._members.get(member_id)
        if member is None:
            raise ValueError("Member not found")
        # Tasks assigned
        tasks = self.list_tasks(assigned_to_member_id=member_id)
        open_tasks = [t for t in tasks if t["status"] in ("open", "in_progress")]
        urgent_tasks = [t for t in open_tasks if t["priority"] in ("high", "urgent")]
        # Active workspaces (if case service is wired)
        active_cases = []
        if self._cases:
            try:
                active_cases = [
                    w for w in self._cases.list_workspaces(attorney_id=member["user_id"])
                    if w.get("status") not in ("approved", "denied", "withdrawn")
                ]
            except Exception:
                active_cases = []
        return {
            "member_id": member_id,
            "user_id": member["user_id"],
            "display_name": member.get("display_name"),
            "role": member["role"],
            "active_cases": len(active_cases),
            "open_tasks": len(open_tasks),
            "urgent_tasks": len(urgent_tasks),
            "computed_at": datetime.utcnow().isoformat(),
        }

    def get_firm_workload(self, firm_id: str) -> dict:
        members = self.list_members(firm_id=firm_id)
        loads = [self.get_workload_for_member(m["id"]) for m in members]
        return {
            "firm_id": firm_id,
            "member_count": len(members),
            "loads": loads,
            "computed_at": datetime.utcnow().isoformat(),
        }
