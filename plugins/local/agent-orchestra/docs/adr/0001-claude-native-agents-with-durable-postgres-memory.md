# Claude Code-native agents with a durable Postgres memory service

The framework is built as Claude Code constructs (role agents + an Orchestrator
skill), **not** a standalone runtime, because the repo is a Claude Code config
repo and that keeps the roles consistent with what already lives here.

The shared memory, however, is a genuine standalone service that **outlives a
single Claude session** — the article's value proposition is durable,
accumulating memory, so a per-session in-process graph was rejected.

That service is **Postgres + pgvector in a single container**, doing both jobs
the article splits across engines: the Context graph as a bitemporal `triples`
table traversed with recursive CTEs, and the vector/RAG half via pgvector. Neo4j
was rejected as premature at single-developer scale and reversible later.

Scope is **one container per project** (matching "one orchestrator per project"),
not a shared multi-project instance — isolation keeps the devcontainer scaffold
simple and avoids cross-project namespacing/auth/poisoning problems. Cross-project
memory is deferred as an additive future feature.

## Considered Options
- Claude-native only: no durable memory — rejected, loses the article's point.
- Standalone framework (LangGraph/CrewAI-style): rejected, inconsistent with repo.
- Hybrid: **chosen** — Claude agents + durable standalone memory service.
- Postgres+Neo4j / embedded graph: rejected in favor of Postgres-only + pgvector.
