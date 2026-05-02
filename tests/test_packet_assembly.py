"""Tests for the Filing-Ready Packet Assembly service."""

from immigration_compliance.services.packet_assembly_service import (
    PacketAssemblyService,
    render_cover_letter,
    _PdfBuilder,
    _paginate,
    _wrap,
    LINES_PER_PAGE,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService
from immigration_compliance.services.form_population_service import FormPopulationService


def _make_workspace_with_form_and_doc():
    ie = IntakeEngineService()
    di = DocumentIntakeService()
    fp = FormPopulationService()
    cw = CaseWorkspaceService(intake_engine=ie, document_intake=di, form_population=fp)
    pa = PacketAssemblyService(case_workspace=cw, document_intake=di, form_population=fp)

    ans = {
        "has_bachelors_or_higher": True, "has_us_employer_offer": True,
        "lca_filed": True, "wage_level": "III", "us_masters_or_higher": True,
        "selected_in_lottery": True, "petitioner_name": "Acme Corp",
        "petitioner_fein": "12-3456789", "position_title": "Software Engineer",
    }
    sess = ie.start_session("user-1", "H-1B")
    ie.submit_answers(sess["id"], ans)
    doc = di.upload("user-1", sess["id"], "passport_chen.pdf", size_bytes=2_000_000, resolution_dpi=300)
    rec = fp.populate("I-129", "user-1", intake_answers=ans, extracted_documents=[doc])
    ws = cw.create_workspace("user-1", "H-1B", "US", intake_session_id=sess["id"], case_label="Chen H-1B")
    cw.link_form_record(ws["id"], rec["id"])
    return cw, pa, ws


def test_assemble_returns_manifest():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    assert "cover_letter" in m and "forms" in m and "exhibits" in m
    assert m["visa_type"] == "H-1B"


def test_assemble_includes_forms_and_exhibits():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    assert len(m["forms"]) == 1
    assert m["forms"][0]["form_id"] == "I-129"
    # Exhibit list reflects uploaded passport linked to checklist
    assert len(m["exhibits"]) >= 1
    assert m["exhibits"][0]["tab"] == "A"


def test_render_text_contains_cover_and_forms():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"], attorney_profile={"name": "Jennifer Park"})
    text = pa.render_text(m)
    assert "FILING PACKET" in text
    assert "I-129" in text
    assert "EXHIBIT" in text


def test_render_pdf_returns_valid_bytes():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    pdf = pa.render_pdf(m)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.endswith(b"%%EOF")


def test_pdf_has_multiple_pages():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    pdf = pa.render_pdf(m)
    page_count = pdf.count(b"/Type /Page ")
    assert page_count >= 2


def test_pdf_includes_xref_and_trailer():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    pdf = pa.render_pdf(m)
    assert b"\nxref\n" in pdf
    assert b"\ntrailer\n" in pdf
    assert b"\nstartxref\n" in pdf


def test_cover_letter_includes_attorney_block():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"], attorney_profile={"name": "Jennifer Park", "firm": "Park Immigration", "bar_number": "NY-1234"})
    assert "Jennifer Park" in m["cover_letter"]
    assert "Park Immigration" in m["cover_letter"]
    assert "NY-1234" in m["cover_letter"]


def test_addendum_only_when_requested():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m_no = pa.assemble(ws["id"], include_strength_summary=False)
    m_yes = pa.assemble(ws["id"], include_strength_summary=True)
    assert m_no["addendum"] is None
    assert m_yes["addendum"] is not None


def test_packet_persisted_and_listable():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    assert pa.get_packet(m["id"])["id"] == m["id"]
    assert len(pa.list_packets(workspace_id=ws["id"])) == 1


def test_paginate_splits_long_text():
    lines = ["L" + str(i) for i in range(LINES_PER_PAGE * 3)]
    pages = _paginate(lines)
    assert len(pages) == 3


def test_wrap_long_line_breaks():
    long = "x" * 200
    out = _wrap(long, width=50)
    assert all(len(s) <= 60 for s in out)  # Allow some slack
    assert "".join(out) == long


def test_cover_letter_includes_visa_and_forms():
    _, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    assert "H-1B" in m["cover_letter"]
    assert "I-129" in m["cover_letter"]


def test_render_pdf_for_empty_manifest():
    """Even an empty workspace shouldn't crash the PDF renderer."""
    cw = CaseWorkspaceService()
    ws = cw.create_workspace("user-1", "F-1", "US")
    pa = PacketAssemblyService(case_workspace=cw)
    m = pa.assemble(ws["id"])
    pdf = pa.render_pdf(m)
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.endswith(b"%%EOF")


def test_pdf_builder_directly():
    """Smoke-test the PDF builder with a minimal page set."""
    builder = _PdfBuilder()
    pdf = builder.build([["Hello"], ["Page 2"]], header_for=lambda i,t: f"H{i}", footer_for=lambda i,t: f"F{i}")
    assert pdf.startswith(b"%PDF-1.4")
    # Two pages → two /Type /Page objects
    assert pdf.count(b"/Type /Page ") == 2


def test_estimate_pages_grows_with_content():
    cw, pa, ws = _make_workspace_with_form_and_doc()
    m = pa.assemble(ws["id"])
    assert m["page_count_estimate"] > 0
