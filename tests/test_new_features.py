"""Tests for new features: documents, audit, PAF, regulatory, global, HRIS."""

from datetime import date

from fastapi.testclient import TestClient

from immigration_compliance.api.app import (
    app,
    service,
    _cases,
    doc_service,
    audit_trail,
    paf_service,
    global_service,
    hris_service,
)

client = TestClient(app)

SAMPLE_EMPLOYEE = {
    "id": "EMP200",
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "country_of_citizenship": "India",
    "visa_type": "H-1B",
    "visa_status": "active",
    "visa_expiration_date": "2027-01-01",
    "i9_completed": True,
    "actual_wage": 100000,
    "prevailing_wage": 90000,
}


class _Reset:
    def setup_method(self):
        service._employees.clear()
        _cases.clear()
        doc_service._documents.clear()
        audit_trail._entries.clear()
        paf_service._pafs.clear()
        global_service._assignments.clear()
        global_service._travel.clear()
        hris_service._integrations.clear()
        hris_service._sync_records.clear()


# =============================================
# Document tests
# =============================================

class TestDocumentEndpoints(_Reset):
    def test_create_document(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        doc = {
            "id": "DOC001",
            "employee_id": "EMP200",
            "category": "passport",
            "title": "Indian Passport",
            "file_name": "passport.pdf",
        }
        resp = client.post("/api/documents", json=doc)
        assert resp.status_code == 201
        assert resp.json()["title"] == "Indian Passport"

    def test_list_documents(self):
        doc = {
            "id": "DOC002",
            "employee_id": "EMP200",
            "category": "visa",
            "title": "H-1B Visa Stamp",
            "file_name": "visa.pdf",
        }
        client.post("/api/documents", json=doc)
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_documents_by_employee(self):
        client.post("/api/documents", json={"id": "DOC003", "employee_id": "EMP200", "category": "passport", "title": "Doc", "file_name": "a.pdf"})
        client.post("/api/documents", json={"id": "DOC004", "employee_id": "OTHER", "category": "passport", "title": "Doc2", "file_name": "b.pdf"})
        resp = client.get("/api/documents?employee_id=EMP200")
        assert len(resp.json()) == 1

    def test_delete_document(self):
        client.post("/api/documents", json={"id": "DOC005", "employee_id": "EMP200", "category": "visa", "title": "Test", "file_name": "t.pdf"})
        resp = client.delete("/api/documents/DOC005")
        assert resp.status_code == 204

    def test_delete_document_not_found(self):
        resp = client.delete("/api/documents/NONEXISTENT")
        assert resp.status_code == 404


# =============================================
# Audit Trail tests
# =============================================

class TestAuditTrailEndpoints(_Reset):
    def test_audit_trail_logs_on_employee_create(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.get("/api/audit-trail")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        assert entries[0]["action"] == "employee_created"

    def test_audit_stats(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.get("/api/audit-trail/stats")
        assert resp.status_code == 200
        assert resp.json()["total_entries"] >= 1


# =============================================
# ICE Audit Simulation tests
# =============================================

class TestICEAuditEndpoints(_Reset):
    def test_ice_audit_empty(self):
        resp = client.post("/api/audit/ice-simulation", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_employees_audited"] == 0
        assert data["overall_grade"] == "N/A"

    def test_ice_audit_with_employees(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.post("/api/audit/ice-simulation", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_employees_audited"] == 1

    def test_ice_audit_finds_missing_i9(self):
        emp = dict(SAMPLE_EMPLOYEE, id="EMP_NOI9", i9_completed=False)
        client.post("/api/employees", json=emp)
        resp = client.post("/api/audit/ice-simulation", json={})
        data = resp.json()
        assert any(f["finding_type"] == "missing_i9" for f in data["findings"])


# =============================================
# PAF tests
# =============================================

class TestPAFEndpoints(_Reset):
    def test_create_paf(self):
        paf = {
            "id": "PAF001",
            "employee_id": "EMP200",
            "lca_number": "LCA-001",
            "job_title": "Software Engineer",
        }
        resp = client.post("/api/pafs", json=paf)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "incomplete"
        assert len(data["documents"]) == 5  # auto-created placeholders

    def test_list_pafs(self):
        client.post("/api/pafs", json={"id": "PAF002", "employee_id": "EMP200"})
        resp = client.get("/api/pafs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_paf_document(self):
        client.post("/api/pafs", json={"id": "PAF003", "employee_id": "EMP200"})
        resp = client.patch("/api/pafs/PAF003/document", json={
            "document_type": "lca_certified",
            "is_present": True,
            "title": "Certified LCA",
        })
        assert resp.status_code == 200
        docs = resp.json()["documents"]
        lca = next(d for d in docs if d["document_type"] == "lca_certified")
        assert lca["is_present"] is True

    def test_delete_paf(self):
        client.post("/api/pafs", json={"id": "PAF004", "employee_id": "EMP200"})
        resp = client.delete("/api/pafs/PAF004")
        assert resp.status_code == 204


# =============================================
# Regulatory Intelligence tests
# =============================================

class TestRegulatoryEndpoints(_Reset):
    def test_get_feed(self):
        resp = client.get("/api/regulatory/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["updates"]) > 0
        assert len(data["processing_times"]) > 0
        assert len(data["visa_bulletin"]) > 0

    def test_get_updates(self):
        resp = client.get("/api/regulatory/updates")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_get_updates_filtered(self):
        resp = client.get("/api/regulatory/updates?impact_level=high")
        assert resp.status_code == 200
        for u in resp.json():
            assert u["impact_level"] == "high"

    def test_get_processing_times(self):
        resp = client.get("/api/regulatory/processing-times")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_get_visa_bulletin(self):
        resp = client.get("/api/regulatory/visa-bulletin")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_get_visa_bulletin_filtered(self):
        resp = client.get("/api/regulatory/visa-bulletin?category=EB-2")
        assert resp.status_code == 200
        for e in resp.json():
            assert e["category"] == "EB-2"


# =============================================
# Global Immigration tests
# =============================================

class TestGlobalEndpoints(_Reset):
    def test_get_countries(self):
        resp = client.get("/api/global/countries")
        assert resp.status_code == 200
        countries = resp.json()
        assert len(countries) > 10
        names = [c["name"] for c in countries]
        assert "United States" in names

    def test_get_country(self):
        resp = client.get("/api/global/countries/US")
        assert resp.status_code == 200
        assert resp.json()["name"] == "United States"

    def test_get_country_not_found(self):
        resp = client.get("/api/global/countries/ZZ")
        assert resp.status_code == 404

    def test_create_assignment(self):
        assignment = {
            "id": "ASSIGN001",
            "employee_id": "EMP200",
            "country_code": "GB",
            "country_name": "United Kingdom",
            "permit_type": "Skilled Worker",
            "permit_status": "active",
        }
        resp = client.post("/api/global/assignments", json=assignment)
        assert resp.status_code == 201

    def test_list_assignments(self):
        client.post("/api/global/assignments", json={"id": "A1", "employee_id": "EMP200", "country_code": "GB", "country_name": "UK"})
        resp = client.get("/api/global/assignments")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_add_travel(self):
        travel = {
            "id": "T1",
            "employee_id": "EMP200",
            "country_code": "GB",
            "country_name": "United Kingdom",
            "entry_date": "2026-01-01",
            "exit_date": "2026-01-10",
            "purpose": "Client meeting",
        }
        resp = client.post("/api/global/travel", json=travel)
        assert resp.status_code == 201
        assert resp.json()["days_counted"] == 10

    def test_get_global_compliance(self):
        resp = client.get("/api/global/compliance/EMP200")
        assert resp.status_code == 200
        assert resp.json()["employee_id"] == "EMP200"


# =============================================
# HRIS Integration tests
# =============================================

class TestHRISEndpoints(_Reset):
    def test_get_providers(self):
        resp = client.get("/api/hris/providers")
        assert resp.status_code == 200
        providers = resp.json()
        names = [p["id"] for p in providers]
        assert "workday" in names
        assert "adp" in names

    def test_create_integration(self):
        integration = {
            "id": "INT001",
            "provider": "workday",
            "name": "Our Workday",
        }
        resp = client.post("/api/hris/integrations", json=integration)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["field_mappings"]) > 0  # auto-populated

    def test_list_integrations(self):
        client.post("/api/hris/integrations", json={"id": "INT002", "provider": "adp", "name": "ADP"})
        resp = client.get("/api/hris/integrations")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_run_sync(self):
        client.post("/api/hris/integrations", json={"id": "INT003", "provider": "bamboohr", "name": "BHR", "employee_count": 50})
        resp = client.post("/api/hris/integrations/INT003/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["records_processed"] == 50

    def test_delete_integration(self):
        client.post("/api/hris/integrations", json={"id": "INT004", "provider": "gusto", "name": "Gusto"})
        resp = client.delete("/api/hris/integrations/INT004")
        assert resp.status_code == 204

    def test_get_default_mappings(self):
        resp = client.get("/api/hris/mappings/workday")
        assert resp.status_code == 200
        assert len(resp.json()) > 0
