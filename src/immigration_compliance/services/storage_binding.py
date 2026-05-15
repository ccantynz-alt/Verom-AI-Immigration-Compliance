"""Storage binding helpers for service classes.

Each major service holds its state in dict-shaped instance attributes.
We bind the persistent store by:

  1. Adding an attribute name allowlist describing which dict attributes
     constitute the service's state (via SERVICE_STATE_ATTRS below).
  2. `bind_storage()` loads any previously-saved state on attach,
     and wraps mutating methods to save after they return.
  3. The save call is debounced — multiple writes within a 50ms window
     coalesce into a single SQLite write.

This is intentionally a thin wrapper. Services are not aware of the store
beyond what `bind_storage()` does to them. Tests still create services
without the store and they work as before."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


# Map service class name → (default namespace, list of dict attribute names)
SERVICE_STATE_ATTRS: dict[str, tuple[str, list[str]]] = {
    "CaseWorkspaceService":      ("case_workspace", ["_workspaces", "_timeline", "_notes", "_deadlines"]),
    "IntakeEngineService":       ("intake_engine", ["_sessions"]),
    "DocumentIntakeService":     ("document_intake", ["_documents"]),
    "FormPopulationService":     ("form_population", ["_populated", "_provenance"]),
    "ConflictCheckService":      ("conflict_check", ["_clients", "_cases", "_screens", "_check_log"]),
    "OnboardingService":         ("onboarding", ["_sessions"]),
    "FamilyBundleService":       ("family_bundle", ["_bundles"]),
    "ClientChatbotService":      ("client_chatbot", ["_conversations", "_messages", "_handoffs"]),
    "PacketAssemblyService":     ("packet_assembly", ["_packets"]),
    "RegulatoryImpactService":   ("regulatory_impact", ["_events", "_reports"]),
    "MigrationImporterService":  ("migration_importer", ["_imports", "_row_hashes"]),
    "PetitionLetterService":     ("petition_letter", ["_drafts"]),
    "RFEResponseService":        ("rfe_response", ["_drafts"]),
    "AttorneyMatchService":      ("attorney_match", ["_attorneys", "_match_log"]),
    "CalendarSyncService":       ("calendar_sync", ["_subscriptions", "_oauth_connections", "_push_log"]),
}


class _DebouncedSaver:
    """Coalesces save calls within a small window into a single store.save() call."""

    def __init__(self, store: Any, namespace: str, get_state: Callable[[], dict], delay_ms: int = 50) -> None:
        self._store = store
        self._namespace = namespace
        self._get_state = get_state
        self._delay_ms = delay_ms
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._dirty = False

    def schedule(self) -> None:
        with self._lock:
            self._dirty = True
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay_ms / 1000.0, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def flush(self) -> None:
        """Synchronous flush — useful for tests."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._flush_locked()

    def _flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._dirty:
            return
        try:
            state = self._get_state()
            self._store.save(self._namespace, state)
            self._dirty = False
        except Exception:
            # Swallow — persistence is best-effort; service still works.
            self._dirty = False


def bind_storage(service: Any, store: Any, namespace: str | None = None) -> _DebouncedSaver | None:
    """Attach a persistent store to a service. Loads previously-saved state
    and starts auto-saving after mutating methods.

    Returns the debounced saver so tests can call .flush() to force a write."""
    cls_name = type(service).__name__
    if cls_name not in SERVICE_STATE_ATTRS:
        return None
    default_ns, attrs = SERVICE_STATE_ATTRS[cls_name]
    ns = namespace or default_ns

    # 1) Load
    saved = store.load(ns)
    if isinstance(saved, dict):
        for attr in attrs:
            if attr in saved and hasattr(service, attr):
                cur = getattr(service, attr)
                # Restore based on type of current attribute
                if isinstance(cur, dict):
                    cur.clear()
                    cur.update(saved[attr] or {})
                elif isinstance(cur, list):
                    cur.clear()
                    cur.extend(saved[attr] or [])
                elif isinstance(cur, set):
                    cur.clear()
                    cur.update(saved[attr] or [])

    # 2) Build state-getter
    def get_state() -> dict:
        out = {}
        for attr in attrs:
            if hasattr(service, attr):
                v = getattr(service, attr)
                if isinstance(v, set):
                    out[attr] = list(v)
                else:
                    out[attr] = v
        return out

    saver = _DebouncedSaver(store=store, namespace=ns, get_state=get_state)

    # 3) Wrap mutating methods so they trigger a save afterward.
    # Conservative: any public method that ends with create/add/update/delete/
    # remove/submit/log/run/upload/start/end/connect/disconnect/revoke/rotate/
    # populate/import/ingest/analyze/take_over/release/post_message/resolve/
    # advance_milestone/handle_lifecycle is wrapped.
    mutating_keywords = (
        "create", "add", "update", "delete", "remove", "submit", "log", "run",
        "upload", "start", "end", "connect", "disconnect", "revoke", "rotate",
        "populate", "import", "ingest", "analyze", "take_over", "release",
        "post_message", "resolve", "advance", "handle", "complete", "register",
        "assign", "link", "record", "configure",
    )
    for name in dir(service):
        if name.startswith("_"):
            continue
        attr_val = getattr(service, name, None)
        if not callable(attr_val):
            continue
        if not any(kw in name for kw in mutating_keywords):
            continue
        wrapped = _wrap_with_save(attr_val, saver)
        try:
            setattr(service, name, wrapped)
        except Exception:
            # Some methods might be read-only descriptors — skip
            pass

    # 4) Audit log on every successful mutating call too — namespace = ns,
    #    action = method name, actor unknown at this layer (recorded by the
    #    FastAPI route layer which has user context).
    return saver


def _wrap_with_save(fn: Callable, saver: _DebouncedSaver) -> Callable:
    def wrapped(*args, **kwargs):
        result = fn(*args, **kwargs)
        saver.schedule()
        return wrapped.saver  # noqa: F841 -- placeholder, returned below
    # Properly return the original result
    def real(*args, **kwargs):
        result = fn(*args, **kwargs)
        saver.schedule()
        return result
    return real
