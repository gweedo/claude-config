-- agent-orchestra Memory service schema (Context graph + vector recall,
-- issues #21–#23).
--
-- Facts are stored as (subject, predicate, object) triples — the unit of the
-- Context graph (see CONTEXT.md). Bitemporal validity columns let a changed fact
-- *supersede* an old one by closing valid_to rather than deleting the row, so
-- history is retained while queries see only the current view (#22). The
-- pgvector `chunks` table below is the vector/RAG half (#23): free text is
-- embedded by a local model inside the MCP server (no external API) and
-- recalled by nearest-neighbor search alongside graph traversal.
--
-- Applied automatically on first `docker compose up` via the postgres image's
-- /docker-entrypoint-initdb.d mount (see docker-compose.yml).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS triples (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject     TEXT NOT NULL,
    predicate   TEXT NOT NULL,
    object      TEXT NOT NULL,
    source_turn TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Bitemporal validity: a triple is current while valid_to IS NULL.
    -- Superseding closes valid_to (#22); the row is never deleted.
    valid_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to    TIMESTAMPTZ
);

-- Subject lookups are the common graph-traversal entry point.
CREATE INDEX IF NOT EXISTS triples_subject_idx   ON triples (subject);
CREATE INDEX IF NOT EXISTS triples_predicate_idx ON triples (predicate);
-- Current-view filtering (valid_to IS NULL) is on the hot path for every query
-- and every traversal hop.
CREATE INDEX IF NOT EXISTS triples_current_idx ON triples (subject) WHERE valid_to IS NULL;

-- Vector recall (#23): free-text chunks embedded by a local model in the MCP
-- server. 384 dims matches sentence-transformers/all-MiniLM-L6-v2, the local
-- embedding model the MCP server loads (see mcp/memory_store.py) — no external
-- API key required.
CREATE TABLE IF NOT EXISTS chunks (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    text        TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    source_turn TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ANN index for nearest-neighbor recall. ivfflat with cosine distance (vector
-- similarity, not exact-match) — matches the <=> operator used in queries.
-- `lists = 1` matches pgvector's own guidance for small tables (rule of thumb
-- ~rows/1000 for rows > 1M; below that, few lists). A per-project Memory
-- store stays small (hundreds to low thousands of chunks), and too many lists
-- relative to row count starves each cluster and *hurts* recall — the
-- opposite of an ANN index's job. Revisit (grow `lists`, raise `ivfflat.probes`)
-- if chunk volume grows materially.
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1);
