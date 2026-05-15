"""Tests for the Voxlen voice dictation integration."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, auth_service, voxlen_service
from immigration_compliance.services.voxlen_service import (
    ExportFormat,
    LLMProvider,
    STTProvider,
    VoxlenService,
    WritingStyle,
)


client = TestClient(app)


def setup_function() -> None:
    voxlen_service._sessions.clear()
    voxlen_service._api_keys.clear()
    auth_service._users.clear()
    auth_service._email_index.clear()
    auth_service._verification_docs.clear()


def _auth(email: str = "attorney@test.com", role: str = "attorney") -> dict:
    body = {
        "email": email,
        "password": "testpass123",
        "first_name": "Vox",
        "last_name": "Len",
        "role": role,
    }
    if role == "attorney":
        body.update({"bar_number": "NY12345", "jurisdiction": "US", "specializations": "H-1B"})
    resp = client.post("/api/auth/signup", json=body)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Voice command engine --------------------------------------------------

def test_voice_commands_insert_punctuation():
    svc = VoxlenService()
    result, actions = svc._apply_voice_commands("hello comma world period", "")
    assert "hello," in result["new_transcript"]
    assert result["new_transcript"].rstrip().endswith(".")
    assert "comma" in actions and "period" in actions


def test_voice_command_new_paragraph_wins_over_new_line():
    svc = VoxlenService()
    result, actions = svc._apply_voice_commands("new paragraph", "foo")
    assert "\n\n" in result["new_transcript"]
    assert actions == ["new paragraph"]


def test_voice_command_delete_that_removes_last_word():
    svc = VoxlenService()
    result, actions = svc._apply_voice_commands("delete that", "this is wrong")
    assert result["new_transcript"].strip() == "this is"
    assert "delete that" in actions


def test_voice_command_capitalize_that():
    svc = VoxlenService()
    result, _ = svc._apply_voice_commands("capitalize that", "petitioner")
    assert "Petitioner" in result["new_transcript"]


def test_voice_command_legal_shortcuts():
    svc = VoxlenService()
    result, actions = svc._apply_voice_commands("cite regulation", "")
    assert "[CITE: 8 CFR" in result["new_transcript"]
    assert actions == ["cite regulation"]


def test_plain_text_has_no_commands():
    svc = VoxlenService()
    result, actions = svc._apply_voice_commands("the beneficiary is qualified", "")
    assert actions == []
    assert "the beneficiary is qualified" in result["new_transcript"]


# --- Session lifecycle -----------------------------------------------------

def test_start_session_with_template():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", template_key="rfe_response")
    assert s.template_key == "rfe_response"
    assert s.title == "RFE Response"
    assert s.status == "active"


def test_start_session_rejects_unsupported_language():
    svc = VoxlenService()
    with pytest.raises(ValueError, match="Unsupported language"):
        svc.start_session(owner_id="u1", language="xx-YY")


def test_start_session_rejects_unknown_template():
    svc = VoxlenService()
    with pytest.raises(ValueError, match="Unknown template"):
        svc.start_session(owner_id="u1", template_key="does_not_exist")


def test_session_isolation_between_users():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    with pytest.raises(PermissionError):
        svc.get_session(s.id, owner_id="u2")


def test_append_chunk_and_transcript_builds_up():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    svc.append_chunk(s.id, "u1", "the beneficiary", started_at_ms=0, ended_at_ms=500)
    svc.append_chunk(s.id, "u1", "is qualified period", started_at_ms=500, ended_at_ms=1200)
    fresh = svc.get_session(s.id, "u1")
    assert "the beneficiary" in fresh.corrected_text
    assert fresh.corrected_text.rstrip().endswith(".")
    assert len(fresh.chunks) == 2


def test_append_interim_chunk_not_stored():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    svc.append_chunk(s.id, "u1", "interim text", is_final=False)
    fresh = svc.get_session(s.id, "u1")
    assert fresh.chunks == []


def test_close_and_delete_session():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    closed = svc.close_session(s.id, "u1")
    assert closed.status == "closed"
    svc.delete_session(s.id, "u1")
    with pytest.raises(ValueError):
        svc.get_session(s.id, "u1")


# --- Grammar polish --------------------------------------------------------

def test_polish_legal_formal_expands_contractions():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", style=WritingStyle.LEGAL_FORMAL)
    svc.append_chunk(s.id, "u1", "the petitioner can't provide that")
    out = svc.polish(s.id, "u1")
    assert "cannot" in out["transcript"].lower()
    assert "can't" not in out["transcript"]


def test_polish_client_friendly_uses_contractions():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", style=WritingStyle.CLIENT_FRIENDLY)
    svc.append_chunk(s.id, "u1", "you cannot submit that yet")
    out = svc.polish(s.id, "u1")
    assert "can't" in out["transcript"].lower()


def test_polish_capitalizes_sentences():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", style=WritingStyle.PROFESSIONAL)
    svc.append_chunk(s.id, "u1", "hello world. this is great")
    out = svc.polish(s.id, "u1")
    assert out["transcript"].startswith("Hello world.")
    assert "This is great" in out["transcript"]


def test_polish_deterministic_flag_set_without_provider():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    svc.append_chunk(s.id, "u1", "hello")
    out = svc.polish(s.id, "u1")
    assert out["deterministic_fallback"] is True


# --- Export formats --------------------------------------------------------

def test_export_txt():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", title="Case 123")
    svc.append_chunk(s.id, "u1", "the beneficiary is qualified")
    out = svc.export(s.id, "u1", ExportFormat.TXT)
    assert out["filename"].endswith(".txt")
    assert out["mime"] == "text/plain"
    assert "beneficiary" in out["content"]


def test_export_markdown():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1", title="RFE Response")
    svc.append_chunk(s.id, "u1", "issue one")
    out = svc.export(s.id, "u1", ExportFormat.MARKDOWN)
    assert out["content"].startswith("# RFE Response")
    assert "**Language:**" in out["content"]


def test_export_json_is_valid():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    svc.append_chunk(s.id, "u1", "hello world", started_at_ms=0, ended_at_ms=1000)
    out = svc.export(s.id, "u1", ExportFormat.JSON)
    parsed = json.loads(out["content"])
    assert parsed["id"] == s.id
    assert len(parsed["chunks"]) == 1


def test_export_srt_has_timecodes():
    svc = VoxlenService()
    s = svc.start_session(owner_id="u1")
    svc.append_chunk(s.id, "u1", "first", started_at_ms=0, ended_at_ms=1500)
    svc.append_chunk(s.id, "u1", "second", started_at_ms=1500, ended_at_ms=3000)
    out = svc.export(s.id, "u1", ExportFormat.SRT)
    assert "00:00:00,000 --> 00:00:01,500" in out["content"]
    assert "00:00:01,500 --> 00:00:03,000" in out["content"]
    assert "first" in out["content"] and "second" in out["content"]


def test_safe_filename_sanitizes_title():
    assert VoxlenService._safe_filename("Re: H-1B/RFE!") == "Re_H-1B_RFE"
    assert VoxlenService._safe_filename("") == "dictation"


# --- Provider configuration ------------------------------------------------

def test_configure_provider_rejects_unknown():
    svc = VoxlenService()
    with pytest.raises(ValueError):
        svc.configure_provider("random-vendor", "1234567890abcdef")


def test_configure_provider_rejects_short_key():
    svc = VoxlenService()
    with pytest.raises(ValueError, match="invalid"):
        svc.configure_provider("deepgram", "short")


def test_configure_provider_fingerprint():
    svc = VoxlenService()
    out = svc.configure_provider("deepgram", "abcdefghij1234567890")
    assert out["configured"] is True
    assert "…" in out["fingerprint"]
    assert out["fingerprint"].startswith("abcd")
    assert out["fingerprint"].endswith("7890")
    # Original key not echoed back
    assert "abcdefghij1234567890" not in out["fingerprint"]


def test_provider_status_tracks_configured():
    svc = VoxlenService()
    svc.configure_provider("anthropic", "sk-ant-xxxxxxxxxx")
    status = svc.provider_status()
    assert status["anthropic"] is True
    assert status["deepgram"] is False


# --- Catalog ---------------------------------------------------------------

def test_catalog_exposes_required_fields():
    cat = VoxlenService.catalog()
    assert len(cat["languages"]) >= 20
    assert "legal_formal" in cat["styles"]
    assert "srt" in cat["export_formats"]
    assert "new paragraph" in cat["voice_commands"]
    assert "rfe_response" in cat["templates"]
    assert cat["templates"]["rfe_response"]["title"] == "RFE Response"


# --- API surface -----------------------------------------------------------

def test_api_catalog_public():
    r = client.get("/api/voxlen/catalog")
    assert r.status_code == 200
    body = r.json()
    assert "voice_commands" in body
    assert "rfe_response" in body["templates"]


def test_api_session_requires_auth():
    r = client.post("/api/voxlen/sessions", json={})
    assert r.status_code == 401


def test_api_full_round_trip():
    headers = _auth()
    r = client.post(
        "/api/voxlen/sessions",
        json={
            "language": "en-US",
            "style": "legal_formal",
            "template_key": "rfe_response",
            "title": "Smith RFE",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["id"]
    # Append transcript
    r2 = client.post(
        f"/api/voxlen/sessions/{session_id}/append",
        json={
            "text": "the petitioner can't show specialty period",
            "started_at_ms": 0,
            "ended_at_ms": 2000,
        },
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["transcript"].rstrip().endswith(".")
    # Polish
    r3 = client.post(
        f"/api/voxlen/sessions/{session_id}/polish",
        json={"style": "legal_formal"},
        headers=headers,
    )
    assert r3.status_code == 200
    assert "cannot" in r3.json()["transcript"].lower()
    # Export markdown
    r4 = client.get(
        f"/api/voxlen/sessions/{session_id}/export?fmt=markdown",
        headers=headers,
    )
    assert r4.status_code == 200
    assert r4.json()["content"].startswith("# Smith RFE")
    # List shows the session
    r5 = client.get("/api/voxlen/sessions", headers=headers)
    assert r5.status_code == 200
    assert any(s["id"] == session_id for s in r5.json())
    # Close
    r6 = client.post(
        f"/api/voxlen/sessions/{session_id}/close", headers=headers
    )
    assert r6.status_code == 200
    assert r6.json()["status"] == "closed"
    # Delete
    r7 = client.delete(
        f"/api/voxlen/sessions/{session_id}", headers=headers
    )
    assert r7.status_code == 200


def test_api_session_ownership_enforced():
    h1 = _auth(email="a@x.com")
    r = client.post("/api/voxlen/sessions", json={}, headers=h1)
    sid = r.json()["id"]
    h2 = _auth(email="b@x.com")
    r2 = client.get(f"/api/voxlen/sessions/{sid}", headers=h2)
    assert r2.status_code == 403


def test_api_configure_provider():
    headers = _auth()
    r = client.post(
        "/api/voxlen/configure",
        json={"provider": "deepgram", "api_key": "abcdefghij1234567890"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["configured"] is True
    status = client.get("/api/voxlen/provider-status", headers=headers).json()
    assert status["deepgram"] is True
