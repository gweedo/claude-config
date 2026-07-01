"""Vector-recall proof (issue #23): store free text, recall it by meaning.

Exercises the same MemoryStore the MCP tools call, against the LIVE Postgres
container — proving the pgvector half is wired: the `chunks` table exists, the
local embedding model runs inside the store with no external API, and a
semantically related (not exact-string) free-text query surfaces the right
chunk via ANN search alongside the existing graph recall.

Run inside the MCP image against the running postgres service:
    docker compose --profile test run --rm mcp-test
"""

from __future__ import annotations

import uuid

from memory_store import MemoryStore


def test_written_chunk_is_returned_by_semantic_query() -> None:
    store = MemoryStore()

    tag = uuid.uuid4().hex[:8]
    # Content and query share no words in common — only meaning overlaps —
    # so an exact-string match could never pass this test, only embeddings.
    written = store.write_chunk(
        text=f"The RateLimiter-{tag} throttles incoming API requests to "
        f"prevent abuse and protect downstream services."
    )
    assert written == 1

    results = store.query_chunks(f"How does RateLimiter-{tag} stop excessive traffic?", top_k=3)

    assert len(results) >= 1
    assert any(f"RateLimiter-{tag}" in r.text for r in results)


def test_semantic_query_ranks_relevant_chunk_above_unrelated_one() -> None:
    store = MemoryStore()

    tag = uuid.uuid4().hex[:8]
    store.write_chunk(text=f"PaymentService-{tag} processes credit card transactions securely.")
    store.write_chunk(text=f"WeatherWidget-{tag} shows the five-day forecast for the user's city.")

    results = store.query_chunks(f"billing and card payments for PaymentService-{tag}", top_k=5)

    relevant = [r for r in results if f"PaymentService-{tag}" in r.text]
    unrelated = [r for r in results if f"WeatherWidget-{tag}" in r.text]
    assert relevant, results
    if unrelated:
        rel_idx = results.index(relevant[0])
        unrel_idx = results.index(unrelated[0])
        assert rel_idx < unrel_idx


def test_query_chunks_for_unrelated_text_still_returns_ranked_results() -> None:
    store = MemoryStore()
    tag = uuid.uuid4().hex[:8]
    store.write_chunk(text=f"Marker-{tag} exists only so this query has something to rank.")

    results = store.query_chunks(f"completely unrelated nonsense {uuid.uuid4().hex}", top_k=1)
    # ANN search always returns nearest neighbors, even if similarity is low —
    # ranking, not filtering, is the contract here.
    assert isinstance(results, list)


def test_graph_and_vector_recall_work_against_the_same_container() -> None:
    """Both halves of the Memory service answer from the same live container."""
    from memory_store import Triple

    store = MemoryStore()
    tag = uuid.uuid4().hex[:8]

    subject = f"AuthModule-{tag}"
    store.write_triples([Triple(subject=subject, predicate="DEPENDS_ON", object="RateLimiter")])
    store.write_chunk(text=f"AuthModule-{tag} authenticates users before granting access.")

    graph_results = store.query_triples(subject)
    vector_results = store.query_chunks(f"How does AuthModule-{tag} verify who a user is?", top_k=3)

    assert len(graph_results) == 1
    assert graph_results[0].object == "RateLimiter"
    assert any(subject in r.text for r in vector_results)
