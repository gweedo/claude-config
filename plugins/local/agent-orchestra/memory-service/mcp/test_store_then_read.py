"""Walking-skeleton proof (issue #21): store a fact, read it back.

Exercises the same MemoryStore the MCP tools call, against the LIVE Postgres
container — proving every layer is wired: schema applied on `up`, the store
connects over localhost, a written triple comes back through a query.

Run inside the MCP image against the running postgres service:
    docker compose run --rm mcp-test
"""

from __future__ import annotations

import uuid

from memory_store import MemoryStore, Triple


def test_written_triple_is_returned_by_query() -> None:
    store = MemoryStore()

    # Unique subject so the test is idempotent across repeated runs.
    subject = f"AuthModule-{uuid.uuid4().hex[:8]}"
    written = store.write_triples(
        [Triple(subject=subject, predicate="DEPENDS_ON", object="RateLimiter")]
    )
    assert written == 1

    results = store.query_triples(subject)

    assert len(results) == 1
    fact = results[0]
    assert fact.subject == subject
    assert fact.predicate == "DEPENDS_ON"
    assert fact.object == "RateLimiter"


def test_query_for_unknown_subject_returns_empty() -> None:
    store = MemoryStore()
    assert store.query_triples(f"Nonexistent-{uuid.uuid4().hex}") == []
