# agent-orchestra — Build Plan

Phased build for the multi-agent framework. Each phase is independently testable
and lands as its own PR (dogfooding the framework's own Phase → PR → review flow).
See `CONTEXT.md` for vocabulary and `docs/adr/0001-0003` for the decisions behind
this plan.

---

## Phase 0 — Plugin skeleton

Stand up the empty plugin so everything else has a home.

- `plugins/local/agent-orchestra/.claude-plugin/plugin.json` (name, version, author).
- Directory tree: `agents/`, `skills/`, `memory-service/`, `docs/`.
- `README.md` describing the framework at a glance.

**Done when:** the plugin loads in Claude Code with no errors and lists no
commands/agents yet.

---

## Phase 1 — Memory service (Postgres + pgvector)

The durable core. Build it standalone and testable before any agent touches it.

- `memory-service/docker-compose.yml` — `pgvector/pgvector` image, named volume,
  localhost port.
- `memory-service/schema.sql` — bitemporal `triples(subject, predicate, object,
  valid_from, valid_to, source_turn)` + `chunks(id, text, embedding vector, …)`;
  indexes (incl. an ivfflat/hnsw index on `embedding`).
- Seed/init script wiring so the schema applies on first `up`.

**Done when:** `docker compose up` yields a Postgres with the schema; manual SQL
can insert a triple, supersede it (close `valid_to`), and a recursive-CTE two-hop
query returns the expected join result.

---

## Phase 2 — Memory MCP server

The sole interface to memory (ADR-0002).

- `memory-service/mcp/` — stdio MCP server (Python recommended: pgvector +
  embeddings ecosystem). Tools: `memory_write(triples)`, `memory_query(question)`,
  `memory_supersede(...)`.
- Local embedding model (small sentence-transformers) for the vector half.
- Entity-linking layer: normalize query phrasing → node names (article bug #1).
- Supersede logic centralized here (article bug #2): writes close prior `valid_to`.

**Done when:** with the server registered, a `memory_write` of triples is
retrievable via `memory_query` (both graph traversal and vector recall), and a
re-write of a changed fact supersedes the old one (old fact no longer returned).

---

## Phase 3 — Role agents + Orchestrator

The multi-agent layer (ADR-0003).

- `agents/{developer,tester,architect,infrastructure,pm,domain-expert}.md` — each
  with its responsibility, the skill-invocation mapping, and memory read/write
  protocol (emit triples at handoff). Architect & Tester include **review mode**.
- Orchestrator skill/command: plan → approve → per-Phase fan-out via Agent tool →
  flush triples → pause → next Phase.
- `skills/domain-expert-init/` — interviews the user and writes/updates
  `domain-expert.md`.

**Done when:** the Orchestrator runs a toy task end-to-end: produces a plan, spawns
≥2 role agents that read/write memory, and a later agent recalls an earlier
agent's decision from the graph (the article's core proof).

---

## Phase 4 — Scaffold integration (`devcontainer-tools`)

Make it one-command to add memory to any project (the explicit ask).

- New `postgres-memory` piece in `devcontainer-tools` that drops into a target
  project: the compose service, `schema.sql`, MCP config entry, `.agent-orchestra/`
  with a seed `domain-expert.md`, and devcontainer `postCreate` wiring to launch
  the MCP server.
- `ci-parity` check that the scaffolded memory service comes up cleanly.

**Done when:** scaffolding a fresh project then "Reopen in Container" gives a
working memory service + registered MCP tools with zero manual steps.

---

## Phase 5 — PR review loop

Close the workflow.

- Orchestrator opens a PR at phase end (`gh`).
- Architect/Tester review-mode runs post findings as PR comments and write issues
  into the graph; user holds merge approval.

**Done when:** a phase's work lands as a PR that already carries Architect/Tester
review comments before the user looks at it.

---

## Sequencing notes

- 1 → 2 → 3 is the critical path; 0 precedes all.
- Phase 4 depends on 1+2 (needs schema + server) but not on 3.
- Phase 5 depends on 3.
- Provisional names to confirm before Phase 0: plugin `agent-orchestra`, skill
  `domain-expert-init`.
