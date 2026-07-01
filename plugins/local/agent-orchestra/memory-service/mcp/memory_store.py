"""Memory store — the deep module behind the Memory MCP server.

Holds all SQL for the Context graph: write triples, query them back, traverse
multiple hops, and supersede a changed fact. The MCP transport layer
(server.py) is a thin wrapper over this; the store is what the integration
tests exercise directly so the proofs do not depend on spawning a stdio
subprocess.

Two ideas from issue #22 live here:

- Bitemporal validity. A triple is *current* while `valid_to IS NULL`. Reads
  filter to the current view by default; supersede closes `valid_to` instead of
  deleting, so history is retained.
- Multi-hop traversal. `query_join` walks the graph via a recursive CTE to
  answer "join" questions no single triple holds (the article's differentiator
  over vector similarity).

Vector recall (#23) lives here too: free text is embedded by a local
sentence-transformers model (loaded once, lazily, at process start — no
external API/key, per ADR-0002) and stored in the `chunks` table; queries embed
the question the same way and rank chunks by cosine distance via pgvector's
`<=>` operator. Graph and vector recall are independent methods on the same
store, reading/writing the same live Postgres container.

Forward-looking note: entity-linking (#25) will join these here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import psycopg
from pgvector.psycopg import register_vector

# Small, CPU-friendly, fully local model — no external API/key (ADR-0002).
# 384-dim output, matching the `chunks.embedding` column in schema.sql.
_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class Triple:
    """A single stored fact: (subject, predicate, object). See CONTEXT.md."""

    subject: str
    predicate: str
    object: str
    source_turn: str | None = None


@dataclass(frozen=True)
class Path:
    """A node reached by traversing the Context graph from a start subject.

    `object` is the node reached and `depth` is how many hops it took (1 = a
    direct triple, 2 = a node reachable only by joining two triples). `predicate`
    is the relation of the final hop that landed on `object`. Returned by
    `query_join` to answer multi-hop questions no single triple holds.
    """

    object: str
    predicate: str
    depth: int


@dataclass(frozen=True)
class Chunk:
    """A stored piece of free text recalled by meaning, not exact match.

    The unit of vector recall (#23), analogous to `Triple` for the graph half.
    `distance` is the cosine distance from the query embedding (lower = more
    similar); it is None for a freshly written chunk that was not returned by
    a similarity search.
    """

    text: str
    source_turn: str | None = None
    distance: float | None = None


_model = None


def _embedding_model():
    """Lazily load the local embedding model (once per process).

    Loaded on first use rather than at import time so importing this module
    (e.g. for the store-then-read graph tests) never pays the model-load cost.
    No network access at call time — the Dockerfile pre-downloads the weights
    into the image, so this is a local, offline load (ADR-0002).
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    return _model


def embed(text: str) -> list[float]:
    """Embed `text` with the local model. Returns a 384-dim vector."""
    vector = _embedding_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def connection_string() -> str:
    """Postgres DSN for the per-project Memory container.

    Reads MEMORY_DATABASE_URL if set (how the MCP server is configured in the
    devcontainer); otherwise defaults to the localhost-bound port from
    docker-compose.yml so local runs work with zero config.
    """
    return os.environ.get(
        "MEMORY_DATABASE_URL",
        "postgresql://orchestra:orchestra@127.0.0.1:5433/orchestra",
    )


class MemoryStore:
    """Connects to the Memory service and reads/writes triples."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or connection_string()

    def _connect(self) -> psycopg.Connection:
        """Open a connection with the pgvector type adapter registered.

        Every method that touches `chunks` needs this so the `vector` column
        round-trips as a Python list rather than pgvector's raw text format.
        """
        conn = psycopg.connect(self._dsn)
        register_vector(conn)
        return conn

    def write_triples(self, triples: Iterable[Triple]) -> int:
        """Store triples. Returns the number written."""
        rows = [
            (t.subject, t.predicate, t.object, t.source_turn) for t in triples
        ]
        if not rows:
            return 0
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO triples (subject, predicate, object, source_turn) "
                "VALUES (%s, %s, %s, %s)",
                rows,
            )
            conn.commit()
        return len(rows)

    def query_triples(
        self, subject: str, *, include_superseded: bool = False
    ) -> list[Triple]:
        """Return triples whose subject matches (most recent first).

        By default only *current* triples are returned (`valid_to IS NULL`), so a
        superseded fact no longer appears. Pass `include_superseded=True` to see
        the full history including closed rows.
        """
        sql = (
            "SELECT subject, predicate, object, source_turn "
            "FROM triples WHERE subject = %s"
        )
        if not include_superseded:
            sql += " AND valid_to IS NULL"
        sql += " ORDER BY id DESC"
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (subject,))
            return [
                Triple(subject=r[0], predicate=r[1], object=r[2], source_turn=r[3])
                for r in cur.fetchall()
            ]

    def query_join(self, subject: str, *, max_depth: int = 2) -> list[Path]:
        """Traverse the Context graph from `subject`, following current edges.

        Walks up to `max_depth` hops via a recursive CTE and returns every node
        reached with the depth and final-hop predicate. This answers "join"
        questions no single triple holds — e.g. from AuthModule, reaching Redis
        at depth 2 via (AuthModule DEPENDS_ON RateLimiter) + (RateLimiter USES
        Redis). Only current triples (`valid_to IS NULL`) are traversed, so a
        superseded hop drops out of every path through it.

        A cycle guard (`%s = ANY(visited)`) prevents infinite loops if the graph
        contains a cycle within max_depth.
        """
        sql = """
            WITH RECURSIVE walk AS (
                SELECT t.object AS node,
                       t.predicate AS predicate,
                       1 AS depth,
                       ARRAY[t.subject, t.object] AS visited
                FROM triples t
                WHERE t.subject = %(start)s AND t.valid_to IS NULL

                UNION ALL

                SELECT t.object,
                       t.predicate,
                       w.depth + 1,
                       w.visited || t.object
                FROM triples t
                JOIN walk w ON t.subject = w.node
                WHERE t.valid_to IS NULL
                  AND w.depth < %(max_depth)s
                  AND NOT (t.object = ANY(w.visited))
            )
            SELECT node, predicate, depth FROM walk ORDER BY depth, node
        """
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, {"start": subject, "max_depth": max_depth})
            return [Path(object=r[0], predicate=r[1], depth=r[2]) for r in cur.fetchall()]

    def supersede(self, *, subject: str, predicate: str, object: str) -> int:
        """Mark matching current triples as no longer valid (bitemporal close).

        Closes `valid_to` on every current triple matching (subject, predicate,
        object) rather than deleting it (see CONTEXT.md "Supersede"). Returns how
        many rows were closed (0 if no current match). The replacement fact, if
        any, is written separately via `write_triples`.
        """
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE triples SET valid_to = now() "
                "WHERE subject = %s AND predicate = %s AND object = %s "
                "AND valid_to IS NULL",
                (subject, predicate, object),
            )
            closed = cur.rowcount
            conn.commit()
        return closed

    def write_chunk(self, text: str, *, source_turn: str | None = None) -> int:
        """Embed `text` with the local model and store it for vector recall.

        Returns 1 on success (mirrors `write_triples`' "count written" shape).
        No external API call — embedding happens in-process (ADR-0002).
        """
        vector = embed(text)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chunks (text, embedding, source_turn) VALUES (%s, %s, %s)",
                (text, vector, source_turn),
            )
            conn.commit()
        return 1

    def query_chunks(self, query: str, *, top_k: int = 5) -> list[Chunk]:
        """Recall the `top_k` chunks most semantically similar to `query`.

        Embeds `query` with the same local model used to write chunks, then
        ranks stored chunks by cosine distance via pgvector's `<=>` operator
        (ANN search using the `chunks_embedding_idx` ivfflat index). This is
        the vector-recall counterpart to `query_triples`/`query_join` — it
        answers free-text questions no exact subject match or graph traversal
        can, and always ranks by similarity rather than requiring a threshold.
        """
        vector = embed(query)
        with self._connect() as conn, conn.cursor() as cur:
            # Probe more of the ivfflat index than the default (1) so recall
            # stays good as the table grows past the small size `lists` was
            # tuned for (schema.sql) — cheap for a per-project, low-QPS store.
            cur.execute("SET ivfflat.probes = 10")
            cur.execute(
                "SELECT text, source_turn, embedding <=> %s::vector AS distance "
                "FROM chunks ORDER BY distance ASC LIMIT %s",
                (vector, top_k),
            )
            return [
                Chunk(text=r[0], source_turn=r[1], distance=r[2]) for r in cur.fetchall()
            ]
