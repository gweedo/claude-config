# agent-orchestra

A Claude Code-native multi-agent framework for software projects.

A per-project **Orchestrator** coordinates six specialized **role agents**
(Developer, Tester, Architect, Infrastructure, PM, Domain Expert) as native
subagents. Because subagents have isolated contexts, they share state through a
durable **Memory service** — one Postgres + pgvector container per project,
holding a bitemporal **Context graph** of `(subject, predicate, object)` triples
plus a vector index, reached **only** through a local stdio **Memory MCP server**
(`memory_write` / `memory_query` / `memory_supersede`).

Workflow: plan-gated → autonomous per phase → GitHub PR → Architect/Tester
pre-review → user approves merge.

See [`CONTEXT.md`](CONTEXT.md) for the ubiquitous language,
[`docs/adr/`](docs/adr/) for the locked decisions, and
[`docs/BUILD-PLAN.md`](docs/BUILD-PLAN.md) for the phased build.

## Status

Early build. Implemented so far (issues #21–#23):

- Plugin skeleton (this directory).
- [`memory-service/`](memory-service/) — Postgres + pgvector container with a
  bitemporal `triples` table (graph recall, incl. multi-hop traversal and
  supersede) and a `chunks` table with an ivfflat ANN index (vector recall via
  a local embedding model, no external API), reached through a stdio Memory
  MCP server exposing `memory_write`, `memory_query`, and `memory_supersede`.

Role agents, the Orchestrator, entity-linking, and the scaffold integration
land in later phases (issues #24–#28).

## Layout

| Path | What |
|------|------|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `agents/` | Role-agent definitions (Phase 3) |
| `skills/` | Orchestrator + supporting skills (Phase 3) |
| `memory-service/` | Postgres container + Memory MCP server |
| `docs/` | CONTEXT, ADRs, build plan |
