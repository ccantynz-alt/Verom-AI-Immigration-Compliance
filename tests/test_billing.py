"""Tests for billing/Stripe endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, auth_service, billing_service


client = TestClient(app)


def setup_function():
    auth_service._users.clear()
    auth_service._email_index.clear()
    auth_service._verification_docs.clear()
    billing_service._subscriptions.clear()
    billing_service._connect_accounts.clear()


def _create_user(role="applicant", email="test@example.com"):
    body = {
        "email": email,
        "password": "testpass123",
        "first_name": "Test",
        "last_name": "User",
        "role": role,
    }
    if role == "attorney":
        body.update({
            "bar_number": "NY12345",
            "jurisdiction": "US",
            "specializations": "H-1B, Family-based",
        })
    resp = client.post("/api/auth/signup", json=body)
    return resp.json()


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Plans ---

def test_get_all_plans():
    resp = client.get("/api/billing/plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) == 6  # 3 attorney + 3 employer


def test_get_attorney_plans():
    resp = client.get("/api/billing/plans?role=attorney")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) == 3
    assert all(p["tier"].startswith("attorney") for p in plans)


def test_get_employer_plans():
    resp = client.get("/api/billing/plans?role=employer")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) == 3
    assert all(p["tier"].startswith("employer") for p in plans)


# --- Checkout ---

def test_create_checkout_session():
    data = _create_user("attorney", "att@example.com")
    token = data["access_token"]
    resp = client.post("/api/billing/checkout", json={
        "plan": "attorney_solo",
        "success_url": "/attorney?billing=success",
        "cancel_url": "/attorney?billing=cancel",
    }, headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"].startswith("cs_")
    assert body["checkout_url"]


def test_checkout_requires_auth():
    resp = client.post("/api/billing/checkout", json={"plan": "attorney_solo"})
    assert resp.status_code == 401


# --- Subscription ---

def test_get_subscription_none():
    data = _create_user()
    resp = client.get("/api/billing/subscription", headers=_auth_headers(data["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["subscription"] is None


def test_get_subscription_after_checkout():
    data = _create_user("employer", "emp@example.com")
    token = data["access_token"]
    client.post("/api/billing/checkout", json={
        "plan": "employer_starter",
    }, headers=_auth_headers(token))
    resp = client.get("/api/billing/subscription", headers=_auth_headers(token))
    assert resp.status_code == 200
    sub = resp.json()["subscription"]
    assert sub is not None
    assert sub["plan"] == "employer_starter"
    assert sub["status"] == "trialing"


# --- Connect (Attorney Only) ---

def test_connect_onboard_attorney():
    data = _create_user("attorney", "att2@example.com")
    token = data["access_token"]
    resp = client.post("/api/billing/connect/onboard", json={
        "return_url": "/attorney",
        "refresh_url": "/attorney",
    }, headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_id"].startswith("acct_")


def test_connect_onboard_forbidden_for_applicant():
    data = _create_user("applicant", "app@example.com")
    token = data["access_token"]
    resp = client.post("/api/billing/connect/onboard", json={}, headers=_auth_headers(token))
    assert resp.status_code == 403


def test_connect_status():
    data = _create_user("attorney", "att3@example.com")
    token = data["access_token"]
    # Before onboarding
    resp = client.get("/api/billing/connect/status", headers=_auth_headers(token))
    assert resp.json()["connected"] is False
    # After onboarding
    client.post("/api/billing/connect/onboard", json={}, headers=_auth_headers(token))
    resp = client.get("/api/billing/connect/status", headers=_auth_headers(token))
    assert resp.json()["connected"] is True


# --- Payment Intent ---

def test_create_payment_intent():
    data = _create_user("applicant", "pay@example.com")
    token = data["access_token"]
    resp = client.post("/api/billing/payment-intent", json={
        "attorney_user_id": "some-attorney-id",
        "case_id": "case-123",
        "description": "H-1B consultation",
    }, headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_intent_id"].startswith("pi_")
    assert body["client_secret"]
