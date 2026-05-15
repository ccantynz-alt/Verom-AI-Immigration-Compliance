-- Claude Memory schema. SQLite with FTS5 for keyword search and a BLOB
-- column for optional vector embeddings. Cosine similarity is computed in
-- Python at recall time so the schema works everywhere without extensions.

CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project    TEXT NOT NULL DEFAULT 'default',
    kind       TEXT NOT NULL DEFAULT 'note',    -- note | decision | state | question | session | fact
    content    TEXT NOT NULL,
    tags       TEXT NOT NULL DEFAULT '',         -- comma-separated
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    embedding  BLOB                              -- float32 vector, may be NULL
);

CREATE INDEX IF NOT EXISTS idx_entries_project ON entries(project);
CREATE INDEX IF NOT EXISTS idx_entries_kind    ON entries(kind);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at DESC);

-- Full-text search index — auto-maintained via triggers.
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    content,
    tags,
    content='entries',
    content_rowid='id',
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
