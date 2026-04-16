"""Tests for the Gate Test continuous test + auto-repair loop."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, auth_service, gate_test
from immigration_compliance.services.gate_test_service import (
    GateTestService,
    RepairStatus,
    TestCategory as GTCategory,
    TestStatus as GTStatus,
)

# Prevent pytest from collecting the service enums as test classes
GTCategory.__test__ = False
GTStatus.__test__ = False


client = TestClient(app)


def setup_function() -> None:
    # Clear shared state — runs/results/repairs only, keep seeded cases
    gate_test._runs.clear()
    gate_test._results.clear()
    gate_test._repairs.clear()
    auth_service._users.clear()
    auth_service._email_index.clear()
    auth_service._verification_docs.clear()


def _auth_headers(role: str = "applicant", email: str = "gate@test.com") -> dict:
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "pw12345678",
            "first_name": "Gate",
            "last_name": "Tester",
            "role": role,
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Seeded suite ----------------------------------------------------------

def test_default_suite_seeded():
    svc = GateTestService()
    cases = svc.list_cases()
    assert len(cases) >= 10
    categories = {c.category for c in cases}
    # Critical categories covered by the default suite
    assert GTCategory.HTTP_5XX in categories
    assert GTCategory.LEGAL_PAGE in categories
    assert GTCategory.API_CONTRACT in categories


# --- Run lifecycle ---------------------------------------------------------

def test_run_records_results_and_summarizes():
    svc = GateTestService()
    case = svc.list_cases()[0]
    run = svc.start_run()
    svc.record_result(run.id, case.id, GTStatus.PASS, "200 OK", 42)
    finished = svc.finish_run(run.id)
    assert finished.finished_at is not None
    assert finished.summary["pass"] == 1
    assert finished.summary["fail"] == 0


def test_record_result_with_unknown_run_fails():
    svc = GateTestService()
    case = svc.list_cases()[0]
    with pytest.raises(ValueError, match="Unknown test run"):
        svc.record_result("nope", case.id, GTStatus.PASS)


# --- Repair loop -----------------------------------------------------------

def test_repair_auto_applies_for_unrestricted_category():
    svc = GateTestService()
    case = [c for c in svc.list_cases() if c.category == GTCategory.HTTP_5XX][0]
    run = svc.start_run()
    result = svc.record_result(run.id, case.id, GTStatus.FAIL, "500 Internal")
    proposal = svc.propose_repair(result.id, "restart worker", "redeploy api/index.py")
    assert proposal.auto_apply is True
    applied = svc.apply_repair(proposal.id)
    assert applied.status == RepairStatus.APPLIED
    verified = svc.verify_repair(proposal.id, passed=True)
    assert verified.status == RepairStatus.VERIFIED


def test_repair_requires_approval_for_restricted_category():
    svc = GateTestService()
    case = [c for c in svc.list_cases() if c.category == GTCategory.LEGAL_PAGE][0]
    run = svc.start_run()
    result = svc.record_result(run.id, case.id, GTStatus.FAIL, "missing disclaimer")
    proposal = svc.propose_repair(result.id, "restore disclaimer", "frontend/privacy.html")
    assert proposal.auto_apply is False
    with pytest.raises(ValueError, match="requires approval"):
        svc.apply_repair(proposal.id)
    svc.approve_repair(proposal.id, approver="human@verom.ai")
    applied = svc.apply_repair(proposal.id)
    assert applied.status == RepairStatus.APPLIED


def test_repair_cannot_be_proposed_for_passing_test():
    svc = GateTestService()
    case = svc.list_cases()[0]
    run = svc.start_run()
    result = svc.record_result(run.id, case.id, GTStatus.PASS)
    with pytest.raises(ValueError, match="passing test"):
        svc.propose_repair(result.id, "x", "y")


def test_verify_requires_applied_state():
    svc = GateTestService()
    case = [c for c in svc.list_cases() if c.category == GTCategory.HTTP_5XX][0]
    run = svc.start_run()
    result = svc.record_result(run.id, case.id, GTStatus.FAIL)
    proposal = svc.propose_repair(result.id, "x", "y")
    with pytest.raises(ValueError, match="must be applied"):
        svc.verify_repair(proposal.id, passed=True)


def test_verify_failed_rolls_back():
    svc = GateTestService()
    case = [c for c in svc.list_cases() if c.category == GTCategory.HTTP_5XX][0]
    run = svc.start_run()
    result = svc.record_result(run.id, case.id, GTStatus.FAIL)
    proposal = svc.propose_repair(result.id, "x", "y")
    svc.apply_repair(proposal.id)
    rolled = svc.verify_repair(proposal.id, passed=False)
    assert rolled.status == RepairStatus.ROLLED_BACK


def test_health_reports_open_failures_and_repairs():
    svc = GateTestService()
    case = [c for c in svc.list_cases() if c.category == GTCategory.HTTP_5XX][0]
    run = svc.start_run()
    r = svc.record_result(run.id, case.id, GTStatus.FAIL)
    svc.propose_repair(r.id, "x", "y")
    svc.finish_run(run.id)
    health = svc.health()
    assert health["cases"] >= 10
    assert health["open_failures"] == 1
    assert health["open_repairs"] == 1
    assert health["last_run"]["id"] == run.id


# --- API surface -----------------------------------------------------------

def test_api_health():
    r = client.get("/api/gate-test/health")
    assert r.status_code == 200
    assert "cases" in r.json()


def test_api_full_run_flow():
    cases = client.get("/api/gate-test/cases").json()
    case = next(c for c in cases if c["category"] == "http_5xx")
    run = client.post("/api/gate-test/runs").json()
    res = client.post(
        f"/api/gate-test/runs/{run['id']}/results",
        json={
            "case_id": case["id"],
            "status": "fail",
            "detail": "500",
            "duration_ms": 120,
        },
    ).json()
    assert res["status"] == "fail"
    rep = client.post(
        "/api/gate-test/repairs",
        json={
            "result_id": res["id"],
            "summary": "restart",
            "patch_hint": "redeploy",
        },
    ).json()
    applied = client.post(f"/api/gate-test/repairs/{rep['id']}/apply").json()
    assert applied["status"] == "applied"
    verified = client.post(
        f"/api/gate-test/repairs/{rep['id']}/verify",
        params={"passed": "true"},
    ).json()
    assert verified["status"] == "verified"
    finished = client.post(f"/api/gate-test/runs/{run['id']}/finish").json()
    assert finished["finished_at"] is not None


def test_api_approve_repair_requires_auth():
    cases = client.get("/api/gate-test/cases").json()
    case = next(c for c in cases if c["category"] == "legal_page")
    run = client.post("/api/gate-test/runs").json()
    res = client.post(
        f"/api/gate-test/runs/{run['id']}/results",
        json={"case_id": case["id"], "status": "fail", "detail": "missing"},
    ).json()
    rep = client.post(
        "/api/gate-test/repairs",
        json={"result_id": res["id"], "summary": "fix", "patch_hint": "html"},
    ).json()
    # No auth — should be 401
    r = client.post(f"/api/gate-test/repairs/{rep['id']}/approve")
    assert r.status_code == 401
    headers = _auth_headers(email="approver@test.com")
    r2 = client.post(
        f"/api/gate-test/repairs/{rep['id']}/approve", headers=headers
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"
