---
name: adr-writer
description: >
  Write Architecture Decision Records (ADRs) — one numbered file per decision plus an index README. Use
  when the user wants to document or record an architecture/design decision with its alternatives, or
  wants a choice between options (X vs Y) captured as an ADR.
metadata:
  version: "0.1.0"
---

# ADR Writer

Capture significant architectural and methodological decisions as Architecture Decision Records — durable explanations of *why* a choice was made, with the alternatives and consequences.

## Location & conventions

- One ADR per file at `docs/architecture/adr/NNNN-short-title.md` (zero-padded, sequential).
- Maintain an index at `docs/architecture/adr/README.md` (table of number, title, status, date).
- Status lifecycle: **Proposed → Accepted → Deprecated / Superseded**. When a decision changes, write a new ADR that supersedes the old one rather than editing history.
- Use kebab-case filenames. Keep ADRs concise (about one page).

## What deserves an ADR

Decisions with real alternatives and lasting impact: framework/runtime, datastore, hosting/compute, rendering/CMS approach, repository layout, environments, IaC, observability/logging, security model, testing methodology, and architecture style (e.g. DDD). Routine, easily-reversible choices do not need one.

## Format

Write each ADR from `templates/ADR.template.md`:

- **Context** — the situation and the forces at play (constraints: team, time, cost, scale, compliance).
- **Decision** — what is being adopted, stated plainly.
- **Options Considered** — each named option with a small assessment table (complexity, cost, scalability, team familiarity) and pros/cons. Always include the alternatives, even the rejected ones.
- **Trade-off Analysis** — why the chosen option wins given the constraints.
- **Consequences** — what gets easier, what gets harder, what to revisit later.
- **Action Items** — concrete follow-ups.

State constraints explicitly ("one developer", "must be EU-resident", "ship in 6 weeks") — they justify the decision.

## After writing

- Add the new ADR to the index `README.md`.
- Ensure it is consistent with `docs/DECISIONS.md` (the ADR is the long-form rationale; the decision log is the summary). Cross-reference by ADR number.

See `templates/ADR.template.md` and `templates/adr-index.template.md`.
