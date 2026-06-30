"""Context-graph proof (issue #22): a two-hop join no single triple answers.

The article's core differentiator over vector RAG: a question whose answer is
not stored in any one triple, but emerges by *traversing* the graph. We store
two separate facts:

    (AuthModule  DEPENDS_ON  RateLimiter)
    (RateLimiter USES        Redis)

No single triple says "AuthModule reaches Redis". A recursive-CTE traversal from
AuthModule must follow both hops to surface Redis at depth 2.

Runs inside the MCP image against the live postgres service:
    docker compose --profile test run --rm mcp-test
"""

from __future__ import annotations

import uuid

from memory_store import MemoryStore, Triple


def test_two_hop_traversal_reaches_node_no_single_triple_names() -> None:
    store = MemoryStore()

    # Unique node names so the test is idempotent across repeated runs.
    tag = uuid.uuid4().hex[:8]
    auth = f"AuthModule-{tag}"
    limiter = f"RateLimiter-{tag}"
    redis = f"Redis-{tag}"

    store.write_triples(
        [
            Triple(subject=auth, predicate="DEPENDS_ON", object=limiter),
            Triple(subject=limiter, predicate="USES", object=redis),
        ]
    )

    paths = store.query_join(auth)

    # The endpoint reachable only by joining the two hops is Redis, at depth 2.
    reached = {(p.object, p.depth) for p in paths}
    assert (limiter, 1) in reached, paths
    assert (redis, 2) in reached, paths


def test_traversal_skips_superseded_hops() -> None:
    # A traversal must not route through a hop whose valid_to has been closed.
    store = MemoryStore()
    tag = uuid.uuid4().hex[:8]
    auth = f"AuthModule-{tag}"
    limiter = f"RateLimiter-{tag}"
    redis = f"Redis-{tag}"

    store.write_triples(
        [
            Triple(subject=auth, predicate="DEPENDS_ON", object=limiter),
            Triple(subject=limiter, predicate="USES", object=redis),
        ]
    )
    # The RateLimiter no longer uses Redis -> close that second hop.
    store.supersede(subject=limiter, predicate="USES", object=redis)

    paths = store.query_join(auth)
    reached = {p.object for p in paths}
    assert limiter in reached, paths
    assert redis not in reached, paths
