"""Tests for Smart Form Auto-Population — single intake → all forms with provenance."""

from immigration_compliance.services.form_population_service import (
    FormPopulationService,
    FORM_SCHEMAS,
)


def _make_extracted():
    return [
        {
            "document_type": "passport",
            "uploaded_at": "2026-01-01",
            "extracted": {
                "full_name": "CHEN, WEI",
                "dob": "1992-05-15",
                "passport_number": "X12345678",
                "nationality": "CHINA",
                "expiry": "2030-12-31",
            },
        },
        {
            "document_type": "lca",
            "uploaded_at": "2026-01-02",
            "extracted": {
                "lca_number": "I-200-12345",
                "wage_level": "III",
                "wage_rate": 145000,
            },
        },
    ]


def _make_intake():
    return {
        "petitioner_name": "Acme Corp",
        "petitioner_fein": "12-3456789",
        "position_title": "Software Engineer",
        "employment_start_date": "2026-10-01",
        "employment_end_date": "2029-09-30",
        "current_status_in_us": "F-1_OPT",
    }


def test_form_registry_covers_core_forms():
    assert {"G-28", "I-129", "I-130", "I-485", "I-765", "I-131", "DS-160"} <= set(FORM_SCHEMAS.keys())


def test_list_forms_filter_drops_non_applicable():
    """list_forms filters out forms that explicitly declare applicable_visas
    when the visa isn't in the list. Forms without applicable_visas are kept
    (they're general-purpose like G-28, DS-160)."""
    # I-129 declares applicable_visas — H-1B is included
    h1b_forms = {f["form_id"] for f in FormPopulationService.list_forms(visa_type="H-1B")}
    assert "I-129" in h1b_forms
    # F-1 isn't in I-129's applicable_visas → excluded
    f1_forms = {f["form_id"] for f in FormPopulationService.list_forms(visa_type="F-1")}
    assert "I-129" not in f1_forms


def test_recommendations_for_h1b():
    recs = FormPopulationService.list_recommended_forms_for_visa("H-1B")
    assert "G-28" in recs and "I-129" in recs and "DS-160" in recs


def test_populate_i129_extracts_passport_fields():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    name_field = next(f for f in rec["fields"] if f["field_id"] == "beneficiary_name")
    assert name_field["value"] == "CHEN, WEI"
    assert name_field["source"] == "extracted.passport.full_name"
    assert name_field["filled"] is True


def test_populate_pulls_intake_when_no_doc():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=[])
    pet_field = next(f for f in rec["fields"] if f["field_id"] == "petitioner_legal_name")
    assert pet_field["value"] == "Acme Corp"
    assert pet_field["source"] == "intake.petitioner_name"


def test_populate_falls_back_to_intake_for_lca_wage():
    fps = FormPopulationService()
    intake = {**_make_intake(), "wage_offered": 150000}
    rec = fps.populate("I-129", "user-1", intake_answers=intake, extracted_documents=[])
    wage_field = next(f for f in rec["fields"] if f["field_id"] == "wage_offered")
    assert wage_field["value"] == 150000
    assert wage_field["source"] == "intake.wage_offered"


def test_empty_required_field_filled_with_na():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers={}, extracted_documents=[])
    # Required field that has no source data
    pet_name = next(f for f in rec["fields"] if f["field_id"] == "petitioner_legal_name")
    assert pet_name["value"] == "N/A"
    assert pet_name["filled"] is False


def test_completeness_pct_reflects_required_fields():
    fps = FormPopulationService()
    rec_full = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    rec_empty = fps.populate("I-129", "user-2", intake_answers={}, extracted_documents=[])
    assert rec_full["completeness_pct"] > rec_empty["completeness_pct"]


def test_bundle_populates_all_recommended_forms():
    fps = FormPopulationService()
    bundle = fps.populate_bundle(
        applicant_id="user-1",
        visa_type="H-1B",
        intake_answers=_make_intake(),
        extracted_documents=_make_extracted(),
    )
    form_ids = [r["form_id"] for r in bundle["forms"]]
    assert "G-28" in form_ids and "I-129" in form_ids and "DS-160" in form_ids


def test_field_update_records_override():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    updated = fps.update_field(rec["id"], "position_title", "Senior Software Engineer", edited_by="atty-1")
    field = next(f for f in updated["fields"] if f["field_id"] == "position_title")
    assert field["value"] == "Senior Software Engineer"
    assert field["manually_overridden"] is True
    assert field["source"] == "manual.atty-1"


def test_provenance_log_captures_auto_and_manual():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    fps.update_field(rec["id"], "position_title", "Senior Engineer")
    log = fps.get_provenance(record_id=rec["id"], field_id="position_title")
    kinds = [p["kind"] for p in log]
    assert "auto" in kinds and "manual_override" in kinds


def test_unknown_form_raises():
    fps = FormPopulationService()
    try:
        fps.populate("FAKE-FORM", "user-1", intake_answers={}, extracted_documents=[])
        assert False
    except ValueError:
        pass


def test_unknown_field_update_raises():
    fps = FormPopulationService()
    rec = fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    try:
        fps.update_field(rec["id"], "not_a_field", "x")
        assert False
    except ValueError:
        pass


def test_list_records_filtered():
    fps = FormPopulationService()
    fps.populate("I-129", "user-1", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    fps.populate("I-130", "user-1", intake_answers={"petitioner_full_name": "John Doe"}, extracted_documents=[])
    fps.populate("I-129", "user-2", intake_answers=_make_intake(), extracted_documents=_make_extracted())
    user_1_records = fps.list_records(applicant_id="user-1")
    assert len(user_1_records) == 2
    i129_records = fps.list_records(form_id="I-129")
    assert len(i129_records) == 2


def test_computed_today_filled():
    fps = FormPopulationService()
    rec = fps.populate("G-28", "user-1", intake_answers={}, extracted_documents=[])
    eng_field = next(f for f in rec["fields"] if f["field_id"] == "engagement_date")
    assert eng_field["filled"] is True
    assert eng_field["source"] == "computed.today"
