# Agent Orchestra

A Claude Code-native multi-agent framework for software projects. A per-project
Orchestrator coordinates specialized role agents, which share a durable Memory
service backed by a Context graph (the "graph + vector" idea from the source
article). The framework is authored here as a local plugin; its Memory service is
scaffolded into each target project as local containers.

## Language

### Agents

**Orchestrator**:
The single coordinator agent for a project. Plans work, delegates to role agents
via native subagents, gates work behind a plan and per-phase checkpoints, and is
the read/write owner of the Memory service.
_Avoid_: Coordinator, manager, lead

**Role agent**:
A specialized agent with one job. Six of them: Developer, Tester, Architect,
Infrastructure, PM, Domain Expert. Spawned by the Orchestrator as native
subagents (isolated context); never invoked directly by the user. Each reuses
existing repo skills rather than re-deriving how to work.
_Avoid_: Worker, spoke, sub-agent (say "role agent")

**Domain Expert**:
The one configurable role agent — its expertise is supplied per project via a
`domain-expert.md` file. The other five roles are fixed.
_Avoid_: SME, specialist

**Review mode**:
A mode (not a separate role) of the Architect and Tester. On an open PR the
Architect reviews design/structure and the Tester reviews coverage/correctness;
both post findings as PR comments and write issues found into the Context graph.
_Avoid_: Reviewer (there is no Reviewer role)

### Memory

**Memory service**:
The durable, cross-session store the agents share. One Postgres + pgvector
container per project. Holds both the Context graph and the vector index.
Accessed only through the Memory MCP server.
_Avoid_: Database, store, RAG (those name parts of it, not the whole)

**Memory MCP server**:
A local stdio MCP server (a process launched by Claude Code inside the
devcontainer) that connects to the Postgres container and exposes the only
interface to memory: `memory_write`, `memory_query`, `memory_supersede`. Owns
entity-linking and superseding logic. No remote/HTTP transport.
_Avoid_: API, gateway

**Context graph**:
The graph half of the Memory service: facts stored as triples and traversed via
recursive CTEs to answer multi-hop ("join") questions that vector similarity
alone cannot.
_Avoid_: Knowledge graph, memory graph

**Triple**:
A single stored fact as (subject, predicate, object), e.g.
(AuthModule, DEPENDS_ON, RateLimiter). Emitted by role agents at handoff and
written via `memory_write`. The unit of the Context graph.
_Avoid_: Edge, relation, fact (informally fine; "triple" is canonical)

**Supersede**:
Marking a triple no longer current when a newer fact replaces it (bitemporal
`valid_to`), rather than deleting it. How the graph handles changed decisions.
_Avoid_: Overwrite, invalidate, delete

**Distractor turn**:
A conversation turn carrying no durable fact (e.g. an acknowledgment). Bypasses
the Memory service entirely — nothing is extracted or stored.
_Avoid_: Noise, filler

### Workflow

**Phase**:
One unit of the Orchestrator's plan. Within a phase the Orchestrator fans out to
role agents autonomously; at the phase boundary it writes facts to memory,
reports, and pauses for the user's go-ahead on the next phase.
_Avoid_: Step, stage, iteration

**PR gate**:
A completed phase lands as commits on a GitHub PR. Architect and Tester pre-review
it in Review mode; the user holds final merge approval.
_Avoid_: Merge check
