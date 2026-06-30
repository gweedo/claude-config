# Local stdio MCP server is the only interface to memory

Agents reach the Memory service exclusively through a **local stdio MCP server**,
never raw SQL and not a CLI. The server exposes intent-level tools
(`memory_write`, `memory_query`, `memory_supersede`) and is the single home for
the two production bugs the article flags: entity-linking (vocabulary mismatch
between query phrasing and node names) and correct superseding of stale triples.

It uses the **stdio transport** — a process Claude Code launches inside the
devcontainer that connects to the Postgres container over localhost. No HTTP/SSE,
no remote hosting; the environment stays fully local.

**Triple extraction is agent-side**: role agents emit `(subject, predicate,
object)` triples at handoff and `memory_write` stores them directly. This avoids a
second LLM call and keeps an API key out of the server. The only model the server
needs is a **local embedding model** for the pgvector half — no external API.

Direct SQL was rejected (LLM-authored SQL leaks the schema, drops the bitemporal
filter, and scatters the entity-linking logic). A CLI was rejected as a clunkier
form of tool-calling. Server-side LLM extraction was rejected because our writers
are already capable LLMs, unlike the article's raw-transcript ingest source.
