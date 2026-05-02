"""Tests for the white-glove Migration Importer."""

from immigration_compliance.services.migration_importer_service import (
    MigrationImporterService,
    COMPETITOR_PROFILES,
    REQUIRED_CANONICAL_FIELDS,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService


DOCKETWISE_CSV = (
    "client_first_name,client_last_name,client_dob,client_email,case_type,matter_status,uscis_receipt_number,petitioner_name,responsible_attorney,matter_id\n"
    "Wei,Chen,1992-05-15,wei@example.com,H1B,Filed,WAC2612345678,Acme Corp,Jennifer Park,DK-001\n"
    "Maria,Garcia,1990-03-22,maria@example.com,I130,In Progress,,Acme Corp,Michael Torres,DK-002\n"
    "John,Smith,1988-09-01,john@example.com,O1,Approved,WAC2511112222,Innovation Inc,David Kim,DK-003\n"
)

INSZOOM_CSV = (
    "beneficiary_first_name,beneficiary_last_name,petition_type,case_id,case_status,petitioner_company,lead_attorney\n"
    "Yuki,Tanaka,H-1B Initial,IZ-100,Filed-Pending,TechCo,Park\n"
    "Raj,Patel,L-1A,IZ-101,Pending,Multinational LLC,Torres\n"
)


def _make():
    ie = IntakeEngineService()
    cw = CaseWorkspaceService(intake_engine=ie)
    mi = MigrationImporterService(case_workspace=cw, intake_engine=ie)
    return ie, cw, mi


def test_profiles_cover_major_competitors():
    ids = set(COMPETITOR_PROFILES.keys())
    assert {"docketwise", "inszoom", "lollylaw", "clio", "eimmigration"} <= ids


def test_detect_profile_docketwise():
    headers = ["client_first_name", "client_last_name", "case_type", "matter_status"]
    assert MigrationImporterService.detect_profile(headers) == "docketwise"


def test_detect_profile_inszoom():
    headers = ["beneficiary_first_name", "beneficiary_last_name", "petition_type", "case_id"]
    assert MigrationImporterService.detect_profile(headers) == "inszoom"


def test_detect_profile_lollylaw():
    headers = ["first_name", "last_name", "matter_type", "matter_id"]
    assert MigrationImporterService.detect_profile(headers) == "lollylaw"


def test_detect_profile_unknown_returns_none():
    headers = ["random", "columns", "that", "match", "nothing"]
    assert MigrationImporterService.detect_profile(headers) is None


def test_map_row_translates_columns_and_values():
    _, _, mi = _make()
    raw = {"client_first_name": "Wei", "client_last_name": "Chen", "case_type": "H1B", "matter_status": "Filed"}
    canonical = mi.map_row("docketwise", raw)
    assert canonical["applicant_first_name"] == "Wei"
    assert canonical["visa_type"] == "H-1B"  # Value transform applied
    assert canonical["case_status"] == "filed"


def test_validate_row_flags_missing_required():
    _, _, mi = _make()
    issues = mi.validate_row({"applicant_first_name": "Wei"})
    assert "missing_applicant_last_name" in issues
    assert "missing_visa_type" in issues


def test_preview_detects_and_maps_docketwise():
    _, _, mi = _make()
    preview = mi.preview(DOCKETWISE_CSV)
    assert preview["profile_id"] == "docketwise"
    assert preview["summary"]["total"] == 3
    assert preview["summary"]["valid"] == 3


def test_preview_detects_inszoom():
    _, _, mi = _make()
    preview = mi.preview(INSZOOM_CSV)
    assert preview["profile_id"] == "inszoom"
    assert preview["summary"]["valid"] == 2


def test_run_import_creates_workspaces():
    ie, cw, mi = _make()
    result = mi.run_import("owner-1", DOCKETWISE_CSV)
    assert result["imported_count"] == 3
    workspaces = cw.list_workspaces(applicant_id="owner-1")
    assert len(workspaces) == 3


def test_run_import_idempotent_on_rerun():
    ie, cw, mi = _make()
    mi.run_import("owner-1", DOCKETWISE_CSV)
    second = mi.run_import("owner-1", DOCKETWISE_CSV)
    assert second["imported_count"] == 0
    assert second["skipped_count"] == 3


def test_dry_run_does_not_create_workspaces():
    ie, cw, mi = _make()
    result = mi.run_import("owner-1", DOCKETWISE_CSV, dry_run=True)
    assert result["imported_count"] == 0
    assert cw.list_workspaces(applicant_id="owner-1") == []


def test_imported_workspace_label_and_status_set():
    ie, cw, mi = _make()
    mi.run_import("owner-1", DOCKETWISE_CSV)
    workspaces = cw.list_workspaces(applicant_id="owner-1")
    chen = next(w for w in workspaces if "Chen" in (w.get("label") or ""))
    assert chen["status"] == "filed"
    assert chen["filing_receipt_number"] == "WAC2612345678"


def test_invalid_rows_skipped():
    invalid_csv = (
        "client_first_name,client_last_name,case_type,matter_status,matter_id\n"
        "Valid,Person,H1B,Open,V-001\n"
        ",MissingFirst,H1B,Open,V-002\n"
    )
    ie, cw, mi = _make()
    result = mi.run_import("owner-1", invalid_csv)
    assert result["imported_count"] == 1
    assert result["skipped_count"] == 1


def test_no_profile_detected_returns_error():
    bad_csv = "weird,columns,no_match\nx,y,z\n"
    _, _, mi = _make()
    result = mi.run_import("owner-1", bad_csv)
    assert "error" in result
    assert result.get("imported_count", 0) == 0


def test_explicit_profile_overrides_detection():
    """If the user knows the source platform, they can force the profile."""
    csv_with_unknown_headers = (
        "client_first_name,client_last_name,case_type,matter_status\n"
        "Wei,Chen,H1B,Open\n"
    )
    _, _, mi = _make()
    preview = mi.preview(csv_with_unknown_headers, profile_id="docketwise")
    assert preview["profile_id"] == "docketwise"


def test_required_canonical_fields_constant():
    assert "applicant_first_name" in REQUIRED_CANONICAL_FIELDS
    assert "visa_type" in REQUIRED_CANONICAL_FIELDS


def test_list_imports_filters_by_owner():
    ie, cw, mi = _make()
    mi.run_import("owner-1", DOCKETWISE_CSV)
    mi.run_import("owner-2", INSZOOM_CSV)
    own1 = mi.list_imports(owner_id="owner-1")
    assert len(own1) == 1
    own2 = mi.list_imports(owner_id="owner-2")
    assert len(own2) == 1


def test_eimmigration_profile_listed():
    profiles = MigrationImporterService.list_profiles()
    assert any(p["id"] == "eimmigration" for p in profiles)
