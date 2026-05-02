"""Tests for Conflict-of-Interest detection."""

from immigration_compliance.services.conflict_check_service import ConflictCheckService


def test_clear_when_no_existing_cases():
    svc = ConflictCheckService()
    r = svc.check_new_case({"applicant_name": "John Doe"}, attorney_id="atty-1")
    assert r["decision"] == "clear"
    assert r["total_conflicts"] == 0


def test_direct_duplicate_same_attorney():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "John Doe", "case_type": "H-1B"})
    r = svc.check_new_case({"applicant_name": "John Doe"}, attorney_id="atty-1")
    assert r["total_conflicts"] >= 1
    assert any(c["code"] == "DIRECT_DUPLICATE" and c["severity"] == "blocking" for c in r["conflicts"])
    assert r["decision"] == "decline_unless_waived"


def test_firm_duplicate_imputed():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "firm_id": "firm-A", "applicant_name": "John Doe"})
    r = svc.check_new_case({"applicant_name": "John Doe"}, attorney_id="atty-2", firm_id="firm-A")
    codes = [c["code"] for c in r["conflicts"]]
    assert "FIRM_DUPLICATE" in codes


def test_adverse_party_employer_match():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "Acme Corp", "case_type": "I-140"})
    r = svc.check_new_case({"applicant_name": "Jane Smith", "employer_name": "Acme Corp"}, attorney_id="atty-1")
    codes = [c["code"] for c in r["conflicts"]]
    assert "ADVERSE_PARTY" in codes


def test_former_client_low_severity():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "John Doe", "status": "closed"})
    r = svc.check_new_case({"applicant_name": "John Doe"}, attorney_id="atty-1")
    codes = [c["code"] for c in r["conflicts"]]
    assert "FORMER_CLIENT" in codes
    assert r["decision"] == "proceed_with_disclosure"


def test_related_party_disclosure():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "Mary Smith"})
    r = svc.check_new_case({"applicant_name": "John Smith", "related_party_names": ["Mary Smith"]}, attorney_id="atty-1")
    codes = [c["code"] for c in r["conflicts"]]
    assert "RELATED_PARTY" in codes


def test_name_match_handles_case_and_whitespace():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "  john doe  "})
    r = svc.check_new_case({"applicant_name": "John  Doe"}, attorney_id="atty-1")
    assert r["total_conflicts"] >= 1


def test_check_log_stored():
    svc = ConflictCheckService()
    svc.check_new_case({"applicant_name": "Person A"}, attorney_id="atty-1")
    svc.check_new_case({"applicant_name": "Person B"}, attorney_id="atty-1")
    log = svc.get_check_log(attorney_id="atty-1")
    assert len(log) == 2


def test_audit_summary_counts():
    svc = ConflictCheckService()
    svc.register_case({"id": "c1", "attorney_id": "atty-1", "applicant_name": "Bob"})
    svc.check_new_case({"applicant_name": "Bob"}, attorney_id="atty-1")
    svc.check_new_case({"applicant_name": "Carol"}, attorney_id="atty-1")
    summary = svc.get_audit_summary()
    assert summary["total_checks"] == 2
    assert summary["total_cases"] == 1


def test_ethics_wall_lifecycle():
    svc = ConflictCheckService()
    w = svc.create_ethics_wall("c1", ["user-x", "user-y"], "Conflict between matters")
    assert w["active"] is True
    walls = svc.list_ethics_walls(case_id="c1")
    assert len(walls) == 1
    svc.deactivate_ethics_wall(w["id"])
    refreshed = svc.list_ethics_walls(case_id="c1")[0]
    assert refreshed["active"] is False
