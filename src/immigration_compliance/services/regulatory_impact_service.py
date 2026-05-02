"""Regulatory Impact Hook — when policy changes, find every affected case.

USCIS, DOL, and DOS publish policy memos, fee changes, prevailing-wage updates,
and visa-bulletin movements multiple times a month. Every change has the same
core question for an attorney: *which of my active cases does this affect?*

This service answers that automatically.

Mechanics:
  - A `RegulatoryEvent` describes a regulatory change with a structured
    impact predicate (e.g. "any I-129 with wage_level=I", or "EB-2 India
    priority date moved by 14 days")
  - When an event is published, walk every active workspace, evaluate the
    predicate against the workspace state, and produce an `ImpactReport`
    listing affected workspaces, severity per case, and a draft client
    notification per case
  - Reports are persisted; attorneys subscribe to the queue and act on
    each one (acknowledged / dismissed / draft sent)

Predicates are data-driven and explainable — every match comes with the
exact field comparison that triggered it. No black-box LLM matching.

Future hook: pluggable scrapers feed Federal Register, USCIS news, DOL
flag updates, and visa bulletins into `ingest_event()`. Today the service
exposes the matching engine + draft generator; ingestion sources are
wired by the upstream `RegulatoryService`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Predicate evaluation
# ---------------------------------------------------------------------------

# Predicates use a tiny safe DSL:
#   {"field": "workspace.visa_type", "op": "in", "value": ["H-1B", "L-1"]}
#   {"field": "intake.answers.wage_level", "op": "==", "value": "I"}
#   {"field": "workspace.country", "op": "==", "value": "US"}
#   {"field": "workspace.status", "op": "in", "value": ["intake","documents","review","filed"]}
# Compound predicates use {"all_of": [...]} or {"any_of": [...]}.

OPS = ("==", "!=", "in", "not_in", "<", "<=", ">", ">=", "contains", "exists")


def _resolve_path(snapshot: dict, path: str) -> Any:
    """Walk a dotted path into the snapshot. Returns None on miss."""
    parts = path.split(".")
    cur: Any = snapshot
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def evaluate_predicate(predicate: dict, snapshot: dict) -> tuple[bool, list[dict]]:
    """Evaluate a predicate against a workspace snapshot.

    Returns (matched, evidence) where evidence lists every leaf comparison
    so we can show attorneys exactly *why* a case was flagged."""
    if "all_of" in predicate:
        matches = []
        all_ok = True
        for sub in predicate["all_of"]:
            ok, ev = evaluate_predicate(sub, snapshot)
            matches.extend(ev)
            if not ok:
                all_ok = False
        return all_ok, matches
    if "any_of" in predicate:
        matches = []
        any_ok = False
        for sub in predicate["any_of"]:
            ok, ev = evaluate_predicate(sub, snapshot)
            matches.extend(ev)
            if ok:
                any_ok = True
        return any_ok, matches
    if "not" in predicate:
        ok, ev = evaluate_predicate(predicate["not"], snapshot)
        return (not ok), ev

    # Leaf predicate
    field = predicate.get("field", "")
    op = predicate.get("op", "==")
    value = predicate.get("value")
    actual = _resolve_path(snapshot, field)
    matched = _compare(op, actual, value)
    return matched, [{"field": field, "op": op, "expected": value, "actual": actual, "matched": matched}]


def _compare(op: str, actual: Any, expected: Any) -> bool:
    if op == "exists":
        return actual is not None
    if actual is None:
        return False
    if op == "==":
        return actual == expected
    if op == "!=":
        return actual != expected
    if op == "in":
        return actual in expected if isinstance(expected, (list, tuple, set)) else False
    if op == "not_in":
        return actual not in expected if isinstance(expected, (list, tuple, set)) else True
    if op == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected.lower() in actual.lower()
        if isinstance(actual, (list, tuple, set)):
            return expected in actual
        return False
    try:
        if op == "<":
            return actual < expected
        if op == "<=":
            return actual <= expected
        if op == ">":
            return actual > expected
        if op == ">=":
            return actual >= expected
    except TypeError:
        return False
    return False


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

EVENT_KINDS = (
    "policy_memo",        # USCIS Policy Manual updates
    "fee_change",         # filing fee schedule update
    "wage_threshold",     # DOL wage / TSMIT / TSMIT-equivalent change
    "visa_bulletin",      # DOS Visa Bulletin priority date movement
    "form_edition",       # form edition cutover
    "processing_time",    # processing time alert
    "executive_order",    # executive action
    "rule_change",        # regulatory rule (NPRM/final rule)
)

SEVERITY_LEVELS = ("informational", "advisory", "action_required", "blocking")


class RegulatoryImpactService:
    """When a regulatory change is published, find every affected case."""

    def __init__(self, case_workspace: Any | None = None) -> None:
        self._cases = case_workspace
        self._events: dict[str, dict] = {}
        self._reports: dict[str, dict] = {}

    # ---------- events ----------
    def ingest_event(
        self,
        title: str,
        kind: str,
        impact_predicate: dict,
        severity: str = "advisory",
        source: str = "manual",
        effective_date: str | None = None,
        summary: str = "",
        client_notification_template: str = "",
        attorney_action_template: str = "",
        link: str = "",
    ) -> dict:
        """Register a regulatory event. The predicate is what we'll evaluate
        against every active workspace to find affected cases."""
        if kind not in EVENT_KINDS:
            raise ValueError(f"Unknown event kind: {kind}")
        if severity not in SEVERITY_LEVELS:
            raise ValueError(f"Unknown severity: {severity}")
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "title": title,
            "kind": kind,
            "impact_predicate": impact_predicate,
            "severity": severity,
            "source": source,
            "effective_date": effective_date or datetime.utcnow().date().isoformat(),
            "summary": summary,
            "client_notification_template": client_notification_template,
            "attorney_action_template": attorney_action_template,
            "link": link,
            "ingested_at": datetime.utcnow().isoformat(),
            "report_id": None,
        }
        self._events[event_id] = event
        return event

    def get_event(self, event_id: str) -> dict | None:
        return self._events.get(event_id)

    def list_events(self, kind: str | None = None, severity: str | None = None) -> list[dict]:
        evs = list(self._events.values())
        if kind:
            evs = [e for e in evs if e["kind"] == kind]
        if severity:
            evs = [e for e in evs if e["severity"] == severity]
        return sorted(evs, key=lambda e: e["ingested_at"], reverse=True)

    # ---------- analysis ----------
    def analyze_event(self, event_id: str, only_active: bool = True) -> dict:
        """Walk every workspace, evaluate predicate, produce an ImpactReport.

        Returns a structured report with affected workspaces, evidence per
        case, and a per-case draft client notification."""
        event = self._events.get(event_id)
        if event is None:
            raise ValueError(f"Event not found: {event_id}")
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")

        all_workspaces = self._cases.list_workspaces()
        if only_active:
            all_workspaces = [w for w in all_workspaces if w.get("status") not in ("approved", "denied", "withdrawn")]

        affected: list[dict] = []
        scanned = 0
        for ws in all_workspaces:
            scanned += 1
            try:
                snap = self._cases.get_snapshot(ws["id"])
            except Exception:
                continue
            matched, evidence = evaluate_predicate(event["impact_predicate"], snap)
            if matched:
                affected.append({
                    "workspace_id": ws["id"],
                    "applicant_id": ws.get("applicant_id"),
                    "attorney_id": ws.get("attorney_id"),
                    "label": ws.get("label"),
                    "visa_type": ws.get("visa_type"),
                    "status": ws.get("status"),
                    "evidence": evidence,
                    "draft_client_notification": self._render_client_draft(event, ws, snap),
                    "draft_attorney_action": self._render_attorney_action(event, ws, snap),
                    "severity": event["severity"],
                })

        report_id = str(uuid.uuid4())
        report = {
            "id": report_id,
            "event_id": event_id,
            "event_title": event["title"],
            "event_kind": event["kind"],
            "severity": event["severity"],
            "scanned_count": scanned,
            "affected_count": len(affected),
            "affected": affected,
            "computed_at": datetime.utcnow().isoformat(),
        }
        self._reports[report_id] = report
        event["report_id"] = report_id
        return report

    @staticmethod
    def _render_client_draft(event: dict, ws: dict, snap: dict) -> str:
        tmpl = event.get("client_notification_template")
        if not tmpl:
            tmpl = (
                "Dear {applicant_name},\n\n"
                "We're reaching out about a recent change at {agency}: {event_title}. "
                "Based on our review, this change may affect your {visa_type} case.\n\n"
                "{summary}\n\n"
                "We're handling the next steps on your behalf — no action needed from you "
                "right now. We'll be in touch shortly with specifics for your case.\n\n"
                "Best regards,\nYour Verom case team"
            )
        return tmpl.format(
            applicant_name="[Client]",
            agency=event["kind"].replace("_", " ").title() if event["kind"] in ("fee_change", "wage_threshold") else "USCIS",
            event_title=event["title"],
            visa_type=ws.get("visa_type", "your"),
            summary=event.get("summary", "")[:500],
        )

    @staticmethod
    def _render_attorney_action(event: dict, ws: dict, snap: dict) -> str:
        tmpl = event.get("attorney_action_template")
        if tmpl:
            return tmpl
        sev = event.get("severity", "advisory")
        if sev == "blocking":
            return f"BLOCKING: review {ws.get('visa_type')} case immediately — strategy may need to change."
        if sev == "action_required":
            return (
                f"ACTION REQUIRED: review the case strategy for this {ws.get('visa_type')} matter; "
                "consider whether a re-filing, supplement, or expedite is warranted."
            )
        if sev == "advisory":
            return f"Advisory: monitor for downstream effects on this {ws.get('visa_type')} case; no immediate action."
        return "Informational: no action required."

    # ---------- reports ----------
    def get_report(self, report_id: str) -> dict | None:
        return self._reports.get(report_id)

    def list_reports(
        self,
        attorney_id: str | None = None,
        applicant_id: str | None = None,
    ) -> list[dict]:
        reports = list(self._reports.values())
        if attorney_id or applicant_id:
            filtered = []
            for r in reports:
                # If an attorney filter is set, keep reports that affect at least one of their cases
                if attorney_id:
                    if any(a.get("attorney_id") == attorney_id for a in r["affected"]):
                        filtered.append(r)
                elif applicant_id:
                    if any(a.get("applicant_id") == applicant_id for a in r["affected"]):
                        filtered.append(r)
            return filtered
        return sorted(reports, key=lambda r: r["computed_at"], reverse=True)

    # ---------- introspection ----------
    @staticmethod
    def list_event_kinds() -> list[str]:
        return list(EVENT_KINDS)

    @staticmethod
    def list_severity_levels() -> list[str]:
        return list(SEVERITY_LEVELS)
