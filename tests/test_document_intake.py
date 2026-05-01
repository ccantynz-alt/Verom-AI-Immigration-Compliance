"""Tests for the Document Intake pipeline (upload → classify → extract → validate → reconcile)."""

from immigration_compliance.services.document_intake_service import (
    DocumentIntakeService,
    DOCUMENT_TYPES,
)
from immigration_compliance.services.intake_engine_service import IntakeEngineService


def test_upload_basic_passport():
    svc = DocumentIntakeService()
    r = svc.upload("user-1", "sess-1", "passport_chen.pdf", size_bytes=2_000_000, page_count=2, resolution_dpi=300)
    assert r["document_type"] == "passport"
    assert r["status"] == "ready"
    assert "valid_passport" in r["satisfies"]
    assert r["stages"]["quality"]["acceptable"] is True


def test_upload_unsupported_extension_flagged():
    svc = DocumentIntakeService()
    r = svc.upload("user-1", None, "scan.exe", size_bytes=200_000)
    assert r["stages"]["quality"]["acceptable"] is False
    assert r["status"] == "needs_attention"


def test_upload_too_small_flagged():
    svc = DocumentIntakeService()
    r = svc.upload("user-1", None, "thumb.jpg", size_bytes=10_000)
    assert r["stages"]["quality"]["acceptable"] is False
    assert any("small" in i.lower() for i in r["stages"]["quality"]["issues"])


def test_upload_low_dpi_flagged():
    svc = DocumentIntakeService()
    r = svc.upload("user-1", None, "passport.pdf", size_bytes=500_000, resolution_dpi=72)
    assert r["stages"]["quality"]["acceptable"] is False
    assert any("DPI" in i for i in r["stages"]["quality"]["issues"])


def test_classify_via_filename_heuristic():
    svc = DocumentIntakeService()
    cases = [
        ("ielts_results.pdf", "english_test"),
        ("bank_statement_jan.pdf", "bank_statement"),
        ("i20_form.pdf", "i20"),
        ("i797_approval.pdf", "approval_notice"),
        ("expert_letter_dr_smith.pdf", "support_letter"),
        ("birth_certificate.pdf", "birth_certificate"),
    ]
    for fname, expected in cases:
        r = svc.upload("u", None, fname, size_bytes=500_000, resolution_dpi=300)
        assert r["document_type"] == expected, f"{fname} → got {r['document_type']}"


def test_declared_type_overrides_heuristic():
    svc = DocumentIntakeService()
    r = svc.upload("u", None, "random_name.pdf", size_bytes=500_000, declared_type="i20", resolution_dpi=300)
    assert r["document_type"] == "i20"
    assert r["stages"]["classify"]["method"] == "declared"


def test_extracted_fields_populated():
    svc = DocumentIntakeService()
    r = svc.upload("u", None, "passport.pdf", size_bytes=500_000, resolution_dpi=300)
    extracted = r["extracted"]
    for f in DOCUMENT_TYPES["passport"]["fields"]:
        assert f in extracted


def test_reconcile_marks_complete_when_required_doc_uploaded():
    doc_svc = DocumentIntakeService()
    intake = IntakeEngineService()
    # F-1 has 'valid_passport' as a base document
    checklist = intake.get_document_checklist("F-1")
    doc_svc.upload("user-1", "sess-1", "passport.pdf", size_bytes=500_000, resolution_dpi=300)
    rec = doc_svc.reconcile_against_checklist("user-1", "sess-1", checklist, intake_answers={})
    passport_item = next((i for i in rec["items"] if i["checklist_item_id"] == "valid_passport"), None)
    assert passport_item is not None
    assert passport_item["status"] == "complete"
    assert rec["completeness_pct"] > 0


def test_reconcile_completeness_zero_when_nothing_uploaded():
    doc_svc = DocumentIntakeService()
    intake = IntakeEngineService()
    checklist = intake.get_document_checklist("H-1B")
    rec = doc_svc.reconcile_against_checklist("user-2", "sess-2", checklist)
    assert rec["completeness_pct"] == 0
    assert all(i["status"] == "missing" for i in rec["items"])


def test_list_documents_filters_by_session():
    svc = DocumentIntakeService()
    svc.upload("user-1", "sess-A", "a.pdf", size_bytes=500_000, resolution_dpi=300)
    svc.upload("user-1", "sess-B", "b.pdf", size_bytes=500_000, resolution_dpi=300)
    a = svc.list_documents(applicant_id="user-1", session_id="sess-A")
    assert len(a) == 1
    assert a[0]["filename"] == "a.pdf"


def test_delete_document():
    svc = DocumentIntakeService()
    r = svc.upload("u", None, "passport.pdf", size_bytes=500_000, resolution_dpi=300)
    assert svc.delete_document(r["id"]) is True
    assert svc.get_document(r["id"]) is None
    assert svc.delete_document("nonexistent") is False


def test_supported_types_listing():
    types = DocumentIntakeService.list_supported_document_types()
    type_keys = {t["document_type"] for t in types}
    assert {"passport", "i20", "i94", "lca", "english_test", "bank_statement"} <= type_keys


def test_expired_document_validation_flag():
    """A document past its expiry date should be flagged as invalid."""
    svc = DocumentIntakeService()
    # Construct a record manually so we can plant an expired date
    r = svc.upload("u", None, "passport.pdf", size_bytes=500_000, resolution_dpi=300)
    # Force expiry to past
    r["extracted"]["expiry"] = "2000-01-01"
    validation = svc._validate(r)
    assert validation["valid"] is False
    assert any("expired" in i.lower() for i in validation["issues"])
