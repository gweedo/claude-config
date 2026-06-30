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

Early build. Implemented so far (issue #21 — walking skeleton):

- Plugin skeleton (this directory).
- [`memory-service/`](memory-service/) — Postgres + pgvector container with a
  minimal `triples` table and a stdio Memory MCP server exposing `memory_write`
  and `memory_query`, with a store-then-read integration proof.

Role agents, the Orchestrator, superseding, vector recall, and the scaffold
integration land in later phases (issues #22–#28).

## Layout

| Path | What |
|------|------|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `agents/` | Role-agent definitions (Phase 3) |
| `skills/` | Orchestrator + supporting skills (Phase 3) |
| `memory-service/` | Postgres container + Memory MCP server |
| `docs/` | CONTEXT, ADRs, build plan |
