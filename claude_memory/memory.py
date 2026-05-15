#!/usr/bin/env python3
"""Claude Memory — SQLite + FTS5 + optional vector search, with a Python CLI.

Public API:
    Memory(db_path)
        .store(content, kind='note', tags=(), project='default') -> dict
        .recall(query, *, kind=None, project=None, limit=5, min_score=0.0) -> list[dict]
        .list_entries(kind=None, project=None, limit=50) -> list[dict]
        .get(entry_id) -> dict
        .delete(entry_id) -> bool
        .update(entry_id, content=None, tags=None) -> dict
        .stats() -> dict

Design goals:
    - Works with only the Python standard library. No required third-party deps.
    - SQLite FTS5 (built into modern SQLite) powers keyword search.
    - Optional vector embeddings via a pluggable Embedder callable. A
      deterministic hashing fallback is provided so recall works out of the
      box and tests are reproducible.
    - Portable — one DB file per project, trivially copyable.

CLI:
    python memory.py store "We chose SQLite over pgvector for portability"
    python memory.py recall "database choice"
    python memory.py list --kind decision
    python memory.py stats
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


# ---------------------------------------------------------------------------
# Embedder — deterministic fallback + pluggable interface
# ---------------------------------------------------------------------------

Embedder = Callable[[str], list[float]]
EMBEDDING_DIM = 256


def hash_embedder(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Deterministic, dependency-free text embedder using feature hashing.

    Not as good as a learned model, but sufficient for semantic-ish recall
    on short notes and 100% reproducible for tests. Every token in the text
    hashes to a bucket with a +/- sign; the vector is then L2-normalized.
    """
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        # Two hashes per token: one picks the bucket, one picks the sign.
        h1 = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).hexdigest(), 16)
        h2 = int(hashlib.blake2b(("sign:" + tok).encode("utf-8"), digest_size=4).hexdigest(), 16)
        bucket = h1 % dim
        sign = 1.0 if (h2 & 1) == 0 else -1.0
        vec[bucket] += sign
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9]+", text) if t]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    # Vectors are L2-normalized on store, but renormalize the query defensively.
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def openai_embedder(
    api_key: str | None = None,
    model: str = "text-embedding-3-small",
    *,
    endpoint: str = "https://api.openai.com/v1/embeddings",
    timeout: float = 30.0,
) -> Embedder:
    """Return an Embedder that calls OpenAI's embeddings API.

    Uses `urllib.request` — no `openai` package required. The returned callable
    raises on any HTTP error so recall failures are loud, not silent.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is not set and api_key was not provided")

    def _embed(text: str) -> list[float]:
        text = text or ""
        if not text.strip():
            return [0.0] * EMBEDDING_DIM
        return _http_embed(
            endpoint=endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            payload={"model": model, "input": text},
            timeout=timeout,
            response_path=("data", 0, "embedding"),
        )

    return _embed


def voyage_embedder(
    api_key: str | None = None,
    model: str = "voyage-3",
    *,
    input_type: str | None = None,
    endpoint: str = "https://api.voyageai.com/v1/embeddings",
    timeout: float = 30.0,
) -> Embedder:
    """Return an Embedder that calls Voyage AI's embeddings API.

    `input_type` may be 'query' or 'document' to get asymmetric embeddings.
    Falls back to None (symmetric) by default.
    """
    key = api_key or os.environ.get("VOYAGE_API_KEY")
    if not key:
        raise ValueError("VOYAGE_API_KEY is not set and api_key was not provided")

    def _embed(text: str) -> list[float]:
        text = text or ""
        if not text.strip():
            return [0.0] * EMBEDDING_DIM
        payload: dict[str, Any] = {"model": model, "input": [text]}
        if input_type:
            payload["input_type"] = input_type
        return _http_embed(
            endpoint=endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=timeout,
            response_path=("data", 0, "embedding"),
        )

    return _embed


def _http_embed(
    *,
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    response_path: tuple[Any, ...],
) -> list[float]:
    """POST JSON, navigate `response_path`, return a float list."""
    import urllib.error
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"embedding HTTP {e.code}: {detail}") from e
    node: Any = data
    for key in response_path:
        node = node[key]
    if not isinstance(node, list) or not all(isinstance(x, (int, float)) for x in node):
        raise RuntimeError("embedding response did not contain a numeric vector")
    return [float(x) for x in node]


def _encode_vec(vec: list[float]) -> bytes:
    return array.array("f", vec).tobytes()


def _decode_vec(blob: bytes | None) -> list[float]:
    if not blob:
        return []
    arr = array.array("f")
    arr.frombytes(blob)
    return list(arr)


# ---------------------------------------------------------------------------
# Memory store
# ---------------------------------------------------------------------------

VALID_KINDS = {
    # Original six — free-form content by role in the project.
    "note",          # generic observation, reminder, or scratch
    "decision",      # "we chose X over Y because Z"
    "state",         # current state of the project (overwrite-friendly)
    "question",      # open question awaiting resolution
    "session",       # session summary / what happened
    "fact",          # stable piece of knowledge (API shape, constant, etc.)
    # Expanded taxonomy — sharper recall, less noise at query time.
    "preference",    # user style preferences ("prefers dark mode", "hates emojis")
    "person",        # profile of a person mentioned across sessions
    "project_meta",  # repo topology, conventions, build/test commands
    "insight",       # non-obvious learning worth re-reading later
}


@dataclass
class Entry:
    id: int
    project: str
    kind: str
    content: str
    tags: list[str]
    created_at: str
    updated_at: str
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "id": self.id,
            "project": self.project,
            "kind": self.kind,
            "content": self.content,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.score is not None:
            out["score"] = round(self.score, 4)
        return out


class Memory:
    """SQLite-backed memory store with keyword + vector recall."""

    def __init__(
        self,
        db_path: str | Path = "claude_memory.db",
        embedder: Embedder | None = None,
    ) -> None:
        self.db_path = str(db_path)
        self.embedder: Embedder = embedder or hash_embedder
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    # -- schema ------------------------------------------------------------
    def _ensure_schema(self) -> None:
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        schema_sql = schema_path.read_text() if schema_path.exists() else _INLINE_SCHEMA
        self._conn.executescript(schema_sql)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Memory":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- store -------------------------------------------------------------
    def store(
        self,
        content: str,
        kind: str = "note",
        tags: Iterable[str] = (),
        project: str = "default",
    ) -> dict[str, Any]:
        content = (content or "").strip()
        if not content:
            raise ValueError("content is empty")
        if kind not in VALID_KINDS:
            raise ValueError(f"invalid kind: {kind!r} (allowed: {sorted(VALID_KINDS)})")
        tag_str = ",".join(sorted({t.strip() for t in tags if t and t.strip()}))
        now = _now_iso()
        vec = self.embedder(content)
        blob = _encode_vec(vec)
        cur = self._conn.execute(
            """INSERT INTO entries (project, kind, content, tags, created_at, updated_at, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project, kind, content, tag_str, now, now, blob),
        )
        self._conn.commit()
        entry_id = cur.lastrowid
        return self.get(entry_id)

    # -- recall ------------------------------------------------------------
    def recall(
        self,
        query: str,
        *,
        kind: str | None = None,
        project: str | None = None,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        query_vec = self.embedder(query)
        rows = self._fetch_rows(kind=kind, project=project)
        # Try FTS5 for keyword hits — it's usually tighter than cosine alone.
        fts_scores: dict[int, float] = {}
        try:
            fts_sql = "SELECT rowid, rank FROM entries_fts WHERE entries_fts MATCH ? ORDER BY rank LIMIT 200"
            for r in self._conn.execute(fts_sql, (_fts_sanitize(query),)):
                # rank is lower = better in bm25; invert to [0, 1]-ish
                fts_scores[r["rowid"]] = 1.0 / (1.0 + abs(r["rank"]))
        except sqlite3.OperationalError:
            # FTS table missing or query invalid — fall back to vector-only.
            fts_scores = {}
        scored: list[Entry] = []
        for row in rows:
            vec = _decode_vec(row["embedding"])
            vec_score = cosine(query_vec, vec) if vec else 0.0
            fts_score = fts_scores.get(row["id"], 0.0)
            # Weighted blend: vector 0.6, keyword 0.4. Bounds are soft.
            score = 0.6 * vec_score + 0.4 * fts_score
            if score < min_score:
                continue
            entry = _row_to_entry(row)
            entry.score = score
            scored.append(entry)
        scored.sort(key=lambda e: (e.score or 0.0), reverse=True)
        return [e.to_dict() for e in scored[:limit]]

    # -- list / get / update / delete -------------------------------------
    def list_entries(
        self,
        kind: str | None = None,
        project: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        rows = self._fetch_rows(kind=kind, project=project, limit=limit)
        return [_row_to_entry(r).to_dict() for r in rows]

    def get(self, entry_id: int) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no entry with id {entry_id}")
        return _row_to_entry(row).to_dict()

    def update(
        self,
        entry_id: int,
        content: str | None = None,
        tags: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        existing = self.get(entry_id)  # raises KeyError if missing
        new_content = content.strip() if content is not None else existing["content"]
        new_tags = (
            ",".join(sorted({t.strip() for t in tags if t and t.strip()}))
            if tags is not None
            else ",".join(existing["tags"])
        )
        new_vec = _encode_vec(self.embedder(new_content))
        self._conn.execute(
            """UPDATE entries SET content=?, tags=?, updated_at=?, embedding=? WHERE id=?""",
            (new_content, new_tags, _now_iso(), new_vec, entry_id),
        )
        self._conn.commit()
        return self.get(entry_id)

    def delete(self, entry_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def stats(self) -> dict[str, Any]:
        total = self._conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"]
        by_kind = {
            r["kind"]: r["n"]
            for r in self._conn.execute(
                "SELECT kind, COUNT(*) AS n FROM entries GROUP BY kind"
            )
        }
        by_project = {
            r["project"]: r["n"]
            for r in self._conn.execute(
                "SELECT project, COUNT(*) AS n FROM entries GROUP BY project"
            )
        }
        return {
            "total": total,
            "by_kind": by_kind,
            "by_project": by_project,
            "db_path": self.db_path,
        }

    # -- helpers -----------------------------------------------------------
    def _fetch_rows(
        self,
        kind: str | None = None,
        project: str | None = None,
        limit: int | None = None,
    ) -> list[sqlite3.Row]:
        sql = "SELECT * FROM entries WHERE 1=1"
        params: list[Any] = []
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY created_at DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return list(self._conn.execute(sql, params))


def _row_to_entry(row: sqlite3.Row) -> Entry:
    tags = [t for t in (row["tags"] or "").split(",") if t]
    return Entry(
        id=row["id"],
        project=row["project"],
        kind=row["kind"],
        content=row["content"],
        tags=tags,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _fts_sanitize(query: str) -> str:
    """FTS5 MATCH queries can choke on punctuation. Quote each token safely."""
    tokens = _tokenize(query)
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens)


# Fallback schema if the .sql file is missing (e.g. when memory.py is copied
# standalone). Kept in sync with schema.sql.
_INLINE_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project    TEXT NOT NULL DEFAULT 'default',
    kind       TEXT NOT NULL DEFAULT 'note',
    content    TEXT NOT NULL,
    tags       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    embedding  BLOB
);
CREATE INDEX IF NOT EXISTS idx_entries_project ON entries(project);
CREATE INDEX IF NOT EXISTS idx_entries_kind    ON entries(kind);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at DESC);
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    content, tags, content='entries', content_rowid='id',
    tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content, tags)
        VALUES('delete', old.id, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, content, tags)
        VALUES('delete', old.id, old.content, old.tags);
    INSERT INTO entries_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags);
