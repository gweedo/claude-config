"""Bitemporal supersede proof (issue #22): change a fact without deleting it.

A re-stated fact replaces the old one by *closing* the prior triple's valid_to
(bitemporal), not by deleting the row. Queries return only current triples, so
the stale fact stops appearing — but the history row is still on disk.

Runs inside the MCP image against the live postgres service:
    docker compose --profile test run --rm mcp-test
"""

from __future__ import annotations

import uuid

from memory_store import MemoryStore, Triple


def test_supersede_hides_stale_fact_from_query() -> None:
    store = MemoryStore()
    subject = f"AuthModule-{uuid.uuid4().hex[:8]}"

    # Original decision: auth uses sessions.
    store.write_triples([Triple(subject=subject, predicate="USES", object="Sessions")])
    assert {t.object for t in store.query_triples(subject)} == {"Sessions"}

    # Decision changed: it now uses JWT. Close the old fact, write the new one.
    closed = store.supersede(subject=subject, predicate="USES", object="Sessions")
    assert closed == 1
    store.write_triples([Triple(subject=subject, predicate="USES", object="JWT")])

    # The query returns only the current fact; the stale one is gone.
    objects = {t.object for t in store.query_triples(subject)}
    assert objects == {"JWT"}, objects


def test_supersede_does_not_delete_history() -> None:
    # Superseding closes valid_to; the historical row is retained, not deleted.
    store = MemoryStore()
    subject = f"PaymentService-{uuid.uuid4().hex[:8]}"

    store.write_triples([Triple(subject=subject, predicate="STATUS", object="Beta")])
    store.supersede(subject=subject, predicate="STATUS", object="Beta")

    # Current view: empty (the only fact was closed).
    assert store.query_triples(subject) == []
    # History view: the closed row is still present.
    history = store.query_triples(subject, include_superseded=True)
    assert len(history) == 1
    assert history[0].object == "Beta"


def test_supersede_unknown_fact_closes_nothing() -> None:
    store = MemoryStore()
    subject = f"Nonexistent-{uuid.uuid4().hex}"
    assert store.supersede(subject=subject, predicate="USES", object="Nothing") == 0
