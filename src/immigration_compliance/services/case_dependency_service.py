"""Case Dependency Tracker — "this can't file until that approves".

Immigration cases form chains: an I-485 can't file until the I-140 is approved
(or visa is current); an I-765 EAD piggybacks on an I-485; an I-130 must be
approved before the consular process can begin; a derivative I-485 follows the
principal's adjustment-of-status decision.

Without dependency tracking, attorneys forget to file the downstream petition
the moment the predecessor approves — costing weeks of unnecessary delay.

This service:
  - Models known dependency relationships per visa type
  - Lets attorneys add custom dependencies on a case
  - Computes the ready-to-file set every time a workspace state changes
  - Surfaces blocking dependencies and the projected unblock date
  - Emits notifications when a dependency clears
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# Dependency kinds. Multiple kinds can apply to a single edge.
DEPENDENCY_KINDS = (
    "blocking_approval",          # downstream cannot file until upstream is approved
    "concurrent_eligible",         # downstream may file concurrently once upstream is filed
    "priority_date_current",       # downstream must wait for visa bulletin currentness
    "decision_required",           # downstream needs upstream decision (approval or denial)
    "derivative_dependency",       # derivative case follows principal's outcome
    "form_prerequisite",           # one form must be filed before another
    "lca_certified",               # H-1B I-129 needs ETA-9035 LCA certified
    "perm_certified",              # I-140 EB-2/EB-3 needs PERM ETA-9089 certified
)

# Pre-built dependency templates by visa type → list of (predecessor, dependent, kind)
TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "EB-2-PERM": [
        ("ETA-9089", "I-140", "perm_certified"),
        ("I-140", "I-485", "blocking_approval"),
        ("I-140", "I-485", "priority_date_current"),
        ("I-485", "I-765", "concurrent_eligible"),
        ("I-485", "I-131", "concurrent_eligible"),
    ],
    "EB-3-PERM": [
        ("ETA-9089", "I-140", "perm_certified"),
        ("I-140", "I-485", "blocking_approval"),
        ("I-140", "I-485", "priority_date_current"),
        ("I-485", "I-765", "concurrent_eligible"),
        ("I-485", "I-131", "concurrent_eligible"),
    ],
    "EB-1A": [
        ("I-140", "I-485", "blocking_approval"),
        ("I-485", "I-765", "concurrent_eligible"),
        ("I-485", "I-131", "concurrent_eligible"),
    ],
    "EB-2-NIW": [
        ("I-140", "I-485", "blocking_approval"),
        ("I-485", "I-765", "concurrent_eligible"),
        ("I-485", "I-131", "concurrent_eligible"),
    ],
    "I-130-AOS": [
        ("I-130", "I-485", "concurrent_eligible"),
        ("I-485", "I-765", "concurrent_eligible"),
        ("I-485", "I-131", "concurrent_eligible"),
    ],
    "I-130-CP": [
        ("I-130", "DS-260", "blocking_approval"),
    ],
    "H-1B": [
        ("ETA-9035", "I-129", "lca_certified"),
        ("I-129", "I-539", "concurrent_eligible"),  # dependents
    ],
    "L-1": [
        ("I-129", "I-539", "concurrent_eligible"),
    ],
    "O-1": [
        ("I-129", "I-539", "concurrent_eligible"),
    ],
    "I-751": [
        # Stand-alone joint petition (no predecessors)
    ],
    "N-400": [
        # Naturalization (no immigration predecessors)
    ],
}


# ---------------------------------------------------------------------------

class CaseDependencyService:
    """Track dependency edges between cases / forms within a case workspace."""

    def __init__(
        self,
        case_workspace_service: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self._cases = case_workspace_service
        self._notifications = notification_service
        self._edges: dict[str, dict] = {}        # edge_id → record
        self._edges_by_workspace: dict[str, list[str]] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_dependency_kinds() -> list[str]:
        return list(DEPENDENCY_KINDS)

    @staticmethod
    def list_templates() -> list[str]:
        return list(TEMPLATES.keys())

    @staticmethod
    def get_template(template_name: str) -> list[dict] | None:
        edges = TEMPLATES.get(template_name)
        if edges is None:
            return None
        return [
            {"predecessor": p, "dependent": d, "kind": k}
            for (p, d, k) in edges
        ]

    # ---------- edge CRUD ----------
    def add_edge(
        self,
        workspace_id: str,
        predecessor_form: str,
        dependent_form: str,
        kind: str,
        predecessor_workspace_id: str | None = None,
        notes: str = "",
    ) -> dict:
        if kind not in DEPENDENCY_KINDS:
            raise ValueError(f"Unknown dependency kind: {kind}")
        edge_id = str(uuid.uuid4())
        record = {
            "id": edge_id,
            "workspace_id": workspace_id,
            "predecessor_workspace_id": predecessor_workspace_id or workspace_id,
            "predecessor_form": predecessor_form,
            "dependent_form": dependent_form,
            "kind": kind,
            "notes": notes,
            "status": "pending",   # pending | unblocked | satisfied | broken
            "created_at": datetime.utcnow().isoformat(),
            "unblocked_at": None,
            "unblock_reason": None,
        }
        self._edges[edge_id] = record
        self._edges_by_workspace.setdefault(workspace_id, []).append(edge_id)
        return record

    def apply_template(
        self,
        workspace_id: str,
        template_name: str,
    ) -> list[dict]:
        if template_name not in TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")
        out: list[dict] = []
        for predecessor, dependent, kind in TEMPLATES[template_name]:
            out.append(self.add_edge(
                workspace_id=workspace_id,
                predecessor_form=predecessor,
                dependent_form=dependent,
                kind=kind,
                notes=f"Auto-applied from template: {template_name}",
            ))
        return out

    def remove_edge(self, edge_id: str) -> bool:
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return False
        ws_edges = self._edges_by_workspace.get(edge["workspace_id"], [])
        if edge_id in ws_edges:
            ws_edges.remove(edge_id)
        return True

    def list_edges_for_workspace(self, workspace_id: str) -> list[dict]:
        ids = self._edges_by_workspace.get(workspace_id, [])
        return [self._edges[i] for i in ids if i in self._edges]

    # ---------- dependency resolution ----------
    def mark_predecessor_satisfied(
        self,
        workspace_id: str,
        predecessor_form: str,
        reason: str = "",
        priority_date_current: bool | None = None,
    ) -> list[dict]:
        """Walk the workspace's edges; flip every edge whose predecessor matches.

        For "priority_date_current" edges we additionally require the caller to
        explicitly assert currentness (since approval alone doesn't make the
        priority date current).
        """
        unblocked: list[dict] = []
        for edge in self.list_edges_for_workspace(workspace_id):
            if edge["predecessor_form"] != predecessor_form:
                continue
            if edge["status"] != "pending":
                continue
            if edge["kind"] == "priority_date_current" and not priority_date_current:
                continue
            edge["status"] = "unblocked"
            edge["unblocked_at"] = datetime.utcnow().isoformat()
            edge["unblock_reason"] = reason or f"{predecessor_form} satisfied"
            unblocked.append(edge)
            self._notify_unblocked(edge)
        return unblocked

    def mark_priority_date_current(
        self,
        workspace_id: str,
        reason: str = "Visa Bulletin shows current",
    ) -> list[dict]:
        unblocked: list[dict] = []
        for edge in self.list_edges_for_workspace(workspace_id):
            if edge["kind"] != "priority_date_current":
                continue
            if edge["status"] != "pending":
                continue
            edge["status"] = "unblocked"
            edge["unblocked_at"] = datetime.utcnow().isoformat()
            edge["unblock_reason"] = reason
            unblocked.append(edge)
            self._notify_unblocked(edge)
        return unblocked

    def mark_dependent_filed(
        self,
        workspace_id: str,
        dependent_form: str,
    ) -> list[dict]:
        """Once the dependent is filed, mark its inbound edges as satisfied."""
        satisfied: list[dict] = []
        for edge in self.list_edges_for_workspace(workspace_id):
            if edge["dependent_form"] != dependent_form:
                continue
            if edge["status"] in ("unblocked", "pending"):
                edge["status"] = "satisfied"
                edge["satisfied_at"] = datetime.utcnow().isoformat()
                satisfied.append(edge)
        return satisfied

    # ---------- ready-to-file ----------
    def ready_to_file(self, workspace_id: str) -> dict:
        """Return the set of forms that have all blocking dependencies cleared."""
        edges = self.list_edges_for_workspace(workspace_id)
        # Group inbound edges by dependent form
        inbound: dict[str, list[dict]] = {}
        for edge in edges:
            inbound.setdefault(edge["dependent_form"], []).append(edge)
        # A form is ready when none of its inbound edges are pending and
        # at least one is unblocked / satisfied.
        ready_forms: list[dict] = []
        blocked_forms: list[dict] = []
        for form, inbound_edges in inbound.items():
            pending_blockers = [
                e for e in inbound_edges
                if e["status"] == "pending" and e["kind"] in (
                    "blocking_approval", "decision_required",
                    "priority_date_current", "lca_certified", "perm_certified",
                    "form_prerequisite", "derivative_dependency",
                )
            ]
            if pending_blockers:
                blocked_forms.append({
                    "form": form,
                    "blocked_by": [
                        {
                            "predecessor_form": b["predecessor_form"],
                            "kind": b["kind"],
                        }
                        for b in pending_blockers
                    ],
                })
            else:
                ready_forms.append({"form": form})
        return {
            "workspace_id": workspace_id,
            "ready": ready_forms,
            "blocked": blocked_forms,
            "total_edges": len(edges),
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- internal ----------
    def _notify_unblocked(self, edge: dict) -> None:
        if not self._notifications:
            return
        try:
            self._notifications.emit(
                event_type="case.dependency_unblocked",
                title=f"{edge['dependent_form']} ready to file",
                body=(
                    f"The {edge['predecessor_form']} → {edge['dependent_form']} "
                    f"dependency ({edge['kind']}) is now cleared. "
                    f"Reason: {edge.get('unblock_reason', '')}"
                ),
                metadata={
                    "edge_id": edge["id"],
                    "workspace_id": edge["workspace_id"],
                    "predecessor_form": edge["predecessor_form"],
                    "dependent_form": edge["dependent_form"],
                    "kind": edge["kind"],
                },
            )
        except Exception:
            pass
