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

Early build. Implemented so far (issues #21–#24):

- Plugin skeleton (this directory).
- [`memory-service/`](memory-service/) — Postgres + pgvector container with a
  bitemporal `triples` table (graph recall, incl. multi-hop traversal and
  supersede) and a `chunks` table with an ivfflat ANN index (vector recall via
  a local embedding model, no external API), reached through a stdio Memory
  MCP server exposing `memory_write`, `memory_query`, and `memory_supersede`
  (issues #21–#23).
- [`agents/developer.md`](agents/developer.md) and
  [`agents/architect.md`](agents/architect.md) — the first two role agents,
  each spawned as an isolated subagent that reads/writes the Context graph at
  handoff (issue #24).
- [`skills/orchestrator/`](skills/orchestrator/) — the plan-gated Orchestrator
  skill: produces a plan, waits for user approval, then fans out to the
  Developer and Architect subagents in sequence so the Architect can recall the
  Developer's decision from the graph (issue #24 — the multi-agent proof).

The remaining four role agents (Tester, Infrastructure, PM, Domain Expert),
Review mode, entity-linking, and the scaffold integration land in later issues
(#25–#28).

## Layout

| Path | What |
|------|------|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `agents/` | Role-agent definitions — `developer.md`, `architect.md` so far |
| `skills/orchestrator/` | Plan-gated Orchestrator skill (plan → approve → fan out → memory) |
| `memory-service/` | Postgres container + Memory MCP server |
| `docs/` | CONTEXT, ADRs, build plan |
