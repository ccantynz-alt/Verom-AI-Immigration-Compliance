"""Tests for sticky features: consultations, interview prep, vault, receipts, travel advisory."""

from __future__ import annotations

from fastapi.testclient import TestClient

from immigration_compliance.api.app import (
    app,
    auth_service,
    consultation_service,
    vault_service,
)


client = TestClient(app)


def setup_function():
    auth_service._users.clear()
    auth_service._email_index.clear()
    auth_service._verification_docs.clear()
    consultation_service._consultations.clear()
    consultation_service._mock_sessions.clear()
    vault_service._documents.clear()
    vault_service._receipts.clear()


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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# =============================================
# Video Consultation Tests
# =============================================

def test_request_consultation():
    applicant = _create_user("applicant", "app@test.com")
    attorney = _create_user("attorney", "att@test.com")
    resp = client.post("/api/consultations", json={
        "attorney_id": attorney["user"]["id"],
        "consultation_type": "initial_consultation",
        "preferred_date": "2026-04-01",
        "preferred_time": "14:00",
        "duration_minutes": 30,
        "notes": "Need help with H-1B application",
    }, headers=_auth(applicant["access_token"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("consult_")
    assert data["room_id"].startswith("room_")
    assert data["room_url"].startswith("/consultation/room/")
    assert data["status"] == "scheduled"
    assert data["consultation_type"] == "initial_consultation"


def test_list_consultations_applicant():
    applicant = _create_user("applicant", "app@test.com")
    attorney = _create_user("attorney", "att@test.com")
    # Create 2 consultations
    for _ in range(2):
        client.post("/api/consultations", json={
            "attorney_id": attorney["user"]["id"],
            "consultation_type": "initial_consultation",
        }, headers=_auth(applicant["access_token"]))
    resp = client.get("/api/consultations", headers=_auth(applicant["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_consultations_attorney():
    applicant = _create_user("applicant", "app@test.com")
    attorney = _create_user("attorney", "att@test.com")
    client.post("/api/consultations", json={
        "attorney_id": attorney["user"]["id"],
    }, headers=_auth(applicant["access_token"]))
    resp = client.get("/api/consultations", headers=_auth(attorney["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_consultation_detail():
    applicant = _create_user("applicant", "app@test.com")
    attorney = _create_user("attorney", "att@test.com")
    create_resp = client.post("/api/consultations", json={
        "attorney_id": attorney["user"]["id"],
    }, headers=_auth(applicant["access_token"]))
    cid = create_resp.json()["id"]
    # Applicant can see it
    resp = client.get(f"/api/consultations/{cid}", headers=_auth(applicant["access_token"]))
    assert resp.status_code == 200
    # Attorney can see it
    resp = client.get(f"/api/consultations/{cid}", headers=_auth(attorney["access_token"]))
    assert resp.status_code == 200


def test_consultation_access_denied():
    applicant = _create_user("applicant", "app@test.com")
    attorney = _create_user("attorney", "att@test.com")
    other = _create_user("applicant", "other@test.com")
    create_resp = client.post("/api/consultations", json={
        "attorney_id": attorney["user"]["id"],
    }, headers=_auth(applicant["access_token"]))
    cid = create_resp.json()["id"]
    resp = client.get(f"/api/consultations/{cid}", headers=_auth(other["access_token"]))
    assert resp.status_code == 403


def test_get_attorney_slots():
    attorney = _create_user("attorney", "att@test.com")
    resp = client.get(
        f"/api/consultations/slots/{attorney['user']['id']}?date=2026-04-01",
        headers=_auth(attorney["access_token"]),
    )
    assert resp.status_code == 200
    slots = resp.json()
    assert len(slots) > 0
    assert "time" in slots[0]


# =============================================
# Interview Prep Tests
# =============================================

def test_get_interview_types():
    resp = client.get("/api/interview-prep/types")
    assert resp.status_code == 200
    types = resp.json()
    assert len(types) >= 5
    labels = [t["type"] for t in types]
    assert "uscis_marriage_interview" in labels
    assert "consular_interview" in labels


def test_start_mock_interview():
    user = _create_user()
    resp = client.post(
        "/api/interview-prep/start?interview_type=uscis_marriage_interview",
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("mock_")
    assert len(data["questions"]) >= 5
    assert data["completed"] is False
    # Check question structure
    q = data["questions"][0]
    assert "question" in q
    assert "tip" in q
    assert "category" in q


def test_start_naturalization_interview():
    user = _create_user()
    resp = client.post(
        "/api/interview-prep/start?interview_type=uscis_naturalization",
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) >= 5


def test_start_consular_interview():
    user = _create_user()
    resp = client.post(
        "/api/interview-prep/start?interview_type=consular_interview",
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) >= 3


def test_complete_mock_interview():
    user = _create_user()
    start = client.post(
        "/api/interview-prep/start?interview_type=uscis_marriage_interview",
        headers=_auth(user["access_token"]),
    )
    sid = start.json()["id"]
    resp = client.post(
        f"/api/interview-prep/{sid}/complete?score=85",
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    assert resp.json()["score"] == 85


def test_list_mock_sessions():
    user = _create_user()
    client.post(
        "/api/interview-prep/start?interview_type=uscis_marriage_interview",
        headers=_auth(user["access_token"]),
    )
    client.post(
        "/api/interview-prep/start?interview_type=consular_interview",
        headers=_auth(user["access_token"]),
    )
    resp = client.get("/api/interview-prep/history/me", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# =============================================
# Document Vault Tests
# =============================================

def test_upload_vault_document():
    user = _create_user()
    resp = client.post("/api/vault/documents", json={
        "user_id": "",
        "filename": "passport.pdf",
        "document_type": "passport",
        "country": "US",
        "expiration_date": "2028-06-15",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("vault_")
    assert data["user_id"] == user["user"]["id"]
    assert data["filename"] == "passport.pdf"


def test_list_vault_documents():
    user = _create_user()
    for name in ["passport.pdf", "visa.pdf", "i94.pdf"]:
        client.post("/api/vault/documents", json={
            "user_id": "",
            "filename": name,
            "document_type": name.split(".")[0],
        }, headers=_auth(user["access_token"]))
    resp = client.get("/api/vault/documents", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_vault_isolation():
    """Each user can only see their own documents."""
    user1 = _create_user("applicant", "u1@test.com")
    user2 = _create_user("applicant", "u2@test.com")
    client.post("/api/vault/documents", json={
        "user_id": "", "filename": "u1_passport.pdf", "document_type": "passport",
    }, headers=_auth(user1["access_token"]))
    client.post("/api/vault/documents", json={
        "user_id": "", "filename": "u2_passport.pdf", "document_type": "passport",
    }, headers=_auth(user2["access_token"]))
    resp1 = client.get("/api/vault/documents", headers=_auth(user1["access_token"]))
    resp2 = client.get("/api/vault/documents", headers=_auth(user2["access_token"]))
    assert len(resp1.json()) == 1
    assert resp1.json()[0]["filename"] == "u1_passport.pdf"
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["filename"] == "u2_passport.pdf"


def test_delete_vault_document():
    user = _create_user()
    create = client.post("/api/vault/documents", json={
        "user_id": "", "filename": "temp.pdf", "document_type": "other",
    }, headers=_auth(user["access_token"]))
    doc_id = create.json()["id"]
    resp = client.delete(f"/api/vault/documents/{doc_id}", headers=_auth(user["access_token"]))
    assert resp.status_code == 204


def test_delete_vault_document_other_user_blocked():
    user1 = _create_user("applicant", "u1@test.com")
    user2 = _create_user("applicant", "u2@test.com")
    create = client.post("/api/vault/documents", json={
        "user_id": "", "filename": "secret.pdf", "document_type": "passport",
    }, headers=_auth(user1["access_token"]))
    doc_id = create.json()["id"]
    resp = client.delete(f"/api/vault/documents/{doc_id}", headers=_auth(user2["access_token"]))
    assert resp.status_code == 403


def test_expiration_alerts():
    user = _create_user()
    # Expired document
    client.post("/api/vault/documents", json={
        "user_id": "", "filename": "old_ead.pdf",
        "document_type": "ead", "expiration_date": "2025-01-01",
    }, headers=_auth(user["access_token"]))
    # Expiring soon
    client.post("/api/vault/documents", json={
        "user_id": "", "filename": "passport.pdf",
        "document_type": "passport", "expiration_date": "2026-04-01",
    }, headers=_auth(user["access_token"]))
    # Far future (no alert)
    client.post("/api/vault/documents", json={
        "user_id": "", "filename": "new_visa.pdf",
        "document_type": "visa", "expiration_date": "2029-01-01",
    }, headers=_auth(user["access_token"]))
    resp = client.get("/api/vault/alerts", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 2  # expired + expiring soon
    assert alerts[0]["urgency"] == "expired"


# =============================================
# Receipt Tracker Tests
# =============================================

def test_add_receipt():
    user = _create_user()
    resp = client.post("/api/receipts", json={
        "user_id": "",
        "receipt_number": "EAC2190012345",
        "form_type": "I-765",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("rcpt_")
    assert data["case_status"] == "Case Was Received"
    assert len(data["status_history"]) == 1


def test_add_receipt_invalid_format():
    user = _create_user()
    resp = client.post("/api/receipts", json={
        "user_id": "",
        "receipt_number": "invalid-123",
        "form_type": "I-765",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 422
    assert "receipt number" in resp.json()["detail"].lower()


def test_list_receipts():
    user = _create_user()
    for rn in ["EAC2190012345", "IOE0912345678"]:
        client.post("/api/receipts", json={
            "user_id": "", "receipt_number": rn, "form_type": "I-765",
        }, headers=_auth(user["access_token"]))
    resp = client.get("/api/receipts", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_check_receipt_status():
    user = _create_user()
    create = client.post("/api/receipts", json={
        "user_id": "", "receipt_number": "EAC2190012345", "form_type": "I-130",
    }, headers=_auth(user["access_token"]))
    tid = create.json()["id"]
    resp = client.post(f"/api/receipts/{tid}/check", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["last_checked"]


def test_delete_receipt():
    user = _create_user()
    create = client.post("/api/receipts", json={
        "user_id": "", "receipt_number": "EAC2190012345", "form_type": "I-765",
    }, headers=_auth(user["access_token"]))
    tid = create.json()["id"]
    resp = client.delete(f"/api/receipts/{tid}", headers=_auth(user["access_token"]))
    assert resp.status_code == 204


# =============================================
# Travel Advisory Tests
# =============================================

def test_travel_safe_no_pending():
    user = _create_user()
    resp = client.post("/api/travel-advisory", json={
        "destination_country": "UK",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_travel"] is True
    assert data["risk_level"] == "safe"


def test_travel_risky_i485():
    user = _create_user()
    resp = client.post("/api/travel-advisory?pending_forms=I-485", json={
        "destination_country": "India",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_travel"] is False
    assert data["risk_level"] == "risky"
    assert any("I-485" in w for w in data["warnings"])


def test_travel_i485_with_advance_parole():
    user = _create_user()
    resp = client.post("/api/travel-advisory?pending_forms=I-485&has_advance_parole=true", json={
        "destination_country": "India",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_travel"] is True
    assert data["risk_level"] == "caution"


def test_travel_blocked_asylum():
    user = _create_user()
    resp = client.post("/api/travel-advisory?pending_forms=I-589", json={
        "destination_country": "Honduras",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_travel"] is False
    assert data["risk_level"] == "blocked"


def test_travel_multiple_pending():
    user = _create_user()
    resp = client.post("/api/travel-advisory?pending_forms=I-485,I-765,N-400", json={
        "destination_country": "Canada",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    # I-485 is the worst, so overall should be risky
    assert data["risk_level"] == "risky"
    assert len(data["warnings"]) >= 3