END;
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_db_path() -> str:
    return os.environ.get("CLAUDE_MEMORY_DB") or str(
        Path(__file__).resolve().parent / "claude_memory.db"
    )


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Claude Memory CLI")
    parser.add_argument("--db", default=_default_db_path(), help="Path to the SQLite database")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_store = sub.add_parser("store", help="Store a memory entry")
    p_store.add_argument("content")
    p_store.add_argument("--kind", default="note", choices=sorted(VALID_KINDS))
    p_store.add_argument("--tags", default="", help="comma-separated tags")
    p_store.add_argument("--project", default="default")

    p_recall = sub.add_parser("recall", help="Recall entries matching a query")
    p_recall.add_argument("query")
    p_recall.add_argument("--kind")
    p_recall.add_argument("--project")
    p_recall.add_argument("--limit", type=int, default=5)
    p_recall.add_argument("--min-score", type=float, default=0.0)

    p_list = sub.add_parser("list", help="List recent entries")
    p_list.add_argument("--kind")
    p_list.add_argument("--project")
    p_list.add_argument("--limit", type=int, default=20)

    p_get = sub.add_parser("get", help="Get a single entry by id")
    p_get.add_argument("id", type=int)

    p_update = sub.add_parser("update", help="Update an entry")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--content")
    p_update.add_argument("--tags")

    p_delete = sub.add_parser("delete", help="Delete an entry")
    p_delete.add_argument("id", type=int)

    sub.add_parser("stats", help="Show database stats")

    args = parser.parse_args(argv)
    mem = Memory(args.db)
    try:
        if args.cmd == "store":
            tags = [t for t in args.tags.split(",") if t]
            _print_json(mem.store(args.content, kind=args.kind, tags=tags, project=args.project))
        elif args.cmd == "recall":
            _print_json(
                mem.recall(
                    args.query,
                    kind=args.kind,
                    project=args.project,
                    limit=args.limit,
                    min_score=args.min_score,
                )
            )
        elif args.cmd == "list":
            _print_json(mem.list_entries(kind=args.kind, project=args.project, limit=args.limit))
        elif args.cmd == "get":
            _print_json(mem.get(args.id))
        elif args.cmd == "update":
            tags = args.tags.split(",") if args.tags is not None else None
            _print_json(mem.update(args.id, content=args.content, tags=tags))
        elif args.cmd == "delete":
            ok = mem.delete(args.id)
            _print_json({"deleted": ok, "id": args.id})
        elif args.cmd == "stats":
            _print_json(mem.stats())
    finally:
        mem.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
