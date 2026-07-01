"""Memory MCP server (stdio) — the only interface to memory (ADR-0002).

Exposes `memory_write`, `memory_query`, and `memory_supersede` over the stdio
transport. `memory_query` answers direct subject lookups, multi-hop "join"
questions (issue #22), and free-text semantic recall over stored chunks via a
local embedding model (issue #23) — graph and vector recall both read the same
live Postgres container. `memory_supersede` closes a stale fact. Entity-linking
(#25) arrives later. All DB work is delegated to MemoryStore; this module is
just the MCP transport + tool schemas.

Run:  python -m server            (from this directory, with deps installed)
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from memory_store import MemoryStore, Triple

mcp = FastMCP("agent-orchestra-memory")
_store = MemoryStore()


@mcp.tool()
def memory_write(triples: list[dict] | None = None, chunks: list[dict] | None = None) -> str:
    """Store facts and/or free text in the Memory service.

    `triples` (Context graph): each is an object {"subject", "predicate",
    "object", and optional "source_turn"}. Role agents emit these at handoff
    (ADR-0002).

    `chunks` (vector recall, #23): each is an object {"text", and optional
    "source_turn"}. Text is embedded by a local model inside this server (no
    external API/key) and stored for later semantic recall via `memory_query`.

    Either or both may be provided in one call. Returns a short confirmation of
    how many of each were written. Raises if neither is given, so a caller
    typo (e.g. a misspelled kwarg) surfaces immediately instead of silently
    writing nothing.
    """
    if not triples and not chunks:
        raise ValueError("memory_write requires at least one of: triples, chunks")
    parts = []
    if triples:
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
        parts.append(f"wrote {written} triple(s)")
    if chunks:
        chunk_count = sum(
            _store.write_chunk(c["text"], source_turn=c.get("source_turn")) for c in chunks
        )
        parts.append(f"wrote {chunk_count} chunk(s)")
    return ", ".join(parts)


@mcp.tool()
def memory_query(
    subject: str | None = None,
    traverse: bool = False,
    text: str | None = None,
    top_k: int = 5,
) -> str:
    """Recall from the Memory service: the Context graph and/or vector chunks.

    Graph recall (`subject`): with `traverse=False` (default) returns the
    current triples whose subject matches, as JSON. Superseded facts are never
    returned. With `traverse=True` it answers a multi-hop "join" question: it
    walks the graph from `subject` and returns every node reached with its hop
    `depth` and the final-hop `predicate`. Use this when the answer is not in
    any single triple — e.g. what a module *transitively* reaches two hops out.

    Vector recall (`text`, #23): embeds the free-text query with the same
    local model used to write chunks and returns the `top_k` most
    semantically-similar stored chunks, ranked by cosine `distance` (lower is
    more similar). Use this for free-text questions no exact subject match or
    graph traversal can answer.

    Pass `subject` and/or `text` — both recall modes read the same live
    container and can be combined in one call. Returns a JSON object with
    "triples" and/or "chunks" keys for whichever modes were requested. Raises
    if neither is given, so a caller typo surfaces immediately instead of
    silently returning an empty object.
    """
    if not subject and not text:
        raise ValueError("memory_query requires at least one of: subject, text")
    result: dict[str, object] = {}
    if subject:
        if traverse:
            paths = _store.query_join(subject)
            result["triples"] = [
                {"object": p.object, "predicate": p.predicate, "depth": p.depth}
                for p in paths
            ]
        else:
            triples_out = _store.query_triples(subject)
            result["triples"] = [
                {
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "source_turn": t.source_turn,
                }
                for t in triples_out
            ]
    if text:
        chunks_out = _store.query_chunks(text, top_k=top_k)
        result["chunks"] = [
            {"text": c.text, "source_turn": c.source_turn, "distance": c.distance}
            for c in chunks_out
        ]
    return json.dumps(result)


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
