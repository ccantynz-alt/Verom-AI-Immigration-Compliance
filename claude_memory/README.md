# Claude Memory

Portable, file-based memory for Claude across sessions and projects.

Three layers:

1. **Markdown you can read** — `memory/project-state.md`, `last-session.md`,
   `decisions-log.md`, `open-questions.md`. Edit by hand any time.
2. **SQLite + FTS5 + vector search** — `memory.py`, one `.db` file per
   project. Keyword and semantic recall in a single query.
3. **MCP server** — `memory_mcp.py` exposes `memory_store`, `memory_recall`,
   `memory_list`, `memory_get`, `memory_update`, `memory_delete`, and
   `memory_stats` as native tools.

## Quick start

```bash
# 1. Core library has no deps. Just run it.
python memory.py store "We picked SQLite over Postgres for portability" --kind decision --tags infra,db
python memory.py recall "database choice"
python memory.py list --kind decision
python memory.py stats

# 2. For the MCP server, install the MCP SDK
pip install -r requirements.txt
python memory_mcp.py  # stdio server, wire into your MCP client
```

## Wiring into your Claude client

Add this to your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`
or any Agent SDK client):

```json
{
  "mcpServers": {
    "claude-memory": {
      "command": "python",
      "args": ["/absolute/path/to/claude_memory/memory_mcp.py"],
      "env": {
        "CLAUDE_MEMORY_DB": "/absolute/path/to/claude_memory.db"
      }
    }
  }
}
```

Once registered, Claude can call `memory_recall` and `memory_store` like any
other tool — no shell commands, no file reads.

## Wiring into a system prompt

Inject `CLAUDE.md` as (part of) your system prompt. The eight-section
constitution tells Claude to:

- **Section 1:** call `memory_recall` before responding in a new session
- **Section 2:** obey three hard rules (no preamble/hedging, finish what you
  start, don't re-ask what's decided)
- **Section 6:** call `memory_store` at session end
- **Section 8:** provide escape hatches so the rules never trap you when you
  just want a quick answer

If the MCP server isn't registered, Section 1 falls back to reading the
markdown files directly. Either path works.

## Pain-point mapping

| Pain point                                  | CLAUDE.md rule         | Memory layer                    |
| ------------------------------------------- | ---------------------- | ------------------------------- |
| "Why is Claude so verbose / sycophantic?"   | Rule 1                 | —                               |
| "Claude left the task half-done."           | Rule 2                 | —                               |
| "I already told Claude this last session."  | Rule 3                 | `memory_recall` + decisions log |
| "Claude forgot what we decided in week 1."  | Section 1, Section 6   | SQLite + markdown               |
| "Claude drifts after 40 turns."             | Section 5              | `memory check` manual reload    |

## Schema

```
entries (id, project, kind, content, tags, created_at, updated_at, embedding)
entries_fts (FTS5 over content + tags, auto-maintained)
```

`kind` is one of:

| Kind | Use for |
| --- | --- |
| `note` | generic observation or scratch |
| `decision` | "we chose X over Y because Z" — append to decisions log |
| `state` | current state of the project (overwrite-friendly) |
| `question` | open question awaiting resolution |
| `session` | session summary / what happened |
| `fact` | stable knowledge (API shape, constant, URL) |
| `preference` | user style preferences ("prefers dark mode", "no emojis") |
| `person` | profile of a person mentioned across sessions |
| `project_meta` | repo topology, conventions, build/test commands |
| `insight` | non-obvious learning worth re-reading later |

Sharper kinds mean sharper recall — filtering by `kind=preference` at session
start surfaces the user's style preferences without dragging in unrelated
notes.

## Recall scoring

Hybrid: `0.6 * cosine(vec) + 0.4 * bm25_normalized(fts)`. The embedder is
pluggable — the default `hash_embedder` is deterministic and dependency-free.

### Pluggable embedders

```python
from memory import Memory, openai_embedder, voyage_embedder

# Default: hash-based, no network, reproducible
mem = Memory("claude_memory.db")

# OpenAI (reads OPENAI_API_KEY from env if api_key is omitted)
mem = Memory("claude_memory.db", embedder=openai_embedder(model="text-embedding-3-small"))

# Voyage (reads VOYAGE_API_KEY from env)
mem = Memory("claude_memory.db", embedder=voyage_embedder(model="voyage-3"))
```

The factories use `urllib.request` — no `openai` or `voyageai` packages
required. Both raise on missing API key at construction time (fail fast) and
raise on HTTP errors at embed time (fail loud). A database built with one
embedder should not be reused with another of a different dimension.

## Environment variables

- `CLAUDE_MEMORY_DB` — path to the SQLite database (default:
  `./claude_memory.db` next to `memory.py`)

## Portability

The entire `claude_memory/` folder is drop-in. Zip it, move it, commit it,
rsync it — no native extensions, no external services. One folder, one
`.db`, done.

## Override pattern

When you want Claude to skip the constitution for one turn, use any of the
keywords from Section 8: `quick`, `just give me`, `brainstorm`, `scratch
that`, `explain your reasoning`. Overrides are scoped to a single turn
unless extended.
