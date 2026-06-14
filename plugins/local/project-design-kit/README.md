# Project Design Kit

A decision-first design workflow for any software project. It takes a project from "undefined" to a complete, internally consistent set of design documents — **before** you write code — and leaves behind a clean `docs/` tree.

It encodes the working style of: resolve the choices everything depends on first, present trade-offs before recommending, decide with structured questions, log every decision, keep open questions visible, and review for consistency at the end.

## Skills

| Skill | What it does |
|-------|--------------|
| **design-workflow** | Orchestrator. Sequences the others through the full passage: context → stack → cross-cutting decisions → ADRs → tech spec → structure → stakeholder input → review → organize `docs/`. |
| **decision-tracker** | Maintains `docs/DECISIONS.md` — final/provisional decisions, risks, open questions, superseded decisions. |
| **adr-writer** | Writes Architecture Decision Records (one file per decision) and the ADR index, with context, options, trade-offs, consequences. |
| **tech-spec-writer** | Writes `docs/architecture/TECH-SPEC.md` with Mermaid diagrams, components, data model, API, infra, CI/CD, testing, security, observability. |
| **structure-designer** | Designs `docs/architecture/STRUCTURE.md`: surface/sitemap, data models + ER diagram, API endpoints, page layout, SEO. |
| **requirements-questionnaire** | Produces a stakeholder questionnaire (in the stakeholders' language) whose answers feed a PRD. |

Each skill ships a generic, fill-in template under its `templates/` folder.

## How to use

Say something like *"let's start designing my project"* or *"run the design workflow"* to kick off the orchestrator, or invoke any single skill directly (e.g. *"write an ADR for choosing Postgres over MySQL"*, *"log this decision"*, *"make a questionnaire for the marketing team"*).

## Resulting docs layout

```
docs/
├── README.md
├── DECISIONS.md
├── architecture/
│   ├── TECH-SPEC.md
│   ├── STRUCTURE.md
│   └── adr/
│       ├── README.md
│       └── NNNN-*.md
└── product/
    ├── PRD.md
    └── <stakeholder>-questionnaire.md
```

## Works well with

- A documentation co-authoring skill (for narrative docs like the PRD: context → section-by-section → reader testing).
- An engineering "architecture" skill (for ADR framing), if available in your environment.

These are optional; the kit is self-contained.
