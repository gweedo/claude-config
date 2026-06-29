# Plan: Build agent-orchestra multi-agent framework

**Project:** agent-orchestra | **Stack:** claude-code-plugin, postgres, pgvector, python, mcp-stdio, docker-compose | **Status:** draft | **Created:** 2026-06-29

A Claude Code-native multi-agent framework: a per-project Orchestrator delegates to 6 role-agent subagents (Developer, Tester, Architect, Infrastructure, PM, Domain Expert) sharing a durable Postgres+pgvector Memory service reached only via a local stdio Memory MCP server, with a plan-gated phase -> PR -> pre-review workflow.

## Constraints
- Claude-native constructs only (agents + skills/commands, not a standalone runtime) — ADR-0001
- Durable memory must outlive a session (no per-session in-process graph) — ADR-0001
- One Postgres+pgvector container per project (no shared multi-project instance) — ADR-0001
- Postgres-only, no Neo4j (graph as bitemporal triples + recursive CTEs) — ADR-0001
- Memory reached only via the stdio MCP server (no raw SQL, no CLI, no HTTP/SSE) — ADR-0002
- Triple extraction is agent-side (server does no LLM extraction, no external API key) — ADR-0002
- Local embedding model only — ADR-0002
- Supersede, don't delete (bitemporal valid_to, centralized in MCP server) — ADR-0002
- Subagents have isolated context (the graph is their only shared memory) — ADR-0003
- Phase boundaries are the canonical memory-write points — ADR-0003
- User holds final merge approval; review is a mode of Architect+Tester, not a role — ADR-0003
- Role agents reuse existing repo skills rather than re-derive workflow — ADR-0003
- Confirm names before Phase 0: plugin `agent-orchestra`, skill `domain-expert-init`
- Each phase lands as its own PR (dogfood the framework's own flow)

## Findings
**Key files:** CONTEXT.md (vocabulary), docs/BUILD-PLAN.md (the 6-phase plan), docs/adr/0001-0003 (decisions)
**Relevant deps:** pgvector/pgvector, docker-compose, mcp (stdio), sentence-transformers, gh, devcontainer-tools plugin
**Skill reuse map:** Developer->implement/tdd, Tester->tdd/diagnosing-bugs, Architect->codebase-design/project-design-kit, Infrastructure->devcontainer-tools/cicd-designer, PM->to-prd/to-issues, Domain Expert->domain-modeling + domain-expert.md
**Gaps:** plugin skeleton absent (only CONTEXT.md + docs/ exist today); memory service unbuilt; MCP server unbuilt; role agents + Orchestrator unbuilt; scaffold piece absent; PR review loop unbuilt
**Article bugs to handle in MCP server:** entity-linking (query phrasing -> node names) and supersede (close prior valid_to)

## Dependencies / critical path

```
0 -> 1 -> 2 -> 3        (critical path)
          \             4 depends on 1+2 (not 3)
           3 -> 5       5 depends on 3
```

## Steps

| # | Action | File | Status |
|---|--------|------|--------|
| **Phase 0 — Plugin skeleton** (depends on: —) | | | |
| 0.0 | Confirm provisional names (plugin agent-orchestra, skill domain-expert-init) | docs/plan/00_meta.yaml | todo |
| 0.1 | Create plugin manifest (name, version, author) | .claude-plugin/plugin.json | todo |
| 0.2 | Create directory tree: agents/, skills/, memory-service/, docs/ | plugin root | todo |
| 0.3 | Write README describing the framework at a glance | README.md | todo |
| **Phase 1 — Memory service** (depends on: 0) | | | |
| 1.1 | Define pgvector service: named volume, localhost port | memory-service/docker-compose.yml | todo |
| 1.2 | Bitemporal triples + chunks(embedding vector) tables + ivfflat/hnsw index | memory-service/schema.sql | todo |
| 1.3 | Wire seed/init so schema applies on first `up` | memory-service/ | todo |
| **Phase 2 — Memory MCP server** (depends on: 1) | | | |
| 2.1 | stdio MCP server: memory_write / memory_query / memory_supersede over localhost | memory-service/mcp/ | todo |
| 2.2 | Integrate local sentence-transformers embedding model (no external API) | memory-service/mcp/ | todo |
| 2.3 | Entity-linking: normalize query phrasing -> node names (bug #1) | memory-service/mcp/ | todo |
| 2.4 | Centralize supersede: changed write closes prior valid_to (bug #2) | memory-service/mcp/ | todo |
| **Phase 3 — Role agents + Orchestrator** (depends on: 2) | | | |
| 3.1 | Author 6 role agents (responsibility, skill map, triple-at-handoff protocol; Architect+Tester review mode) | agents/*.md | todo |
| 3.2 | Orchestrator skill: plan -> approve -> per-Phase fan-out -> flush triples -> pause | skills/orchestrator/ | todo |
| 3.3 | domain-expert-init skill: interview user, write/update domain-expert.md | skills/domain-expert-init/ | todo |
| **Phase 4 — Scaffold integration** (depends on: 1, 2) | | | |
| 4.1 | postgres-memory piece: compose service, schema.sql, MCP config, .agent-orchestra/ seed, postCreate wiring | devcontainer-tools | todo |
| 4.2 | ci-parity check that scaffolded memory service comes up cleanly | devcontainer-tools | todo |
| **Phase 5 — PR review loop** (depends on: 3) | | | |
| 5.1 | Orchestrator opens a PR at phase end via gh | skills/orchestrator/ | todo |
| 5.2 | Architect/Tester review mode: PR comments + write issues into graph; user holds merge | agents/{architect,tester}.md | todo |

## Acceptance criteria ("done when")

- **Phase 0:** plugin loads in Claude Code with no errors and lists no commands/agents yet.
- **Phase 1:** `docker compose up` yields Postgres with the schema; manual SQL can insert a triple, supersede it (close valid_to), and a recursive-CTE two-hop query returns the expected join.
- **Phase 2:** with the server registered, a `memory_write` of triples is retrievable via `memory_query` (graph + vector), and a re-write of a changed fact supersedes the old one (old fact no longer returned).
- **Phase 3:** the Orchestrator runs a toy task end-to-end — produces a plan, spawns >=2 role agents that read/write memory, and a later agent recalls an earlier agent's decision from the graph.
- **Phase 4:** scaffolding a fresh project then "Reopen in Container" gives a working memory service + registered MCP tools with zero manual steps.
- **Phase 5:** a phase's work lands as a PR that already carries Architect/Tester review comments before the user looks at it.

## Verification
- Phase 0: load the plugin; confirm no errors, no commands/agents listed.
- Phase 1: `cd memory-service && docker compose up -d`; via psql insert/supersede a triple and run a two-hop recursive CTE.
- Phase 2: register server; memory_write sample triples; memory_query returns via graph + vector; re-write a fact and confirm the superseded one no longer returns.
- Phase 3: run Orchestrator on a toy task; verify plan, >=2 agents read/write memory, later agent recalls an earlier decision.
- Phase 4: run devcontainer-tools ci-parity check; scaffold a fresh project and Reopen in Container with zero manual steps.
- Phase 5: complete a phase; confirm the PR carries Architect/Tester comments pre-review and merge stays blocked on user approval.
- Regression: each phase stays independently testable and lands as its own PR; earlier phases keep passing as later ones build.

**Rollback:** Each phase is its own PR — revert/close the phase PR to undo. The Memory service is one isolated per-project container (`docker compose down -v` removes it) and the plugin is local, so nothing affects other projects.

---
*Source of truth: `plans/build-agent-orchestra/` (here: `docs/plan/`) — edit the YAML files, not this document.*
