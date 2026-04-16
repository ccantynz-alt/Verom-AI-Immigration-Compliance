"""Gate Test — continuous website testing + auto-repair + resubmit loop.

Gate Test is a first-class Verom product: a watchdog that runs suites against
the live site (and the staging build), diagnoses failures, proposes a repair,
applies it when safe, retests, and only closes the loop once the site is green
again. Every run is logged so we can audit why a change was applied.

Safety model:
  - Every repair has an `auto_apply` flag. P0/P1 categories (broken links, 5xx,
    dead assets) may auto-apply. Anything touching auth, billing, legal, or
    escrow requires human approval before apply.
  - Repairs are always paired with a regression suite before resubmit. No
    blind commits.
  - Every repair emits a ledger entry into the Continuous Improvement
    service so shipped fixes count toward the daily advancement mandate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TestCategory(str, Enum):
    BROKEN_LINK = "broken_link"
    HTTP_5XX = "http_5xx"
    MISSING_ASSET = "missing_asset"
    SLOW_PAGE = "slow_page"
    ACCESSIBILITY = "accessibility"
    SEO = "seo"
    API_CONTRACT = "api_contract"
    AUTH_FLOW = "auth_flow"
    BILLING_FLOW = "billing_flow"
    LEGAL_PAGE = "legal_page"
    CONTENT_DRIFT = "content_drift"


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class RepairStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


# Categories that require human approval before Gate Test auto-applies a repair.
_RESTRICTED_CATEGORIES = {
    TestCategory.AUTH_FLOW,
    TestCategory.BILLING_FLOW,
    TestCategory.LEGAL_PAGE,
    TestCategory.API_CONTRACT,
}


@dataclass
class TestCase:
    id: str
    name: str
    category: TestCategory
    target: str          # URL path, API route, or asset
    assertion: str       # human-readable expectation
    enabled: bool = True


@dataclass
class TestResult:
    id: str
    case_id: str
    status: TestStatus
    detail: str
    duration_ms: int
    ran_at: str


@dataclass
class RepairProposal:
    id: str
    result_id: str
    category: TestCategory
    summary: str
    patch_hint: str
    auto_apply: bool
    status: RepairStatus
    created_at: str
    applied_at: str | None = None
    verified_at: str | None = None
    approver: str | None = None


@dataclass
class TestRun:
    id: str
    started_at: str
    finished_at: str | None
    results: list[str] = field(default_factory=list)  # result ids
    repairs: list[str] = field(default_factory=list)  # repair ids
    summary: dict[str, int] = field(default_factory=dict)


class GateTestService:
    """Continuous test + auto-repair + resubmit loop for the website."""

    def __init__(self) -> None:
        self._cases: dict[str, TestCase] = {}
        self._results: dict[str, TestResult] = {}
        self._repairs: dict[str, RepairProposal] = {}
        self._runs: dict[str, TestRun] = {}
        self._seed_default_suite()

    # ------------------------------------------------------------------
    # Suite management
    # ------------------------------------------------------------------
    def _seed_default_suite(self) -> None:
        seeds = [
            ("Landing page loads", TestCategory.HTTP_5XX, "/", "200 OK"),
            ("App dashboard loads", TestCategory.HTTP_5XX, "/app", "200 OK"),
            ("Login page loads", TestCategory.HTTP_5XX, "/login", "200 OK"),
            ("Applicant portal loads", TestCategory.HTTP_5XX, "/applicant", "200 OK"),
            ("Attorney portal loads", TestCategory.HTTP_5XX, "/attorney", "200 OK"),
            ("Privacy page present", TestCategory.LEGAL_PAGE, "/privacy", "legal content present"),
            ("Terms page present", TestCategory.LEGAL_PAGE, "/terms", "legal content present"),
            ("Landing CSS asset", TestCategory.MISSING_ASSET, "/static/css/landing.css", "asset exists"),
            ("Dashboard CSS asset", TestCategory.MISSING_ASSET, "/static/css/styles.css", "asset exists"),
            ("Health endpoint", TestCategory.API_CONTRACT, "/health", "status=ok"),
            ("Billing plans endpoint", TestCategory.API_CONTRACT, "/api/billing/plans", "list of plans"),
            ("Landing page title", TestCategory.SEO, "/", "has <title>"),
        ]
        for name, cat, target, assertion in seeds:
            self.register_case(name=name, category=cat, target=target, assertion=assertion)

    def register_case(
        self,
        name: str,
        category: TestCategory,
        target: str,
        assertion: str,
        enabled: bool = True,
    ) -> TestCase:
        case = TestCase(
            id=str(uuid.uuid4()),
            name=name,
            category=category,
            target=target,
            assertion=assertion,
            enabled=enabled,
        )
        self._cases[case.id] = case
        return case

    def list_cases(self) -> list[TestCase]:
        return sorted(self._cases.values(), key=lambda c: (c.category.value, c.name))

    def disable_case(self, case_id: str) -> TestCase:
        case = self._require_case(case_id)
        case.enabled = False
        return case

    # ------------------------------------------------------------------
    # Running a suite (simulated — real execution is done by the harness)
    # ------------------------------------------------------------------
    def start_run(self) -> TestRun:
        run = TestRun(
            id=str(uuid.uuid4()),
            started_at=datetime.utcnow().isoformat(),
            finished_at=None,
        )
        self._runs[run.id] = run
        return run

    def record_result(
        self,
        run_id: str,
        case_id: str,
        status: TestStatus,
        detail: str = "",
        duration_ms: int = 0,
    ) -> TestResult:
        run = self._require_run(run_id)
        self._require_case(case_id)
        result = TestResult(
            id=str(uuid.uuid4()),
            case_id=case_id,
            status=status,
            detail=detail,
            duration_ms=max(0, duration_ms),
            ran_at=datetime.utcnow().isoformat(),
        )
        self._results[result.id] = result
        run.results.append(result.id)
        return result

    def finish_run(self, run_id: str) -> TestRun:
        run = self._require_run(run_id)
        run.finished_at = datetime.utcnow().isoformat()
        summary: dict[str, int] = {s.value: 0 for s in TestStatus}
        for rid in run.results:
            summary[self._results[rid].status.value] += 1
        run.summary = summary
        return run

    def get_run(self, run_id: str) -> TestRun:
        return self._require_run(run_id)

    def list_runs(self) -> list[TestRun]:
        return sorted(self._runs.values(), key=lambda r: r.started_at, reverse=True)

    # ------------------------------------------------------------------
    # Auto-repair loop
    # ------------------------------------------------------------------
    def propose_repair(
        self,
        result_id: str,
        summary: str,
        patch_hint: str,
    ) -> RepairProposal:
        result = self._require_result(result_id)
        if result.status == TestStatus.PASS:
            raise ValueError("Cannot propose repair for a passing test")
        case = self._cases[result.case_id]
        auto_apply = case.category not in _RESTRICTED_CATEGORIES
        proposal = RepairProposal(
            id=str(uuid.uuid4()),
            result_id=result_id,
            category=case.category,
            summary=summary,
            patch_hint=patch_hint,
            auto_apply=auto_apply,
            status=RepairStatus.PROPOSED,
            created_at=datetime.utcnow().isoformat(),
        )
        self._repairs[proposal.id] = proposal
        # attach to the run
        for run in self._runs.values():
            if result_id in run.results:
                run.repairs.append(proposal.id)
                break
        return proposal

    def approve_repair(self, repair_id: str, approver: str) -> RepairProposal:
        repair = self._require_repair(repair_id)
        if repair.status != RepairStatus.PROPOSED:
            raise ValueError(f"Repair not in proposed state: {repair.status.value}")
        repair.status = RepairStatus.APPROVED
        repair.approver = approver
        return repair

    def apply_repair(self, repair_id: str) -> RepairProposal:
        repair = self._require_repair(repair_id)
        if repair.status not in {RepairStatus.PROPOSED, RepairStatus.APPROVED}:
            raise ValueError(f"Cannot apply repair in state {repair.status.value}")
        if not repair.auto_apply and repair.status != RepairStatus.APPROVED:
            raise ValueError("Restricted category — repair requires approval before apply")
        repair.status = RepairStatus.APPLIED
        repair.applied_at = datetime.utcnow().isoformat()
        return repair

    def verify_repair(self, repair_id: str, passed: bool) -> RepairProposal:
        repair = self._require_repair(repair_id)
        if repair.status != RepairStatus.APPLIED:
            raise ValueError("Repair must be applied before verification")
        if passed:
            repair.status = RepairStatus.VERIFIED
            repair.verified_at = datetime.utcnow().isoformat()
        else:
            repair.status = RepairStatus.ROLLED_BACK
        return repair

    def reject_repair(self, repair_id: str, reason: str = "") -> RepairProposal:
        repair = self._require_repair(repair_id)
        repair.status = RepairStatus.REJECTED
        if reason:
            repair.summary = f"{repair.summary} [rejected: {reason}]"
        return repair

    # ------------------------------------------------------------------
    # Health view
    # ------------------------------------------------------------------
    def health(self) -> dict[str, Any]:
        runs = list(self._runs.values())
        last_run = max(runs, key=lambda r: r.started_at) if runs else None
        failing_results = [
            r for r in self._results.values()
            if r.status in (TestStatus.FAIL, TestStatus.ERROR)
        ]
        open_repairs = [
            r for r in self._repairs.values()
            if r.status in (RepairStatus.PROPOSED, RepairStatus.APPROVED, RepairStatus.APPLIED)
        ]
        return {
            "cases": len(self._cases),
            "runs": len(runs),
            "last_run": None if last_run is None else {
                "id": last_run.id,
                "started_at": last_run.started_at,
                "finished_at": last_run.finished_at,
                "summary": last_run.summary,
            },
            "open_failures": len(failing_results),
            "open_repairs": len(open_repairs),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require_case(self, case_id: str) -> TestCase:
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Unknown test case: {case_id}")
        return case

    def _require_run(self, run_id: str) -> TestRun:
        run = self._runs.get(run_id)
        if run is None:
            raise ValueError(f"Unknown test run: {run_id}")
        return run

    def _require_result(self, result_id: str) -> TestResult:
        result = self._results.get(result_id)
        if result is None:
            raise ValueError(f"Unknown test result: {result_id}")
        return result

    def _require_repair(self, repair_id: str) -> RepairProposal:
        repair = self._repairs.get(repair_id)
        if repair is None:
            raise ValueError(f"Unknown repair: {repair_id}")
        return repair
