"""Memory MCP server (stdio) — the only interface to memory (ADR-0002).

Walking skeleton (issue #21): exposes `memory_write` and `memory_query` over the
stdio transport. `memory_supersede`, entity-linking, and vector recall arrive in
Phase 2. All DB work is delegated to MemoryStore; this module is just the
MCP transport + tool schemas.

Run:  python -m server            (from this directory, with deps installed)
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from memory_store import MemoryStore, Triple

mcp = FastMCP("agent-orchestra-memory")
_store = MemoryStore()


@mcp.tool()
def memory_write(triples: list[dict]) -> str:
    """Store facts in the Context graph.

    Each triple is an object {"subject", "predicate", "object", and optional
    "source_turn"}. Role agents emit these at handoff (ADR-0002). Returns a
    short confirmation of how many were written.
    """
    parsed = [
        Triple(
            subject=t["subject"],
            predicate=t["predicate"],
            object=t["object"],
            source_turn=t.get("source_turn"),
        )
        for t in triples
    ]
    written = _store.write_triples(parsed)
    return f"wrote {written} triple(s)"


@mcp.tool()
def memory_query(subject: str) -> str:
    """Recall facts about a subject from the Context graph.

    Returns matching triples as JSON. For the walking skeleton this is a direct
    subject match; richer traversal + vector recall arrive in later phases.
    """
    results = _store.query_triples(subject)
    return json.dumps(
        [
            {
                "subject": t.subject,
                "predicate": t.predicate,
                "object": t.object,
                "source_turn": t.source_turn,
            }
            for t in results
        ]
    )


if __name__ == "__main__":
    mcp.run()
