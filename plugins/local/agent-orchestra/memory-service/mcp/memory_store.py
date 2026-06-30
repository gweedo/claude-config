"""Memory store — the deep module behind the Memory MCP server.

This holds all SQL for the walking skeleton (issue #21): write triples, query
them back. The MCP transport layer (server.py) is a thin wrapper over this; the
store is what the integration test exercises directly so the store-then-read
proof does not depend on spawning a stdio subprocess.

Forward-looking note: entity-linking and superseding (ADR-0002) will live here
too once Phase 2 lands. For the skeleton, querying is a simple subject match.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import psycopg


@dataclass(frozen=True)
class Triple:
    """A single stored fact: (subject, predicate, object). See CONTEXT.md."""

    subject: str
    predicate: str
    object: str
    source_turn: str | None = None


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

    def query_triples(self, subject: str) -> list[Triple]:
        """Return all triples whose subject matches (most recent first).

        Subject-keyed lookup is the walking skeleton's only query path; richer
        graph traversal + vector recall arrive in later phases.
        """
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT subject, predicate, object, source_turn "
                "FROM triples WHERE subject = %s ORDER BY id DESC",
                (subject,),
            )
            return [
                Triple(subject=r[0], predicate=r[1], object=r[2], source_turn=r[3])
                for r in cur.fetchall()
            ]
