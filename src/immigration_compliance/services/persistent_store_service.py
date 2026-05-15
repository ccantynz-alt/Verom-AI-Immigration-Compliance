"""Persistent Store — SQLite-backed snapshotting for service state.

The platform's services keep their state in plain dicts/lists for
testability and speed. This module gives them durable persistence
without touching their data models: a service registers itself with
a namespace, hands its in-memory state to `save()` on writes, and
loads it on startup.

Schema:
  service_state:
    namespace TEXT PRIMARY KEY        -- e.g. "case_workspace"
    payload   TEXT                    -- JSON-serialized state dict
    updated_at TEXT                   -- ISO-8601 UTC

  audit_log:
    id INTEGER PRIMARY KEY AUTOINCREMENT
    namespace TEXT NOT NULL
    actor_id TEXT
    action TEXT NOT NULL
    target_id TEXT
    payload TEXT                       -- JSON details
    at TEXT NOT NULL

Two paths:
  - JSON snapshotting: full namespace state replaced on each save.
    Simple, atomic, survives crashes. Good for early stages.
  - Append-only audit log: separate table that's never truncated.
    The persistent home for everything that used to live in
    `AuditTrailService` in-memory.

Services use it via the StorageMixin convenience class — drop-in
addition to the existing service classes. Existing tests still pass
because if no store is configured, save/load are no-ops."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Persistent Store
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = os.environ.get("VEROM_DB_PATH", "verom_state.db")
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS service_state (
    namespace TEXT PRIMARY KEY,
    payload   TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    actor_id TEXT,
    action TEXT NOT NULL,
    target_id TEXT,
    payload TEXT,
    at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_namespace ON audit_log(namespace);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_at ON audit_log(at);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


class PersistentStore:
    """Thread-safe SQLite-backed key/value + audit-log persistence.

    Use a single instance per process. The connection is opened lazily and
    serialized via a lock — fine for our scale; swap for a connection pool
    when concurrency demands it."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    # ---------- connection management ----------
    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.executescript(SCHEMA)
            cur = self._conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row is None:
                self._conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # ---------- service state ----------
    def save(self, namespace: str, state: dict | list) -> None:
        """Replace the persisted state for a namespace. Atomic."""
        if not namespace:
            raise ValueError("namespace required")
        payload = json.dumps(state, default=str)
        now = datetime.utcnow().isoformat()
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT INTO service_state (namespace, payload, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(namespace) DO UPDATE SET payload = excluded.payload, "
                "updated_at = excluded.updated_at",
                (namespace, payload, now),
            )

    def load(self, namespace: str) -> Any | None:
        if not namespace:
            return None
        with self._lock:
            conn = self._connect()
            cur = conn.execute("SELECT payload FROM service_state WHERE namespace = ?", (namespace,))
            row = cur.fetchone()
            if row is None:
                return None
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return None

    def list_namespaces(self) -> list[dict]:
        with self._lock:
            conn = self._connect()
            cur = conn.execute("SELECT namespace, updated_at, length(payload) FROM service_state ORDER BY namespace")
            return [
                {"namespace": ns, "updated_at": at, "size_bytes": size}
                for ns, at, size in cur.fetchall()
            ]

    def clear(self, namespace: str) -> bool:
        with self._lock:
            conn = self._connect()
            cur = conn.execute("DELETE FROM service_state WHERE namespace = ?", (namespace,))
            return cur.rowcount > 0

    def clear_all(self) -> int:
        with self._lock:
            conn = self._connect()
            cur = conn.execute("DELETE FROM service_state")
            return cur.rowcount

    # ---------- audit log ----------
    def log(
        self,
        namespace: str,
        action: str,
        actor_id: str | None = None,
        target_id: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        """Append a single audit log entry. Append-only — never updated, never deleted."""
        now = datetime.utcnow().isoformat()
        json_payload = json.dumps(payload, default=str) if payload is not None else None
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO audit_log (namespace, actor_id, action, target_id, payload, at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (namespace, actor_id, action, target_id, json_payload, now),
            )
            row_id = cur.lastrowid
        return {
            "id": row_id, "namespace": namespace, "actor_id": actor_id,
            "action": action, "target_id": target_id, "payload": payload, "at": now,
        }

    def get_log(
        self,
        namespace: str | None = None,
        actor_id: str | None = None,
        target_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        since: str | None = None,
    ) -> list[dict]:
        sql = "SELECT id, namespace, actor_id, action, target_id, payload, at FROM audit_log WHERE 1=1"
        params: list[Any] = []
        if namespace:
            sql += " AND namespace = ?"; params.append(namespace)
        if actor_id:
            sql += " AND actor_id = ?"; params.append(actor_id)
        if target_id:
            sql += " AND target_id = ?"; params.append(target_id)
        if action:
            sql += " AND action = ?"; params.append(action)
        if since:
            sql += " AND at >= ?"; params.append(since)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._connect()
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        out = []
        for row_id, ns, actor, action_, target, payload, at in rows:
            try:
                parsed = json.loads(payload) if payload else None
            except (json.JSONDecodeError, TypeError):
                parsed = None
            out.append({
                "id": row_id, "namespace": ns, "actor_id": actor,
                "action": action_, "target_id": target, "payload": parsed, "at": at,
            })
        return out

    def get_audit_summary(self) -> dict:
        with self._lock:
            conn = self._connect()
            total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            by_ns = {ns: cnt for ns, cnt in conn.execute(
                "SELECT namespace, COUNT(*) FROM audit_log GROUP BY namespace"
            ).fetchall()}
            by_action = {a: cnt for a, cnt in conn.execute(
                "SELECT action, COUNT(*) FROM audit_log GROUP BY action"
            ).fetchall()}
        return {
            "total_entries": total,
            "by_namespace": by_ns,
            "by_action": by_action,
        }


# ---------------------------------------------------------------------------
# Convenience: a process-wide default store
# ---------------------------------------------------------------------------

_DEFAULT_STORE: PersistentStore | None = None
_DEFAULT_STORE_LOCK = threading.Lock()


def get_default_store(db_path: str | None = None) -> PersistentStore:
    global _DEFAULT_STORE
    with _DEFAULT_STORE_LOCK:
        if _DEFAULT_STORE is None or db_path is not None:
            _DEFAULT_STORE = PersistentStore(db_path=db_path)
        return _DEFAULT_STORE


def reset_default_store() -> None:
    """Tests use this to clear the singleton between cases."""
    global _DEFAULT_STORE
    with _DEFAULT_STORE_LOCK:
        if _DEFAULT_STORE is not None:
            _DEFAULT_STORE.close()
        _DEFAULT_STORE = None
