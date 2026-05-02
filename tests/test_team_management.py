"""Tests for the Team Management + RBAC service."""

from immigration_compliance.services.team_management_service import (
    TeamManagementService,
    BUILTIN_ROLES,
    ALL_PERMISSIONS,
    VISIBILITY_KINDS,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService


def _make():
    cw = CaseWorkspaceService()
    return cw, TeamManagementService(case_workspace=cw)


def test_builtin_roles_present():
    expected = {"admin", "partner", "attorney", "paralegal", "legal_assistant", "observer"}
    assert expected <= set(BUILTIN_ROLES.keys())


def test_admin_has_all_permissions():
    assert set(BUILTIN_ROLES["admin"]["permissions"]) == set(ALL_PERMISSIONS)


def test_attorney_can_submit_efiling():
    cw, tm = _make()
    tm.register_firm("Park Imm", "NY", "user-1")
    assert tm.has_permission("user-1", "efiling.submit") is True


def test_paralegal_cannot_submit_efiling():
    cw, tm = _make()
    firm = tm.register_firm("Park Imm", "NY", "user-1")
    tm.add_member(firm["id"], "user-paul", role="paralegal")
    assert tm.has_permission("user-paul", "efiling.submit") is False


def test_legal_assistant_cannot_post_trust_transactions():
    cw, tm = _make()
    firm = tm.register_firm("Park Imm", "NY", "user-1")
    tm.add_member(firm["id"], "user-lisa", role="legal_assistant")
    assert tm.has_permission("user-lisa", "trust.post_transaction") is False


def test_register_firm_auto_creates_admin_member():
    cw, tm = _make()
    firm = tm.register_firm("Park Imm", "NY", "user-1")
    members = tm.list_members(firm_id=firm["id"])
    assert len(members) == 1
    assert members[0]["role"] == "admin"


def test_add_member_unknown_firm_rejected():
    cw, tm = _make()
    try:
        tm.add_member("fake-firm", "u", role="attorney")
        assert False
    except ValueError:
        pass


def test_add_member_unknown_role_rejected():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    try:
        tm.add_member(firm["id"], "u2", role="emperor")
        assert False
    except ValueError:
        pass


def test_update_member_role():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    m = tm.add_member(firm["id"], "user-paul", role="paralegal")
    assert tm.has_permission("user-paul", "efiling.submit") is False
    tm.update_member_role(m["id"], "attorney")
    assert tm.has_permission("user-paul", "efiling.submit") is True


def test_deactivate_member_revokes_permissions():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    m = tm.add_member(firm["id"], "user-x", role="attorney")
    assert tm.has_permission("user-x", "case.view") is True
    tm.deactivate_member(m["id"], reason="left firm")
    assert tm.has_permission("user-x", "case.view") is False


def test_custom_role_creation():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    role = tm.create_custom_role(
        firm_id=firm["id"], role_id="senior_paralegal",
        label="Senior Paralegal",
        permissions=["case.view", "case.update", "billing.view"],
    )
    assert role["is_custom"] is True
    assert role["label"] == "Senior Paralegal"


def test_custom_role_cannot_override_builtin():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    try:
        tm.create_custom_role(firm["id"], "admin", "Admin", ["case.view"])
        assert False
    except ValueError:
        pass


def test_custom_role_unknown_permission_rejected():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    try:
        tm.create_custom_role(firm["id"], "x", "X", ["fake.permission"])
        assert False
    except ValueError:
        pass


def test_custom_role_assigned_to_member():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    tm.create_custom_role(firm["id"], "sp", "Senior", ["billing.view"])
    m = tm.add_member(firm["id"], "user-x", role="sp")
    assert tm.has_permission("user-x", "billing.view") is True
    assert tm.has_permission("user-x", "case.delete") is False


def test_list_roles_includes_builtins_plus_custom():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    tm.create_custom_role(firm["id"], "sp", "Senior", ["case.view"])
    roles = tm.list_roles_for_firm(firm["id"])
    role_ids = {r["id"] for r in roles}
    assert "admin" in role_ids
    assert "attorney" in role_ids
    assert "sp" in role_ids


def test_visibility_filter_attorney_sees_only_assigned():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    tm.add_member(firm["id"], "atty-1", role="attorney")
    cases = [
        {"id": "c1", "attorney_id": "atty-1", "applicant_id": "client-1"},
        {"id": "c2", "attorney_id": "atty-2", "applicant_id": "client-2"},
    ]
    visible = tm.filter_visible_cases("atty-1", cases)
    assert len(visible) == 1
    assert visible[0]["id"] == "c1"


def test_visibility_filter_admin_sees_firm_wide():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "user-admin")
    cases = [
        {"id": "c1", "firm_id": firm["id"], "attorney_id": "x"},
        {"id": "c2", "firm_id": firm["id"], "attorney_id": "y"},
        {"id": "c3", "firm_id": "other-firm", "attorney_id": "z"},
    ]
    visible = tm.filter_visible_cases("user-admin", cases)
    assert len(visible) == 2  # only this firm's cases


def test_offices():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    o = tm.add_office(firm["id"], "NYC HQ", address="100 Main", state="NY")
    assert o["firm_id"] == firm["id"]
    offices = tm.list_offices(firm_id=firm["id"])
    assert len(offices) == 1


def test_create_task():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    m = tm.add_member(firm["id"], "atty-1", role="attorney")
    t = tm.create_task(firm["id"], "Draft I-129", assigned_to_member_id=m["id"], priority="high", due_date="2026-12-01")
    assert t["status"] == "open"
    assert t["priority"] == "high"


def test_invalid_priority_rejected():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    try:
        tm.create_task(firm["id"], "X", priority="emergency!")
        assert False
    except ValueError:
        pass


def test_update_task_status():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "u")
    t = tm.create_task(firm["id"], "X")
    tm.update_task(t["id"], status="completed")
    refreshed = tm.list_tasks(firm_id=firm["id"])[0]
    assert refreshed["status"] == "completed"
    assert refreshed.get("completed_at")


def test_workload_aggregation():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "user-admin")
    m = tm.add_member(firm["id"], "atty-1", role="attorney")
    tm.create_task(firm["id"], "T1", assigned_to_member_id=m["id"], priority="high")
    tm.create_task(firm["id"], "T2", assigned_to_member_id=m["id"], priority="normal")
    tm.create_task(firm["id"], "T3", assigned_to_member_id=m["id"], priority="urgent")
    load = tm.get_workload_for_member(m["id"])
    assert load["open_tasks"] == 3
    assert load["urgent_tasks"] == 2  # high + urgent


def test_firm_workload_aggregates_all_members():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "user-admin")
    tm.add_member(firm["id"], "atty-1", role="attorney")
    tm.add_member(firm["id"], "para-1", role="paralegal")
    workload = tm.get_firm_workload(firm["id"])
    assert workload["member_count"] == 3  # founder + 2 added


def test_visibility_kinds_constant():
    assert set(VISIBILITY_KINDS) == {"all", "assigned", "own"}


def test_all_permissions_listed():
    perms = TeamManagementService.list_all_permissions()
    assert "case.view" in perms
    assert "trust.post_transaction" in perms
    assert "firm.manage_members" in perms


def test_get_user_permissions_returns_role_perms():
    cw, tm = _make()
    firm = tm.register_firm("F", "NY", "user-admin")
    perms = tm.get_user_permissions("user-admin")
    # Admin gets all
    assert len(perms) == len(ALL_PERMISSIONS)


def test_get_user_permissions_for_unregistered_user_empty():
    cw, tm = _make()
    perms = tm.get_user_permissions("ghost-user")
    assert perms == []
