-- agent-orchestra Memory service schema (walking skeleton, issue #21).
--
-- This is the THINNEST useful slice of the Context graph: a minimal triples
-- table that stores facts as (subject, predicate, object). The full bitemporal
-- columns (valid_from / valid_to for superseding) and the pgvector `chunks`
-- table arrive in build Phase 1/2 (issues #22+). Kept intentionally small here
-- so the walking skeleton proves the wiring, not the feature set.
--
-- Applied automatically on first `docker compose up` via the postgres image's
-- /docker-entrypoint-initdb.d mount (see docker-compose.yml).

CREATE TABLE IF NOT EXISTS triples (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject     TEXT NOT NULL,
    predicate   TEXT NOT NULL,
    object      TEXT NOT NULL,
    source_turn TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Subject lookups are the common graph-traversal entry point.
CREATE INDEX IF NOT EXISTS triples_subject_idx   ON triples (subject);
CREATE INDEX IF NOT EXISTS triples_predicate_idx ON triples (predicate);
