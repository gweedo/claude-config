# Memory service

The durable, per-project store the agents share (ADR-0001). One Postgres +
pgvector container, reached **only** through the local stdio Memory MCP server
(ADR-0002).

This is the walking-skeleton slice (issue #21): a minimal `triples(subject,
predicate, object)` table and an MCP server exposing `memory_write` and
`memory_query`. Bitemporal superseding, vector recall, and entity-linking arrive
in build Phase 1/2.

## Layout

| Path | What |
|------|------|
| `docker-compose.yml` | Postgres+pgvector service (localhost-bound) + a `test` profile |
| `schema.sql` | Applied on first `up`; creates the `triples` table |
| `mcp/server.py` | stdio Memory MCP server (`memory_write`, `memory_query`) |
| `mcp/memory_store.py` | DB layer the MCP tools delegate to |
| `mcp/test_store_then_read.py` | Store-then-read integration proof |

## Run the database

```bash
cd memory-service
docker compose up -d            # Postgres comes up, schema.sql applied on first init
docker compose down             # stop (keep data)
docker compose down -v          # stop and drop the volume
```

Postgres listens on `127.0.0.1:5433` (DB `orchestra`, user/pass `orchestra`).

## Verify store-then-read (issue #21 acceptance)

With the database up, run the integration test inside the MCP image against the
live container:

```bash
docker compose run --rm mcp-test
```

It writes a triple via the same `MemoryStore` the MCP tools use and reads it back
— proving the schema, container, and store layer are wired end to end.

## Register the MCP server with Claude Code

The server speaks stdio and is launched as a one-shot container that connects to
the running Postgres over the compose network. Example MCP config entry:

```json
{
  "mcpServers": {
    "agent-orchestra-memory": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "memory-service/docker-compose.yml",
        "run", "--rm", "-T", "mcp-server"
      ]
    }
  }
}
```

(The full devcontainer wiring — auto-launch on `postCreate` — is delivered by the
`devcontainer-tools` `postgres-memory` scaffold piece in Phase 4.)
