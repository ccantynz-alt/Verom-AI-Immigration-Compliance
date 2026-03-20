"""Tests for the FastAPI endpoints."""

from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, service, _cases

client = TestClient(app)

SAMPLE_EMPLOYEE = {
    "id": "EMP100",
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@example.com",
    "country_of_citizenship": "Canada",
    "visa_type": "TN",
    "visa_status": "active",
    "visa_expiration_date": "2028-01-01",
    "i9_completed": True,
}


def setup_function():
    """Clear service state before each test function."""
    service._employees.clear()
    _cases.clear()


class _ResetMixin:
    def setup_method(self):
        service._employees.clear()
        _cases.clear()


class TestHealthEndpoint(_ResetMixin):
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestFrontend(_ResetMixin):
    def test_serve_index(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Verom" in resp.text


class TestEmployeeEndpoints(_ResetMixin):
    def test_create_employee(self):
        resp = client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        assert resp.status_code == 201
        assert resp.json()["id"] == "EMP100"

    def test_create_duplicate_employee(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        assert resp.status_code == 409

    def test_list_employees(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.get("/api/employees")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_employee(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.get("/api/employees/EMP100")
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Alice"

    def test_get_employee_not_found(self):
        resp = client.get("/api/employees/NONEXISTENT")
        assert resp.status_code == 404

    def test_delete_employee(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.delete("/api/employees/EMP100")
        assert resp.status_code == 204

    def test_delete_employee_not_found(self):
        resp = client.delete("/api/employees/NONEXISTENT")
        assert resp.status_code == 404


class TestComplianceEndpoints(_ResetMixin):
    def test_check_employee_compliance(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.post("/api/compliance/check/EMP100", json={})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_check_nonexistent_employee(self):
        resp = client.post("/api/compliance/check/NONEXISTENT", json={})
        assert resp.status_code == 404

    def test_generate_report(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        resp = client.post("/api/compliance/report", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_employees"] == 1
        assert "violations" in data
        assert "risk_summary" in data


class TestCaseEndpoints(_ResetMixin):
    def test_create_case(self):
        client.post("/api/employees", json=SAMPLE_EMPLOYEE)
        case = {
            "id": "CASE001",
            "employee_id": "EMP100",
            "case_type": "H-1B Extension",
            "status": "draft",
        }
        resp = client.post("/api/cases", json=case)
        assert resp.status_code == 201
        assert resp.json()["case_type"] == "H-1B Extension"

    def test_list_cases(self):
        case = {
            "id": "CASE002",
            "employee_id": "EMP100",
            "case_type": "TN Application",
            "status": "filed",
        }
        client.post("/api/cases", json=case)
        resp = client.get("/api/cases")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_case_status(self):
        case = {
            "id": "CASE003",
            "employee_id": "EMP100",
            "case_type": "L-1 Extension",
            "status": "draft",
        }
        client.post("/api/cases", json=case)
        resp = client.patch("/api/cases/CASE003/status", json={"status": "filed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "filed"

    def test_delete_case(self):
        case = {
            "id": "CASE004",
            "employee_id": "EMP100",
            "case_type": "EAD Renewal",
            "status": "pending",
        }
        client.post("/api/cases", json=case)
        resp = client.delete("/api/cases/CASE004")
        assert resp.status_code == 204
