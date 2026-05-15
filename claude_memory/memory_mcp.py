#!/usr/bin/env python3
"""Claude Memory MCP server — exposes the Memory library as MCP tools so
Claude can call memory_store / memory_recall / memory_list / memory_get /
memory_update / memory_delete / memory_stats as native tools.

Register in your MCP client config:

    {
      "mcpServers": {
        "claude-memory": {
          "command": "python",
          "args": ["/absolute/path/to/claude_memory/memory_mcp.py"],
          "env": { "CLAUDE_MEMORY_DB": "/absolute/path/to/claude_memory.db" }
        }
      }
    }

Requires: `pip install mcp` (Anthropic's official MCP SDK). The underlying
memory.py has zero third-party dependencies — the MCP wrapper is optional.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Make memory.py importable whether launched from any cwd
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from memory import VALID_KINDS, Memory  # noqa: E402


def _db_path() -> str:
    return os.environ.get("CLAUDE_MEMORY_DB") or str(_HERE / "claude_memory.db")


TOOL_SPECS = [
    {
        "name": "memory_store",
        "description": (
            "Persist a piece of information to long-term memory. Use for "
            "decisions, project state, facts, or anything that should "
            "survive beyond this conversation. Do not use for trivia."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The text to remember."},
                "kind": {
                    "type": "string",
                    "enum": sorted(VALID_KINDS),
                    "description": "Classification of this memory.",
                    "default": "note",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Free-form tags for later filtering.",
                    "default": [],
                },
                "project": {
                    "type": "string",
                    "description": "Project namespace. Defaults to 'default'.",
                    "default": "default",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_recall",
        "description": (
            "Retrieve memories relevant to a query. Combines keyword search "
            "(FTS5) and vector similarity. Call this at the start of every "
            "session with the user's opening message as the query."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language query."},
                "kind": {
                    "type": "string",
                    "enum": sorted(VALID_KINDS),
                    "description": "Filter by memory kind.",
                },
                "project": {"type": "string", "description": "Filter by project."},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                "min_score": {"type": "number", "default": 0.0, "minimum": 0.0, "maximum": 1.0},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_list",
        "description": "List recent memory entries, optionally filtered by kind or project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": sorted(VALID_KINDS)},
                "project": {"type": "string"},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
            },
        },
    },
    {
        "name": "memory_get",
        "description": "Fetch a single memory entry by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "memory_update",
        "description": "Update an existing memory entry's content or tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["id"],
        },
    },
    {
        "name": "memory_delete",
        "description": "Delete a memory entry by id. Irreversible.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "memory_stats",
        "description": "Show memory database statistics (counts by kind and project).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_tool(name: str, args: dict, mem: Memory) -> dict:
    """Dispatch a tool call. Returns a JSON-serializable dict."""
    if name == "memory_store":
        return mem.store(
            content=args["content"],
            kind=args.get("kind", "note"),
            tags=args.get("tags", []) or [],
            project=args.get("project", "default"),
        )
    if name == "memory_recall":
        return {
            "results": mem.recall(
                query=args["query"],
                kind=args.get("kind"),
                project=args.get("project"),
                limit=int(args.get("limit", 5)),
                min_score=float(args.get("min_score", 0.0)),
            )
        }
    if name == "memory_list":
        return {
            "results": mem.list_entries(
                kind=args.get("kind"),
                project=args.get("project"),
                limit=int(args.get("limit", 20)),
            )
        }
    if name == "memory_get":
        return mem.get(int(args["id"]))
    if name == "memory_update":
        return mem.update(
            entry_id=int(args["id"]),
            content=args.get("content"),
            tags=args.get("tags"),
        )
    if name == "memory_delete":
        return {"deleted": mem.delete(int(args["id"])), "id": int(args["id"])}
    if name == "memory_stats":
        return mem.stats()
    raise ValueError(f"unknown tool: {name}")


# ---------------------------------------------------------------------------
# MCP server entrypoint (requires the `mcp` package)
# ---------------------------------------------------------------------------

async def _run_mcp() -> None:
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        print(
            "The 'mcp' package is required to run the MCP server.\n"
            "Install it with:  pip install mcp\n"
            f"(import error: {exc})",
            file=sys.stderr,
        )
        raise SystemExit(2)

    server = Server("claude-memory")
    mem = Memory(_db_path())

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=spec["name"],
                description=spec["description"],
                inputSchema=spec["inputSchema"],
            )
            for spec in TOOL_SPECS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        try:
            result = handle_tool(name, arguments or {}, mem)
            payload = json.dumps(result, indent=2, sort_keys=True, default=str)
            return [TextContent(type="text", text=payload)]
        except Exception as exc:  # surfaced to the model as a tool error
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    try:
        asyncio.run(_run_mcp())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
