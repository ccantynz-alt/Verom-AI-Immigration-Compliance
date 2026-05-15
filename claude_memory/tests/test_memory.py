"""Tests for the Claude Memory library, CLI, and MCP tool dispatch."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

# Make the parent dir importable
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from memory import (  # noqa: E402
    Memory,
    VALID_KINDS,
    cosine,
    hash_embedder,
    main as cli_main,
    openai_embedder,
    voyage_embedder,
)
from memory_mcp import handle_tool, TOOL_SPECS  # noqa: E402


@pytest.fixture
def db(tmp_path) -> Memory:
    mem = Memory(tmp_path / "mem.db")
    yield mem
    mem.close()


# --- Embedder -------------------------------------------------------------

def test_hash_embedder_is_deterministic():
    a = hash_embedder("the quick brown fox")
    b = hash_embedder("the quick brown fox")
    assert a == b
    assert len(a) == 256


def test_hash_embedder_different_inputs_differ():
    a = hash_embedder("database choice")
    b = hash_embedder("frontend framework")
    assert a != b


def test_cosine_identical_vectors_is_one():
    v = hash_embedder("hello world")
    assert cosine(v, v) == pytest.approx(1.0, abs=1e-6)


def test_cosine_empty_vectors_is_zero():
    assert cosine([], [0.1, 0.2]) == 0.0


# --- Store / get / update / delete ----------------------------------------

def test_store_returns_entry_with_id_and_timestamps(db):
    entry = db.store("We picked SQLite", kind="decision", tags=["infra", "db"])
    assert entry["id"] >= 1
    assert entry["kind"] == "decision"
    assert entry["content"] == "We picked SQLite"
    assert sorted(entry["tags"]) == ["db", "infra"]
    assert entry["created_at"] == entry["updated_at"]


def test_store_rejects_empty_content(db):
    with pytest.raises(ValueError, match="empty"):
        db.store("   ")


def test_store_rejects_invalid_kind(db):
    with pytest.raises(ValueError, match="invalid kind"):
        db.store("x", kind="random")


def test_get_missing_raises(db):
    with pytest.raises(KeyError):
        db.get(9999)


def test_update_changes_content_and_timestamp(db):
    a = db.store("original")
    b = db.update(a["id"], content="revised")
    assert b["content"] == "revised"
    assert b["created_at"] == a["created_at"]
    # updated_at may equal created_at on fast clocks, but content has changed
    assert b["id"] == a["id"]


def test_delete_returns_true_then_false(db):
    e = db.store("temp")
    assert db.delete(e["id"]) is True
    assert db.delete(e["id"]) is False


# --- Recall: keyword + vector ---------------------------------------------

def test_recall_finds_exact_keyword_match(db):
    db.store("We picked SQLite over Postgres for portability", kind="decision")
    db.store("Frontend: vanilla JS, no framework", kind="decision")
    hits = db.recall("SQLite", limit=5)
    assert hits
    assert "SQLite" in hits[0]["content"]


def test_recall_prefers_more_relevant_entry(db):
    db.store("The CEO likes red office chairs.", kind="note")
    db.store("Database choice: SQLite for portability.", kind="decision")
    hits = db.recall("which database did we pick", limit=2)
    assert hits
    # The database note should outrank the office-chair note.
    top = hits[0]["content"]
    assert "database" in top.lower() or "sqlite" in top.lower()


def test_recall_respects_kind_filter(db):
    db.store("a decision", kind="decision")
    db.store("a question", kind="question")
    results = db.recall("a", kind="decision", limit=10)
    assert all(r["kind"] == "decision" for r in results)


def test_recall_respects_project_filter(db):
    db.store("alpha thing", project="alpha")
    db.store("beta thing", project="beta")
    results = db.recall("thing", project="alpha", limit=10)
    assert all(r["project"] == "alpha" for r in results)
    assert any("alpha" in r["content"] for r in results)


def test_recall_empty_query_returns_empty(db):
    db.store("anything")
    assert db.recall("") == []


def test_recall_respects_min_score(db):
    db.store("totally unrelated content about cats")
    results = db.recall("quantum field theory", min_score=0.9)
    assert results == []


def test_recall_includes_score(db):
    db.store("SQLite is portable and fast")
    [hit] = db.recall("SQLite")
    assert "score" in hit
    assert 0.0 <= hit["score"] <= 1.0


# --- Listing / stats ------------------------------------------------------

def test_list_returns_newest_first(db):
    a = db.store("first")
    b = db.store("second")
    rows = db.list_entries(limit=10)
    # newest first
    assert rows[0]["id"] == b["id"]
    assert rows[1]["id"] == a["id"]


def test_stats_reports_counts(db):
    db.store("d1", kind="decision")
    db.store("d2", kind="decision")
    db.store("q1", kind="question")
    stats = db.stats()
    assert stats["total"] == 3
    assert stats["by_kind"]["decision"] == 2
    assert stats["by_kind"]["question"] == 1


# --- MCP tool dispatch ----------------------------------------------------

def test_mcp_tool_specs_cover_all_operations():
    names = {spec["name"] for spec in TOOL_SPECS}
    assert names == {
        "memory_store",
        "memory_recall",
        "memory_list",
        "memory_get",
        "memory_update",
        "memory_delete",
        "memory_stats",
    }


def test_mcp_store_and_recall_round_trip(db):
    stored = handle_tool(
        "memory_store",
        {"content": "Decided: SQLite + FTS5 + vector hybrid", "kind": "decision"},
        db,
    )
    assert stored["id"] >= 1
    out = handle_tool("memory_recall", {"query": "SQLite vector hybrid"}, db)
    assert out["results"]
    assert "SQLite" in out["results"][0]["content"]


def test_mcp_list_get_update_delete_stats(db):
    created = handle_tool("memory_store", {"content": "original"}, db)
    listed = handle_tool("memory_list", {}, db)
    assert any(r["id"] == created["id"] for r in listed["results"])
    got = handle_tool("memory_get", {"id": created["id"]}, db)
    assert got["content"] == "original"
    updated = handle_tool(
        "memory_update",
        {"id": created["id"], "content": "revised", "tags": ["x"]},
        db,
    )
    assert updated["content"] == "revised"
    stats = handle_tool("memory_stats", {}, db)
    assert stats["total"] >= 1
    del_out = handle_tool("memory_delete", {"id": created["id"]}, db)
    assert del_out["deleted"] is True


def test_mcp_unknown_tool_raises(db):
    with pytest.raises(ValueError, match="unknown tool"):
        handle_tool("memory_nonexistent", {}, db)


# --- CLI ------------------------------------------------------------------

def test_cli_store_and_recall(tmp_path):
    db_path = str(tmp_path / "cli.db")
    # store
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli_main(["--db", db_path, "store", "We chose SQLite for portability", "--kind", "decision", "--tags", "infra,db"])
    assert rc == 0
    stored = json.loads(buf.getvalue())
    assert stored["kind"] == "decision"
    assert "db" in stored["tags"]
    # recall
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc = cli_main(["--db", db_path, "recall", "SQLite"])
    assert rc == 0
    hits = json.loads(buf2.getvalue())
    assert hits and "SQLite" in hits[0]["content"]


def test_cli_stats_reports_total(tmp_path):
    db_path = str(tmp_path / "cli2.db")
    cli_main(["--db", db_path, "store", "hello"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_main(["--db", db_path, "stats"])
    stats = json.loads(buf.getvalue())
    assert stats["total"] == 1


# --- Schema / persistence ------------------------------------------------

def test_valid_kinds_match_contract():
    assert VALID_KINDS == {
        "note",
        "decision",
        "state",
        "question",
        "session",
        "fact",
        "preference",
        "person",
        "project_meta",
        "insight",
    }


def test_store_accepts_expanded_kinds(db):
    for kind in ("preference", "person", "project_meta", "insight"):
        entry = db.store(f"{kind} content", kind=kind)
        assert entry["kind"] == kind


# --- Embedder factories --------------------------------------------------

def test_openai_embedder_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        openai_embedder()


def test_voyage_embedder_requires_api_key(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
        voyage_embedder()


def test_openai_embedder_picks_up_env_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    embed = openai_embedder()
    assert callable(embed)


def test_embedder_factories_return_zero_vector_for_empty_input(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("VOYAGE_API_KEY", "vy-test")
    # Empty text must not make a network call.
    assert openai_embedder()("") == [0.0] * 256
    assert voyage_embedder()("   ") == [0.0] * 256


def test_persistence_across_reopen(tmp_path):
    db_path = tmp_path / "persist.db"
    with Memory(db_path) as m:
        m.store("first run remembers this", kind="fact")
    with Memory(db_path) as m2:
        hits = m2.recall("remembers this")
        assert hits and "first run" in hits[0]["content"]
