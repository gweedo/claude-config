# The theory behind agent-orchestra

This document explains *why* the Memory service is built the way it is. It is the
conceptual companion to the decisions in [`docs/adr/`](./adr/) and the vocabulary
in [`../CONTEXT.md`](../CONTEXT.md) — read those for *what* was decided and the
canonical terms. Here we cover the underlying ideas.

Source inspiration: *"Vector RAG isn't enough: I built a context graph layer for
multi-agent memory"* (Towards Data Science).

---

## 1. The problem: shared memory across isolated agents

agent-orchestra runs each role as a **native Claude Code subagent** in its own
isolated context (ADR-0003). Isolation is a feature — it keeps each role focused
and keeps token cost bounded — but it creates a problem: the Tester cannot see
what the Developer decided three steps ago, because they never shared a context.

Something outside the agents has to hold the facts they accumulate. That
something is the **Memory service**, and the whole framework's coherence rests on
it: *the graph IS the agents' shared memory*. Every other design choice serves
this one need — durable, queryable, cross-agent, cross-session recall.

## 2. Why vector RAG alone is not enough

The obvious approach is vector RAG: embed every conversation turn, and on a
question retrieve the most semantically similar chunks. This works for "what did
we say about X?" but fails on **join questions** — questions whose answer is
spread across two facts that were never stated together.

> "Which datastore does the module owned by the Developer depend on?"

If "the Developer owns AuthModule" and "AuthModule depends on Redis" were stated
in different turns, no single chunk contains the answer. Similarity search ranks
chunks individually; it has no mechanism to *combine* two of them. The source
article measured this gap directly: ~80% accuracy on join queries with a graph
vs. ~20% with vector RAG.

The failure is structural, not a tuning problem. More embeddings or a bigger
top-k cannot manufacture a relationship that was never co-located in text.

## 3. The context graph: facts as triples

The fix is to store facts as **triples** — `(subject, predicate, object)`:

```
(Developer,   OWNS,        AuthModule)
(AuthModule,  DEPENDS_ON,  Redis)
```

Now the join question is a **graph traversal**: start at `Developer`, follow
`OWNS` to `AuthModule`, follow `DEPENDS_ON` to `Redis`. Two hops, deterministic,
exact. The relationship is explicit in the data structure rather than implied by
proximity in an embedding space.

This is implemented as the `query_join` recursive CTE in `memory_store.py`
(issue #22): a bounded, cycle-guarded walk of up to N hops.

### Why Postgres recursive CTEs instead of a graph database

The article used NetworkX with a Neo4j export path. We use a **single Postgres +
pgvector container** instead (ADR-0001), with traversal expressed as a recursive
CTE. The reasoning:

- At single-developer, per-project scale, traversals are shallow (1–3 hops) and
  the graph is small. A recursive CTE is more than fast enough.
- One engine means one container, one connection, one backup story — the
  environment stays fully local with no second moving part.
- It is reversible: if traversals ever get deep or hot enough to matter, the
  triples table exports cleanly to a real graph engine later.

## 4. Why a graph and vectors, not graph *or* vectors

The two retrieval modes answer different question shapes, so the Memory service
keeps both (the vector half arrives in issue #23):

| Question shape | Example | Best tool |
| --- | --- | --- |
| Fuzzy / semantic | "anything we noted about rate limiting?" | vector recall (pgvector) |
| Relational / join | "what does the PM's top-priority module depend on?" | graph traversal |

Vector RAG is not wrong — it is incomplete. The context graph is the *added*
layer, not a replacement.

## 5. Bitemporality: superseding, not deleting

Decisions change mid-project. "RateLimiter is high priority" becomes "RateLimiter
is low priority." A naive store would overwrite or delete the old fact — and then
lose the ability to answer "when did that change, and what was it before?"

Instead, every triple carries `valid_from` / `valid_to`. A fact is **current**
while `valid_to IS NULL`. **Superseding** a fact closes its `valid_to` (stamps it
with the time it stopped being true) and inserts the replacement as a new current
row. Nothing is destroyed.

Consequences that make this worth the complexity:

- **Queries default to the current view** (`valid_to IS NULL`), so agents never
  act on stale facts — directly addressing one of the two production bugs the
  article flags (stale-fact retrieval when edges aren't properly superseded).
- **Traversal only follows current edges**, so a superseded hop drops a whole
  path out of a join result automatically.
- **History is retained** for audit / "why did we change our mind?" via an
  `include_superseded` opt-in.

This is the `supersede` method + the partial index on the current-view hot path
(issue #22).

## 6. The MCP server as the single interface

Agents never touch SQL. All memory access goes through the **stdio Memory MCP
server** (ADR-0002), which exposes intent-level tools: `memory_write`,
`memory_query`, `memory_supersede`. The reasoning is concentration of risk:

- The bitemporal **current-view filter** lives in one place, so no agent can
  forget it and read stale facts.
- The future **entity-linking** layer (the article's other production bug —
  query phrasing not matching node names, issue #25) has exactly one home.
- Agents do **agent-side extraction**: they emit clean triples at handoff, so the
  server needs no second LLM and the environment needs no external API key.

## 7. What is deliberately deferred

The theory is larger than any one issue. The build deliberately lands it in thin,
verifiable slices (see [`BUILD-PLAN.md`](./BUILD-PLAN.md)):

- **#21** — wiring proof: minimal triples table + write/read through real MCP.
- **#22** — the graph proof: multi-hop traversal + bitemporal supersede.
- **#23** — the vector half (pgvector `chunks` + local embeddings).
- **#25** — entity-linking (vocabulary mismatch — article bug #1).

Each slice is the smallest change that proves a piece of this theory against a
live container, rather than building the whole essay at once.
