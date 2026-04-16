"""Tests for the Continuous Improvement (Zero Idle Time) flywheel."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from immigration_compliance.api.app import app, cis_service
from immigration_compliance.services.continuous_improvement_service import (
    ContinuousImprovementService,
    ImprovementPriority,
    ImprovementStatus,
    SignalSource,
)


client = TestClient(app)


def setup_function() -> None:
    # Reset the shared service between tests — isolate state
    cis_service._signals.clear()
    cis_service._ideas.clear()
    cis_service._ledger.clear()
    cis_service._tick_count = 0


# --- Signal ingestion ------------------------------------------------------

def test_ingest_signal_happy_path():
    svc = ContinuousImprovementService()
    sig = svc.ingest_signal(
        source=SignalSource.COMPETITOR,
        summary="Casium shipped agentic RFE responder",
        payload={"vendor": "casium", "feature": "rfe_responder"},
        relevance=0.9,
    )
    assert sig.id
    assert sig.source == SignalSource.COMPETITOR
    assert sig.relevance == 0.9
    assert svc.list_signals() == [sig]


def test_ingest_signal_clamps_relevance():
    svc = ContinuousImprovementService()
    low = svc.ingest_signal(SignalSource.BUG_REPORT, "x", relevance=-5)
    high = svc.ingest_signal(SignalSource.BUG_REPORT, "y", relevance=99)
    assert low.relevance == 0.0
    assert high.relevance == 1.0


def test_ingest_signal_rejects_privileged_payload():
    svc = ContinuousImprovementService()
    with pytest.raises(ValueError, match="Prohibited signal key"):
        svc.ingest_signal(
            SignalSource.INTERNAL_AUDIT,
            "leak attempt",
            payload={"client_data": "secret"},
        )


def test_list_signals_filters_by_source():
    svc = ContinuousImprovementService()
    svc.ingest_signal(SignalSource.COMPETITOR, "a")
    svc.ingest_signal(SignalSource.DEPENDENCY, "b")
    out = svc.list_signals(source=SignalSource.DEPENDENCY)
    assert len(out) == 1
    assert out[0].summary == "b"


# --- Idea queue ------------------------------------------------------------

def test_propose_and_list_ideas_prioritized():
    svc = ContinuousImprovementService()
    low = svc.propose_improvement("polish", "small", ImprovementPriority.P3_POLISH)
    broken = svc.propose_improvement("fix 500", "critical", ImprovementPriority.P0_BROKEN)
    upgrade = svc.propose_improvement("bump fastapi", "cve", ImprovementPriority.P2_UPGRADE)
    q = svc.list_queue()
    assert [i.id for i in q] == [broken.id, upgrade.id, low.id]


def test_propose_with_unknown_signal_raises():
    svc = ContinuousImprovementService()
    with pytest.raises(ValueError, match="unknown signal"):
        svc.propose_improvement("x", "y", origin_signal_id="does-not-exist")


def test_next_task_returns_highest_priority_and_marks_in_progress():
    svc = ContinuousImprovementService()
    svc.propose_improvement("polish", "small", ImprovementPriority.P3_POLISH)
    broken = svc.propose_improvement("fix", "critical", ImprovementPriority.P0_BROKEN)
    picked = svc.next_task()
    assert picked is not None
    assert picked.id == broken.id
    assert picked.status == ImprovementStatus.IN_PROGRESS


def test_next_task_none_when_empty():
    svc = ContinuousImprovementService()
    assert svc.next_task() is None


def test_defer_and_reject():
    svc = ContinuousImprovementService()
    idea = svc.propose_improvement("x", "y")
    svc.defer(idea.id, reason="waiting-on-legal")
    assert svc._ideas[idea.id].status == ImprovementStatus.DEFERRED
    idea2 = svc.propose_improvement("a", "b")
    svc.reject(idea2.id, reason="duplicate")
    assert svc._ideas[idea2.id].status == ImprovementStatus.REJECTED


# --- Advancement ledger / daily mandate -----------------------------------

def test_record_advancement_marks_idea_shipped():
    svc = ContinuousImprovementService()
    idea = svc.propose_improvement("ship me", "because")
    rec = svc.record_advancement(
        title="Shipped feature X",
        description="Done",
        improvement_id=idea.id,
    )
    assert rec.date == date.today().isoformat()
    assert svc._ideas[idea.id].status == ImprovementStatus.SHIPPED
    assert svc._ideas[idea.id].shipped_at is not None


def test_daily_mandate_met_after_one_advancement():
    svc = ContinuousImprovementService()
    status = svc.daily_mandate_status()
    assert status["mandate_met"] is False
    svc.record_advancement("t", "d")
    status = svc.daily_mandate_status()
    assert status["mandate_met"] is True
    assert status["shipped_count"] == 1


def test_flywheel_state_and_tick():
    svc = ContinuousImprovementService()
    svc.propose_improvement("one", "x", ImprovementPriority.P1_COMPETITIVE)
    svc.propose_improvement("two", "y", ImprovementPriority.P3_POLISH)
    state1 = svc.flywheel_state()
    assert state1["ideas_total"] == 2
    assert state1["ideas_by_status"][ImprovementStatus.QUEUED.value] == 2
    tick1 = svc.tick()
    assert tick1["tick"] == 1
    assert tick1["picked_up"]["priority"] == ImprovementPriority.P1_COMPETITIVE.value
    # After tick, one is in progress, queue depth drops to 1
    assert tick1["queue_depth"] == 1


def test_tick_with_empty_queue_is_safe():
    svc = ContinuousImprovementService()
    out = svc.tick()
    assert out["picked_up"] is None
    assert out["queue_depth"] == 0


# --- API surface -----------------------------------------------------------

def test_api_ingest_signal_and_list():
    r = client.post(
        "/api/cis/signals",
        json={
            "source": "competitor",
            "summary": "new feature from Casium",
            "payload": {"vendor": "casium"},
            "relevance": 0.8,
        },
    )
    assert r.status_code == 200, r.text
    sig_id = r.json()["id"]
    r2 = client.get("/api/cis/signals")
    assert r2.status_code == 200
    assert any(s["id"] == sig_id for s in r2.json())


def test_api_rejects_privileged_signal():
    r = client.post(
        "/api/cis/signals",
        json={
            "source": "internal_audit",
            "summary": "bad",
            "payload": {"client_data": "oops"},
        },
    )
    assert r.status_code == 400


def test_api_propose_idea_and_tick():
    r = client.post(
        "/api/cis/ideas",
        json={
            "title": "upgrade fastapi",
            "rationale": "newer release",
            "priority": "p2_upgrade",
        },
    )
    assert r.status_code == 200, r.text
    idea_id = r.json()["id"]
    tick = client.post("/api/cis/tick").json()
    assert tick["picked_up"]["id"] == idea_id


def test_api_record_advancement_shows_in_ledger():
    idea_r = client.post(
        "/api/cis/ideas",
        json={"title": "t", "rationale": "r"},
    )
    idea_id = idea_r.json()["id"]
    adv = client.post(
        "/api/cis/advancements",
        json={
            "title": "shipped it",
            "description": "done",
            "improvement_id": idea_id,
        },
    )
    assert adv.status_code == 200
    ledger = client.get("/api/cis/advancements").json()
    assert ledger["today"]["mandate_met"] is True
    assert any(r["title"] == "shipped it" for r in ledger["today_records"])


def test_api_state_endpoint():
    r = client.get("/api/cis/state")
    assert r.status_code == 200
    body = r.json()
    for key in ("ticks", "signals", "ideas_total", "ideas_by_status", "mandate_today"):
        assert key in body
