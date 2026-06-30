-- agent-orchestra Memory service schema (Context graph, issues #21–#22).
--
-- Facts are stored as (subject, predicate, object) triples — the unit of the
-- Context graph (see CONTEXT.md). Bitemporal validity columns let a changed fact
-- *supersede* an old one by closing valid_to rather than deleting the row, so
-- history is retained while queries see only the current view (#22). The
-- pgvector `chunks` table for vector recall arrives in #23.
--
-- Applied automatically on first `docker compose up` via the postgres image's
-- /docker-entrypoint-initdb.d mount (see docker-compose.yml).

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
