"""Memory MCP server (stdio) — the only interface to memory (ADR-0002).

Exposes `memory_write`, `memory_query`, and `memory_supersede` over the stdio
transport. `memory_query` answers both direct subject lookups and multi-hop
"join" questions (issue #22); `memory_supersede` closes a stale fact. Entity-
linking (#25) and vector recall (#23) arrive later. All DB work is delegated to
MemoryStore; this module is just the MCP transport + tool schemas.

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
def memory_query(subject: str, traverse: bool = False) -> str:
    """Recall facts about a subject from the Context graph.

    With `traverse=False` (default) this returns the current triples whose
    subject matches, as JSON. Superseded facts are never returned.

    With `traverse=True` it answers a multi-hop "join" question: it walks the
    graph from `subject` and returns every node reached with its hop `depth` and
    the final-hop `predicate`. Use this when the answer is not in any single
    triple — e.g. what a module *transitively* reaches two hops out.
    """
    if traverse:
        paths = _store.query_join(subject)
        return json.dumps(
            [{"object": p.object, "predicate": p.predicate, "depth": p.depth} for p in paths]
        )
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


@mcp.tool()
def memory_supersede(subject: str, predicate: str, object: str) -> str:
    """Mark a fact no longer current when a newer one replaces it.

    Closes the matching current triple's `valid_to` (bitemporal) rather than
    deleting it, so history is retained but queries stop returning it (ADR-0002,
    CONTEXT.md "Supersede"). Write the replacement fact separately via
    `memory_write`. Returns how many triples were closed.
    """
    closed = _store.supersede(subject=subject, predicate=predicate, object=object)
    return f"superseded {closed} triple(s)"


if __name__ == "__main__":
    mcp.run()
