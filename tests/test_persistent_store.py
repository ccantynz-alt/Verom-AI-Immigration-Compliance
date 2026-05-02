"""Tests for the SQLite-backed persistent store."""

import os
import tempfile

from immigration_compliance.services.persistent_store_service import (
    PersistentStore,
    get_default_store,
    reset_default_store,
)


def _temp_store():
    path = tempfile.mktemp(suffix=".db")
    return PersistentStore(db_path=path), path


def _cleanup(path: str):
    try:
        os.unlink(path)
    except OSError:
        pass


def test_save_and_load_round_trip():
    store, path = _temp_store()
    try:
        store.save("ns1", {"a": 1, "b": [1, 2, 3]})
        loaded = store.load("ns1")
        assert loaded == {"a": 1, "b": [1, 2, 3]}
    finally:
        store.close()
        _cleanup(path)


def test_save_replaces_state():
    store, path = _temp_store()
    try:
        store.save("ns1", {"v": 1})
        store.save("ns1", {"v": 2})
        assert store.load("ns1") == {"v": 2}
    finally:
        store.close()
        _cleanup(path)


def test_load_missing_namespace_returns_none():
    store, path = _temp_store()
    try:
        assert store.load("does_not_exist") is None
    finally:
        store.close()
        _cleanup(path)


def test_save_empty_namespace_raises():
    store, path = _temp_store()
    try:
        try:
            store.save("", {"x": 1})
            assert False
        except ValueError:
            pass
    finally:
        store.close()
        _cleanup(path)


def test_persistence_across_instances():
    path = tempfile.mktemp(suffix=".db")
    try:
        store1 = PersistentStore(db_path=path)
        store1.save("ns1", {"persisted": True})
        store1.close()
        store2 = PersistentStore(db_path=path)
        loaded = store2.load("ns1")
        assert loaded == {"persisted": True}
        store2.close()
    finally:
        _cleanup(path)


def test_list_namespaces():
    store, path = _temp_store()
    try:
        store.save("ns1", {"a": 1})
        store.save("ns2", {"b": 2})
        ns_list = store.list_namespaces()
        names = {n["namespace"] for n in ns_list}
        assert names == {"ns1", "ns2"}
        for n in ns_list:
            assert n["size_bytes"] > 0
            assert n["updated_at"]
    finally:
        store.close()
        _cleanup(path)


def test_clear_namespace():
    store, path = _temp_store()
    try:
        store.save("ns1", {"a": 1})
        assert store.clear("ns1") is True
        assert store.load("ns1") is None
        assert store.clear("ns1") is False
    finally:
        store.close()
        _cleanup(path)


def test_clear_all():
    store, path = _temp_store()
    try:
        store.save("ns1", {})
        store.save("ns2", {})
        count = store.clear_all()
        assert count == 2
        assert store.list_namespaces() == []
    finally:
        store.close()
        _cleanup(path)


def test_audit_log_append_and_query():
    store, path = _temp_store()
    try:
        store.log("case_workspace", "create", actor_id="user-1", target_id="ws-1", payload={"v": 1})
        store.log("case_workspace", "update", actor_id="user-1", target_id="ws-1")
        store.log("intake", "submit", actor_id="user-2", payload={"answers": 5})
        all_log = store.get_log()
        assert len(all_log) == 3
        cw_log = store.get_log(namespace="case_workspace")
        assert len(cw_log) == 2
        actor1 = store.get_log(actor_id="user-1")
        assert len(actor1) == 2
        target = store.get_log(target_id="ws-1")
        assert len(target) == 2
        action = store.get_log(action="submit")
        assert len(action) == 1
    finally:
        store.close()
        _cleanup(path)


def test_audit_log_descending_order():
    store, path = _temp_store()
    try:
        for i in range(5):
            store.log("ns", f"action-{i}", actor_id="u")
        log = store.get_log(limit=3)
        assert len(log) == 3
        # Most recent first
        assert log[0]["action"] == "action-4"
        assert log[1]["action"] == "action-3"
    finally:
        store.close()
        _cleanup(path)


def test_audit_log_payload_round_trip():
    store, path = _temp_store()
    try:
        store.log("ns", "complex", payload={"nested": {"data": [1, 2]}})
        log = store.get_log()
        assert log[0]["payload"] == {"nested": {"data": [1, 2]}}
    finally:
        store.close()
        _cleanup(path)


def test_audit_summary_aggregates():
    store, path = _temp_store()
    try:
        store.log("ns1", "create"); store.log("ns1", "create"); store.log("ns1", "delete")
        store.log("ns2", "create")
        summary = store.get_audit_summary()
        assert summary["total_entries"] == 4
        assert summary["by_namespace"]["ns1"] == 3
        assert summary["by_namespace"]["ns2"] == 1
        assert summary["by_action"]["create"] == 3
    finally:
        store.close()
        _cleanup(path)


def test_default_store_singleton():
    reset_default_store()
    s1 = get_default_store(db_path=tempfile.mktemp(suffix=".db"))
    s2 = get_default_store()
    assert s1 is s2
    reset_default_store()


def test_save_handles_non_json_serializable_via_str():
    """default=str should let dates/datetimes through without crashing."""
    from datetime import datetime
    store, path = _temp_store()
    try:
        store.save("ns", {"now": datetime(2026, 1, 1, 12, 0)})
        loaded = store.load("ns")
        assert loaded is not None
        # datetime serialized as ISO string
        assert "2026-01-01" in loaded["now"]
    finally:
        store.close()
        _cleanup(path)
