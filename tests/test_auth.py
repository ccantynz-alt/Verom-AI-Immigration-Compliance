"""Tests for authentication endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, auth_service


client = TestClient(app)

# Reset auth state between tests
def setup_function():
    auth_service._users.clear()
    auth_service._email_index.clear()
    auth_service._verification_docs.clear()


def _signup(role="applicant", email="test@example.com"):
    body = {
        "email": email,
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": role,
    }
    # Attorney requires extra fields
    if role == "attorney":
        body.update({
            "bar_number": "NY12345",
            "jurisdiction": "US",
            "specializations": "H-1B, Family-based",
        })
    return client.post("/api/auth/signup", json=body)


def _login(email="test@example.com", password="testpass123"):
    return client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- Signup tests ---

def test_signup_applicant():
    resp = _signup("applicant")
    assert resp.status_code == 201
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["role"] == "applicant"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["first_name"] == "Test"
    assert data["user"]["verification_status"] == "not_applicable"


def test_signup_attorney():
    resp = client.post("/api/auth/signup", json={
        "email": "attorney@example.com",
        "password": "testpass123",
        "first_name": "Jane",
        "last_name": "Esq",
        "role": "attorney",
        "bar_number": "NY12345",
        "jurisdiction": "US",
        "years_experience": 10,
        "specializations": "H-1B, Family-based",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["role"] == "attorney"
    assert data["user"]["bar_number"] == "NY12345"
    assert data["user"]["jurisdiction"] == "US"
    # Attorney starts as pending verification
    assert data["user"]["verification_status"] == "pending"


def test_signup_employer():
    resp = _signup("employer", "hr@company.com")
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "employer"
    assert resp.json()["user"]["verification_status"] == "not_applicable"


def test_signup_duplicate_email():
    _signup()
    resp = _signup()
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_signup_short_password():
    resp = client.post("/api/auth/signup", json={
        "email": "test@example.com",
        "password": "short",
        "first_name": "Test",
        "last_name": "User",
        "role": "applicant",
    })
    assert resp.status_code == 422


def test_signup_invalid_email():
    resp = client.post("/api/auth/signup", json={
        "email": "not-an-email",
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "applicant",
    })
    assert resp.status_code == 422


# --- Attorney signup validation ---

def test_attorney_signup_requires_bar_number():
    resp = client.post("/api/auth/signup", json={
        "email": "att@example.com",
        "password": "testpass123",
        "first_name": "No",
        "last_name": "Bar",
        "role": "attorney",
        "jurisdiction": "US",
        "specializations": "H-1B",
    })
    assert resp.status_code == 409 or resp.status_code == 422 or "bar number" in resp.json().get("detail", "").lower()


def test_attorney_signup_requires_jurisdiction():
    resp = client.post("/api/auth/signup", json={
        "email": "att@example.com",
        "password": "testpass123",
        "first_name": "No",
        "last_name": "Jurisdiction",
        "role": "attorney",
        "bar_number": "NY12345",
        "specializations": "H-1B",
    })
    assert resp.status_code in (409, 422) or "jurisdiction" in resp.json().get("detail", "").lower()


def test_attorney_signup_requires_specializations():
    resp = client.post("/api/auth/signup", json={
        "email": "att@example.com",
        "password": "testpass123",
        "first_name": "No",
        "last_name": "Spec",
        "role": "attorney",
        "bar_number": "NY12345",
        "jurisdiction": "US",
    })
    assert resp.status_code in (409, 422) or "specialization" in resp.json().get("detail", "").lower()


def test_attorney_signup_invalid_bar_number():
    resp = client.post("/api/auth/signup", json={
        "email": "att@example.com",
        "password": "testpass123",
        "first_name": "Bad",
        "last_name": "Bar",
        "role": "attorney",
        "bar_number": "x",  # Too short
        "jurisdiction": "US",
        "specializations": "H-1B",
    })
    assert resp.status_code in (409, 422) or "bar number" in resp.json().get("detail", "").lower()


def test_attorney_signup_invalid_jurisdiction():
    resp = client.post("/api/auth/signup", json={
        "email": "att@example.com",
        "password": "testpass123",
        "first_name": "Bad",
        "last_name": "Jur",
        "role": "attorney",
        "bar_number": "NY12345",
        "jurisdiction": "MARS",  # Not supported
        "specializations": "H-1B",
    })
    assert resp.status_code in (409, 422) or "jurisdiction" in resp.json().get("detail", "").lower()


# --- Login tests ---

def test_login_success():
    _signup()
    resp = _login()
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "test@example.com"


def test_login_wrong_password():
    _signup()
    resp = _login(password="wrongpass123")
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


def test_login_nonexistent_user():
    resp = _login(email="nobody@example.com")
    assert resp.status_code == 401


def test_login_case_insensitive_email():
    _signup(email="Test@Example.COM")
    resp = _login(email="test@example.com")
    assert resp.status_code == 200


# --- Protected endpoint tests ---

def test_me_with_valid_token():
    signup_resp = _signup()
    token = signup_resp.json()["access_token"]
    resp = client.get("/api/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_me_without_token():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token():
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401


def test_me_with_expired_format():
    resp = client.get("/api/auth/me", headers={"Authorization": "Basic dGVzdDp0ZXN0"})
    assert resp.status_code == 401
