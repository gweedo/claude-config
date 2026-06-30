# Memory service

The durable, per-project store the agents share (ADR-0001). One Postgres +
pgvector container, reached **only** through the local stdio Memory MCP server
(ADR-0002).

The Context-graph slice (issues #21–#22): a bitemporal `triples(subject,
predicate, object, valid_from, valid_to)` table and an MCP server exposing
`memory_write`, `memory_query` (direct lookups and multi-hop "join" traversal),
and `memory_supersede`. Vector recall (#23) and entity-linking (#25) arrive
later.

## Layout

| Path | What |
|------|------|
| `docker-compose.yml` | Postgres+pgvector service (localhost-bound) + a `test` profile |
| `schema.sql` | Applied on first `up`; creates the bitemporal `triples` table |
| `mcp/server.py` | stdio Memory MCP server (`memory_write`, `memory_query`, `memory_supersede`) |
| `mcp/memory_store.py` | DB layer the MCP tools delegate to (write, query, traverse, supersede) |
| `mcp/test_store_then_read.py` | Store-then-read integration proof (#21) |
| `mcp/test_two_hop_join.py` | Multi-hop recursive-CTE traversal proof (#22) |
| `mcp/test_supersede.py` | Bitemporal supersede proof (#22) |
| `mcp/test_mcp_*.py` | MCP stdio round-trip proofs for the exposed tools |

## Run the database

```bash
cd memory-service
docker compose up -d            # Postgres comes up, schema.sql applied on first init
docker compose down             # stop (keep data)
docker compose down -v          # stop and drop the volume
```

Postgres listens on `127.0.0.1:5433` (DB `orchestra`, user/pass `orchestra`).

## Verify (issue #21 + #22 acceptance)

With the database up, run the integration tests inside the MCP image against the
live container:

```bash
docker compose --profile test run --rm mcp-test
```

This runs every proof against the live Postgres: store-then-read (#21), the
two-hop recursive-CTE join that no single triple answers, bitemporal supersede
(stale fact hidden, history retained), and the MCP stdio round-trips for
`memory_write`, `memory_query`, and `memory_supersede` (#22).

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
