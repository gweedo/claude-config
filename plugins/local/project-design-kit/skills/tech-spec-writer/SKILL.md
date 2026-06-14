---
name: tech-spec-writer
description: >
  Use this skill to write a technical specification for a software project. Trigger phrases: "write the
  tech spec", "create a technical specification", "document how the system is built", "spec out the
  architecture", "write the engineering reference". Produces docs/architecture/TECH-SPEC.md with an
  architecture overview, Mermaid diagrams, components, data model, API, infrastructure, CI/CD, testing,
  security, and observability.
metadata:
  version: "0.1.0"
---

# Tech Spec Writer

Produce the engineering reference for the system — *how* it is built and operated. The *why* lives in the ADRs; this document describes the design that follows from them.

## Location

Write to `docs/architecture/TECH-SPEC.md` from `templates/TECH-SPEC.template.md`. Cross-reference `../DECISIONS.md`, `STRUCTURE.md`, and `adr/`.

## Sections to cover

1. **Overview** — what the system is, primary goals, fixed constraints.
2. **Architecture overview** — a top-down **Mermaid** diagram of the runtime components and how requests flow, plus a short component list and references to the relevant ADRs.
3. **Components** — each deployable/service: responsibilities, key libraries, internal structure (if it follows a pattern like layered/DDD, show the layout and dependency rule, ideally as a Mermaid diagram).
4. **Data model** — summary of entities and relationships; include a Mermaid `erDiagram`. Full field detail can live in `STRUCTURE.md`.
5. **API design** — the surfaces (public/admin/etc.), contract conventions, pagination, auth.
6. **Infrastructure** — hosting, datastore, storage, edge/CDN, secrets, registry, region; a table works well.
7. **CI/CD** — source control, pipelines, environments, migrations; a Mermaid pipeline diagram helps.
8. **Testing strategy** — the test pyramid and tools if a methodology (e.g. TDD) was chosen.
9. **Cross-cutting concerns** — security, observability/logging, performance, and (for web) SEO.
10. **Resolved / open technical choices** — a short list, marking resolved ones and linking the decision log.
11. **Out of scope** — explicit non-goals.

## Mermaid diagrams

Use Mermaid (renders in most Markdown viewers). To keep diagrams monochrome, prefix with:

```
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
```

Prefer a clean top-down flow with grouped subgraphs over many crossing arrows; move minor relationships to a sentence under the diagram.

## Quality

- Keep it consistent with the decision log and ADRs; reference ADRs by number.
- When scope changes, update affected sections and fix cross-references.
- Mark deferred features clearly (e.g. "phase 2") so the spec reflects actual v1 scope.

See `templates/TECH-SPEC.template.md`.
