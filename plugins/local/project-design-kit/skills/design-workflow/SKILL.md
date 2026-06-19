---
name: design-workflow
description: >
  Run an end-to-end, decision-first design workflow for a software project, before writing code. Use
  when the user wants to design or plan a project's architecture and documentation from scratch, or run
  the design workflow. The orchestrator that sequences decision-tracker, adr-writer, tech-spec-writer,
  structure-designer, cicd-designer, and requirements-questionnaire into a docs/ tree.
metadata:
  version: "0.1.0"
---

# Design Workflow (orchestrator)

Guide a project from undefined to a complete, internally consistent set of design documents — **before** writing code. Sequence the companion skills in this plugin, apply a consistent working style, and leave behind a clean `docs/` tree.

## Working style (apply throughout)

1. **Decisions first, code later.** Resolve the choices that everything else depends on before building anything.
2. **Present trade-offs before recommending.** For every open choice, lay out the realistic options with pros/cons tied to *this* project's constraints (team size, skills, time-to-launch, cost, scale), then give a clear recommendation.
3. **Ask with structured choices.** Use multiple-choice questions for decisions; let the user pick or override. One decision thread at a time; don't overwhelm.
4. **Log every meaningful decision** immediately via the `decision-tracker` skill. Never rely on chat history as the record.
5. **Keep open questions visible.** When something is undecided or owned by someone else, capture it as an open question rather than guessing.
6. **Respect fixed constraints.** Identify what is non-negotiable (language, cloud, budget, deadline) and design within it.
7. **Flag risks honestly.** Name the biggest effort/risk items (e.g. anything custom-built) and suggest ways to de-risk (minimal v1, fallbacks).
8. **Review for consistency** at the end and whenever scope changes — stale cross-references and contradictions are the main failure mode.
9. **For multi-part areas, run a stage-by-stage deep-dive** — resolve one decision at a time (options → trade-offs → recommend → decide → log), then synthesize into an ADR and a spec section. See `references/decision-facilitation.md`.

## The passages (run in order; adapt to the project)

### 1. Establish context and constraints
- Identify the project's purpose, the team (who is technical vs not), and the **fixed constraints**.
- Surface the **open questions** and record them with `decision-tracker`. Ask: "What are our open questions?"

### 2. Resolve the foundational stack first
- Tackle the choices everything depends on first (language/framework, hosting/runtime, datastore, rendering/CMS approach).
- For each: present options + trade-offs, recommend, ask, then **log the decision**.
- If a choice depends on another open question (e.g. content language affects domain/SEO), resolve the upstream one first and note the dependency.

### 3. Capture cross-cutting decisions
- Version control, CI/CD, repository layout (mono/poly), environments (staging/prod), IaC, observability/logging, security, testing methodology, architecture approach (e.g. DDD), and any privacy/compliance constraints.
- Log each with `decision-tracker`.
- For the **CI/CD pipeline and deployment strategy**, use the `cicd-designer` skill to run the stage-by-stage deep-dive (branching, tests, security, image tagging, environments/secrets, migrations, release strategy, verification/rollback).

### 4. Write Architecture Decision Records
- For each significant decision, produce an ADR with the `adr-writer` skill (context, options, trade-offs, consequences). One file per decision under `docs/architecture/adr/`, plus an index.
- If the host environment has an engineering "architecture" skill available, you may use it for ADR framing; otherwise use `adr-writer`.

### 5. Write the technical specification
- Use `tech-spec-writer` to produce `docs/architecture/TECH-SPEC.md`: architecture overview (with Mermaid diagrams), components, data model, API surface, infrastructure, CI/CD, testing, security, observability, and a list of resolved/open choices.

### 6. Design the structure and data model
- Use `structure-designer` to produce `docs/architecture/STRUCTURE.md`: sitemap/surface map, data models (with an ER diagram), API endpoints, and (for web) SEO/page layout.

### 7. Gather stakeholder input
- When product/content/business details are owned by non-technical teammates, use `requirements-questionnaire` to produce a fill-in questionnaire in the stakeholders' language. Their answers feed a PRD later.
- Mark anything blocked on those answers as an open question; do not invent product facts.

### 8. Co-author and review
- For longer narrative docs (PRD, proposals), use a doc co-authoring approach if available (context → section-by-section → reader testing).
- Run a **complete consistency review** of all docs: check for contradictions, stale references after scope changes, broken cross-links, and gaps. Fix unambiguous issues; raise real design questions to the user.

### 9. Organize into a docs/ tree
- Place all documentation under `docs/` with this structure, and add a `docs/README.md` index:

```
docs/
├── README.md                     # index / front door
├── DECISIONS.md                  # decision log
├── architecture/
│   ├── TECH-SPEC.md
│   ├── STRUCTURE.md
│   └── adr/
│       ├── README.md             # ADR index
│       └── NNNN-*.md             # one decision per file
└── product/
    ├── PRD.md                    # once stakeholder answers arrive
    └── <stakeholder>-questionnaire.md
```

- Update all relative cross-references when moving files; verify no links break.

## Companion skills in this plugin

The passages above invoke these by name; see each skill's own description for what it does:
`decision-tracker`, `adr-writer`, `tech-spec-writer`, `structure-designer`,
`requirements-questionnaire`, `cicd-designer`.

Each ships a generic template under its `templates/` folder — read it, then fill it from the project's real, researched facts (never ship placeholder text as if it were decided).

## Utilities (shared references)
- `references/decision-facilitation.md` — the stage-by-stage deep-dive decision method.
- `references/mermaid-snippets.md` — monochrome Mermaid diagram patterns (architecture, layers, ER, pipeline) used by the tech-spec and structure docs.
