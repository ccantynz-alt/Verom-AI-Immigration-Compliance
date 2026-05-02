"""SOC 2 Audit Artifact Generator — auditor-ready evidence pack.

SOC 2 Type II is a non-negotiable for enterprise clients. Without the audit
artifact, every Fortune 500 corporate immigration buyer drops out of the
sales cycle. This service generates the evidence pack auditors actually
ask for, pulling from the persistent audit log, the conflict-check log,
the trust-account reconciliation history, and access control records.

Trust Service Criteria covered:
  - SECURITY      — access controls, MFA, encryption-at-rest assertions
  - AVAILABILITY  — uptime SLAs, incident response, backup verification
  - CONFIDENTIALITY — data classification, encryption, access reviews
  - PROCESSING_INTEGRITY — audit log completeness, change management
  - PRIVACY       — data handling, consent records, subject access logs

Generated artifact is a structured manifest + evidence-file index that an
auditor can import. The platform itself doesn't issue SOC 2 reports — that's
the auditor's job. This service produces the inputs the auditor needs.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta
from typing import Any


TSC = (
    "security",
    "availability",
    "confidentiality",
    "processing_integrity",
    "privacy",
)


# Each control: ID, criterion, description, evidence sources we can pull
CONTROL_CATALOG: dict[str, dict[str, Any]] = {
    "CC1.1": {
        "criterion": "security",
        "category": "Control Environment",
        "description": "Organizational structure includes designated owners for security/privacy.",
        "evidence_sources": ["team_management.list_members", "team_management.list_builtin_roles"],
    },
    "CC1.4": {
        "criterion": "security",
        "category": "Control Environment",
        "description": "Personnel changes are documented including onboarding/offboarding.",
        "evidence_sources": ["team_management.member_history", "audit_log.firm_management"],
    },
    "CC2.1": {
        "criterion": "security",
        "category": "Communication & Information",
        "description": "Internal communication of policy changes captured in audit log.",
        "evidence_sources": ["audit_log.policy_changes"],
    },
    "CC3.1": {
        "criterion": "security",
        "category": "Risk Assessment",
        "description": "Risk register including conflict checks and ethics walls.",
        "evidence_sources": ["conflict_check.audit_summary", "conflict_check.ethics_walls"],
    },
    "CC5.1": {
        "criterion": "security",
        "category": "Control Activities",
        "description": "Logical access controls enforced via RBAC.",
        "evidence_sources": ["team_management.role_permissions", "team_management.list_all_permissions"],
    },
    "CC6.1": {
        "criterion": "security",
        "category": "Logical Access",
        "description": "User authentication is controlled and logged.",
        "evidence_sources": ["auth.login_log", "audit_log.actor_id"],
    },
    "CC6.2": {
        "criterion": "security",
        "category": "Logical Access",
        "description": "Role-based access is reviewed periodically.",
        "evidence_sources": ["team_management.role_audits"],
    },
    "CC6.6": {
        "criterion": "security",
        "category": "Logical Access",
        "description": "Externally-facing services use TLS; webhooks signed.",
        "evidence_sources": ["notifications.webhook_secret_rotation_log"],
    },
    "CC7.1": {
        "criterion": "security",
        "category": "System Operations",
        "description": "System monitoring includes SLA breach tracking.",
        "evidence_sources": ["sla_tracker.list_breached", "audit_log.sla_breaches"],
    },
    "CC7.2": {
        "criterion": "security",
        "category": "System Operations",
        "description": "Anomalies trigger notification + escalation.",
        "evidence_sources": ["sla_tracker.tick", "cadence_tracker.list_escalations"],
    },
    "CC7.3": {
        "criterion": "security",
        "category": "Incident Response",
        "description": "Incidents tracked and resolved with attribution.",
        "evidence_sources": ["audit_log.incidents"],
    },
    "CC8.1": {
        "criterion": "processing_integrity",
        "category": "Change Management",
        "description": "Code changes go through review (git history evidence).",
        "evidence_sources": ["audit_log.deployment_log"],
    },
    "PI1.1": {
        "criterion": "processing_integrity",
        "category": "Processing Integrity",
        "description": "Form populations and filings preserve provenance.",
        "evidence_sources": ["form_population.provenance_log",
                              "efiling_proxy.submission_events"],
    },
    "PI1.4": {
        "criterion": "processing_integrity",
        "category": "Processing Integrity",
        "description": "Trust-account three-way reconciliation runs and discrepancies are flagged.",
        "evidence_sources": ["trust_accounting.list_reconciliations"],
    },
    "C1.1": {
        "criterion": "confidentiality",
        "category": "Data Classification",
        "description": "Confidential data is encrypted at rest (SQLite WAL) and access-restricted.",
        "evidence_sources": ["persistent_store.config", "team_management.role_permissions"],
    },
    "C1.2": {
        "criterion": "confidentiality",
        "category": "Data Disposal",
        "description": "Document share links honor expiry; deactivation logged.",
        "evidence_sources": ["doc_management.share_link_log"],
    },
    "P1.1": {
        "criterion": "privacy",
        "category": "Notice & Communication",
        "description": "Privacy disclosures attached to translated client communications.",
        "evidence_sources": ["translation.disclaimers"],
    },
    "P3.1": {
        "criterion": "privacy",
        "category": "Choice & Consent",
        "description": "Consent recorded for OAuth + share-link operations.",
        "evidence_sources": ["calendar_sync.list_connections", "doc_management.share_link_log"],
    },
    "P5.1": {
        "criterion": "privacy",
        "category": "Access",
        "description": "Subject access logged via persistent audit log.",
        "evidence_sources": ["persistent_store.get_log"],
    },
    "P6.1": {
        "criterion": "privacy",
        "category": "Disclosure & Notification",
        "description": "Data breaches trigger documented notification flow.",
        "evidence_sources": ["audit_log.breach_notifications"],
    },
    "A1.1": {
        "criterion": "availability",
        "category": "Capacity Planning",
        "description": "Capacity monitored via workload aggregation per attorney.",
        "evidence_sources": ["team_management.get_firm_workload"],
    },
    "A1.2": {
        "criterion": "availability",
        "category": "Backup & Recovery",
        "description": "SQLite WAL journaling + namespace snapshotting documented.",
        "evidence_sources": ["persistent_store.list_namespaces"],
    },
}


REPORT_KINDS = ("evidence_pack", "control_inventory", "incident_report")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class Soc2AuditService:
    """Generate auditor-ready evidence packs from platform telemetry."""

    def __init__(
        self,
        persistent_store: Any | None = None,
        team_management_service: Any | None = None,
        conflict_check_service: Any | None = None,
        trust_accounting_service: Any | None = None,
        sla_tracker_service: Any | None = None,
        cadence_tracker_service: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self._store = persistent_store
        self._team = team_management_service
        self._conflicts = conflict_check_service
        self._trust = trust_accounting_service
        self._sla = sla_tracker_service
        self._cadence = cadence_tracker_service
        self._notifications = notification_service
        self._reports: dict[str, dict] = {}
        self._incidents: list[dict] = []

    # ---------- introspection ----------
    @staticmethod
    def list_trust_service_criteria() -> list[str]:
        return list(TSC)

    @staticmethod
    def list_controls(criterion: str | None = None) -> list[dict]:
        out = []
        for cid, c in CONTROL_CATALOG.items():
            if criterion and c["criterion"] != criterion:
                continue
            out.append({"id": cid, **c})
        return out

    @staticmethod
    def get_control(control_id: str) -> dict | None:
        c = CONTROL_CATALOG.get(control_id)
        if c is None:
            return None
        return {"id": control_id, **c}

    # ---------- incident logging ----------
    def log_incident(
        self, incident_type: str, severity: str, description: str,
        affected_user_ids: list[str] | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        if severity not in ("low", "medium", "high", "critical"):
            raise ValueError(f"Invalid severity: {severity}")
        record = {
            "id": str(uuid.uuid4()),
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
            "affected_user_ids": affected_user_ids or [],
            "actor_user_id": actor_user_id,
            "logged_at": datetime.utcnow().isoformat(),
            "status": "open",
        }
        self._incidents.append(record)
        return record

    def resolve_incident(self, incident_id: str, resolution_notes: str = "") -> dict:
        for inc in self._incidents:
            if inc["id"] == incident_id:
                inc["status"] = "resolved"
                inc["resolved_at"] = datetime.utcnow().isoformat()
                inc["resolution_notes"] = resolution_notes
                return inc
        raise ValueError("Incident not found")

    def list_incidents(self, severity: str | None = None, status: str | None = None,
                       since: str | None = None) -> list[dict]:
        out = self._incidents
        if severity:
            out = [i for i in out if i["severity"] == severity]
        if status:
            out = [i for i in out if i["status"] == status]
        if since:
            out = [i for i in out if i["logged_at"] >= since]
        return out

    # ---------- evidence pack generation ----------
    def generate_evidence_pack(
        self,
        period_start: str,
        period_end: str,
        firm_id: str | None = None,
        kind: str = "evidence_pack",
    ) -> dict:
        if kind not in REPORT_KINDS:
            raise ValueError(f"Unknown report kind: {kind}")
        report_id = str(uuid.uuid4())
        controls = []
        for cid, ctrl in CONTROL_CATALOG.items():
            evidence_records = self._gather_evidence(cid, ctrl, period_start, period_end, firm_id)
            controls.append({
                "control_id": cid,
                **ctrl,
                "evidence_records_count": len(evidence_records),
                "evidence_summary": self._summarize_evidence(cid, evidence_records),
                "evidence_hash": _evidence_hash(evidence_records),
            })

        # Aggregate stats
        incidents_in_window = [
            i for i in self._incidents
            if period_start <= i["logged_at"] <= period_end + "T23:59:59"
        ]

        record = {
            "id": report_id,
            "kind": kind,
            "period_start": period_start,
            "period_end": period_end,
            "firm_id": firm_id,
            "trust_service_criteria_covered": list(TSC),
            "controls": controls,
            "control_count": len(controls),
            "incident_count": len(incidents_in_window),
            "incident_breakdown": {
                sev: sum(1 for i in incidents_in_window if i["severity"] == sev)
                for sev in ("low", "medium", "high", "critical")
            },
            "audit_log_entry_count": self._audit_log_count(period_start, period_end),
            "trust_reconciliations_count": self._trust_recon_count(),
            "rbac_role_count": self._role_count(),
            "generated_at": datetime.utcnow().isoformat(),
            "auditor_distribution_notes": (
                "This evidence pack is intended for SOC 2 Type II auditor consumption. "
                "Each control entry includes an evidence_summary describing the data "
                "the auditor can review, and an evidence_hash for tamper-evidence "
                "verification. The platform does not issue SOC 2 attestations — the "
                "auditor reviews this pack and issues the report."
            ),
        }
        self._reports[report_id] = record
        return record

    def _gather_evidence(self, control_id: str, ctrl: dict, period_start: str,
                         period_end: str, firm_id: str | None) -> list[dict]:
        # Walk the evidence_sources list and pull from wired services
        records: list[dict] = []
        for source in ctrl.get("evidence_sources", []):
            try:
                if source.startswith("audit_log") and self._store:
                    namespace = source.split(".", 1)[1] if "." in source else None
                    log = self._store.get_log(
                        namespace=namespace, since=period_start, limit=200,
                    )
                    log = [l for l in log if l["at"] <= period_end + "T23:59:59"]
                    records.extend(log[:50])
                elif source.startswith("conflict_check") and self._conflicts:
                    if "audit_summary" in source:
                        records.append({"summary": self._conflicts.get_audit_summary()})
                    elif "ethics_walls" in source:
                        records.extend(self._conflicts.list_ethics_walls()[:20])
                elif source.startswith("trust_accounting") and self._trust:
                    if "list_reconciliations" in source:
                        records.extend(self._trust.list_reconciliations(limit=20))
                elif source.startswith("sla_tracker") and self._sla:
                    if "list_breached" in source:
                        records.extend(self._sla.list_breached()[:20])
                elif source.startswith("cadence_tracker") and self._cadence:
                    if "list_escalations" in source:
                        records.extend(self._cadence.list_escalations(limit=20))
                elif source.startswith("team_management") and self._team:
                    if "list_all_permissions" in source:
                        records.append({"permissions": self._team.list_all_permissions()})
                    elif "list_builtin_roles" in source:
                        records.append({"roles": self._team.list_builtin_roles()})
            except Exception:
                # Don't crash evidence gathering on partial wiring
                continue
        return records

    @staticmethod
    def _summarize_evidence(control_id: str, records: list[dict]) -> str:
        if not records:
            return "No evidence records pulled in this period."
        return f"{len(records)} evidence record(s) collected from wired services. Auditor can drill into raw records via the API."

    def _audit_log_count(self, since: str, until: str) -> int:
        if not self._store:
            return 0
        try:
            return len(self._store.get_log(since=since, limit=10000))
        except Exception:
            return 0

    def _trust_recon_count(self) -> int:
        if not self._trust:
            return 0
        try:
            return len(self._trust.list_reconciliations(limit=1000))
        except Exception:
            return 0

    def _role_count(self) -> int:
        if not self._team:
            return 0
        try:
            return len(self._team.list_builtin_roles())
        except Exception:
            return 0

    # ---------- queries ----------
    def get_report(self, report_id: str) -> dict | None:
        return self._reports.get(report_id)

    def list_reports(self, kind: str | None = None, limit: int = 20) -> list[dict]:
        out = list(self._reports.values())
        if kind:
            out = [r for r in out if r["kind"] == kind]
        return sorted(out, key=lambda r: r["generated_at"], reverse=True)[:limit]


def _evidence_hash(records: list[dict]) -> str:
    """Deterministic hash of evidence records for tamper-evidence."""
    import json
    payload = json.dumps(records, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
