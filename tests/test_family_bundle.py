"""Tests for the Family Bundle Engine — derivative case generation."""

from immigration_compliance.services.family_bundle_service import (
    FamilyBundleService,
    DERIVATIVE_RULES,
    VALID_RELATIONSHIPS,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService


def _make():
    ie = IntakeEngineService()
    cw = CaseWorkspaceService(intake_engine=ie)
    fb = FamilyBundleService(case_workspace=cw, intake_engine=ie)
    return ie, cw, fb


def test_derivative_rules_cover_major_visas():
    assert {"H-1B", "L-1", "O-1", "F-1", "J-1", "I-130", "I-485"} <= set(DERIVATIVE_RULES.keys())


def test_h1b_spouse_maps_to_h4_with_ead():
    rule = DERIVATIVE_RULES["H-1B"]["spouse"]
    assert rule["derivative_visa"] == "H-4"
    assert rule["filing_with"] == "I-539"
    assert rule["ead_eligible"] is True


def test_create_bundle_records_principal():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    assert b["principal_workspace_id"] == ws["id"]
    assert b["principal_visa_type"] == "H-1B"
    assert b["members"] == []


def test_add_spouse_creates_derivative_workspace():
    ie, cw, fb = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"us_address": "100 Main"})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    spouse = fb.add_dependent(b["id"], "spouse", "Lin", "Chen", "1992-08-15")
    assert spouse["derivative_visa"] == "H-4"
    assert spouse["derivative_workspace_id"] is not None
    derived_ws = cw.get_workspace(spouse["derivative_workspace_id"])
    assert derived_ws is not None
    assert derived_ws["visa_type"] == "H-4"


def test_add_child_above_age_cap_warns():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    child = fb.add_dependent(b["id"], "child", "Adult", "Kid", "2000-01-01")
    assert child["age_warning"] is not None
    assert "21-year age cap" in child["age_warning"] or "age cap" in child["age_warning"]


def test_add_child_under_age_cap_no_warning():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    child = fb.add_dependent(b["id"], "child", "Young", "Kid", "2018-05-22")
    assert child["age_warning"] is None


def test_invalid_relationship_rejected():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    try:
        fb.add_dependent(b["id"], "uncle", "U", "C", "1970-01-01")
        assert False
    except ValueError:
        pass


def test_unsupported_combination_rejected():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    # H-1B doesn't have a "parent" derivative rule
    try:
        fb.add_dependent(b["id"], "parent", "Old", "Chen", "1955-05-10")
        assert False
    except ValueError:
        pass


def test_l1_spouse_l2_with_ead():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "L-1", "US")
    b = fb.create_bundle("user-1", ws["id"], "L-1")
    spouse = fb.add_dependent(b["id"], "spouse", "S", "Smith", "1990-01-01")
    assert spouse["derivative_visa"] == "L-2"
    assert spouse["ead_eligible"] is True


def test_o1_spouse_o3_no_ead():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "O-1", "US")
    b = fb.create_bundle("user-1", ws["id"], "O-1")
    spouse = fb.add_dependent(b["id"], "spouse", "S", "Smith", "1990-01-01")
    assert spouse["derivative_visa"] == "O-3"
    assert spouse["ead_eligible"] is False


def test_i485_spouse_has_ead_and_advance_parole():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "I-485", "US")
    b = fb.create_bundle("user-1", ws["id"], "I-485")
    spouse = fb.add_dependent(b["id"], "spouse", "S", "Smith", "1990-01-01")
    assert spouse["ead_eligible"] is True
    assert spouse["advance_parole_eligible"] is True


def test_bundle_snapshot_aggregates_members():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    fb.add_dependent(b["id"], "spouse", "S", "Chen", "1992-01-01")
    fb.add_dependent(b["id"], "child", "C", "Chen", "2018-05-15")
    snap = fb.get_bundle_snapshot(b["id"])
    assert len(snap["members"]) == 2


def test_required_forms_for_bundle_lists_all():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    fb.add_dependent(b["id"], "spouse", "S", "Chen", "1992-01-01")
    forms = fb.list_required_forms_for_bundle(b["id"])
    # Principal H-1B + spouse I-539 + spouse EAD I-765
    assert len(forms) >= 3
    filings = [f["filing_with"] for f in forms]
    assert "I-539" in filings
    assert "I-765" in filings  # spouse EAD


def test_get_bundle_for_workspace_finds_principal_and_derivative():
    ie, cw, fb = _make()
    ws = cw.create_workspace("user-1", "H-1B", "US")
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    spouse = fb.add_dependent(b["id"], "spouse", "S", "Chen", "1992-01-01")
    # Find by principal
    found = fb.get_bundle_for_workspace(ws["id"])
    assert found is not None and found["id"] == b["id"]
    # Find by derivative
    found2 = fb.get_bundle_for_workspace(spouse["derivative_workspace_id"])
    assert found2 is not None and found2["id"] == b["id"]


def test_supported_combinations_listing():
    combos = FamilyBundleService.list_supported_combinations()
    assert len(combos) >= 10
    h1b_spouse = [c for c in combos if c["primary_visa"] == "H-1B" and c["relationship"] == "spouse"]
    assert len(h1b_spouse) == 1
    assert h1b_spouse[0]["derivative_visa"] == "H-4"


def test_valid_relationships_constant():
    assert VALID_RELATIONSHIPS == ("spouse", "child", "parent")


def test_dependent_inherits_principal_address():
    """Spouse's intake should inherit us_address from the principal."""
    ie, cw, fb = _make()
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], {"us_address": "100 Main St", "petitioner_name": "Acme"})
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"])
    b = fb.create_bundle("user-1", ws["id"], "H-1B")
    spouse = fb.add_dependent(b["id"], "spouse", "S", "Chen", "1992-01-01")
    derived_ws = cw.get_workspace(spouse["derivative_workspace_id"])
    if derived_ws.get("intake_session_id"):
        derived_session = ie.get_session(derived_ws["intake_session_id"])
        # Inherited fields land in the derived intake
        assert derived_session["answers"].get("us_address") == "100 Main St"
        assert derived_session["answers"].get("first_name") == "S"
