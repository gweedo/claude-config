---
name: tech-spec-writer
description: >
  Write a technical specification (docs/architecture/TECH-SPEC.md) for a software project — architecture
  overview with Mermaid diagrams, components, data model, API, infrastructure, CI/CD, testing, security,
  observability. Use when the user wants to spec out or document how the system is built.
metadata:
  version: "0.2.0"
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
6. **Infrastructure** — hosting, datastore, storage, edge/CDN, secrets, registry, region; a table works well. Include a short **Containerization** subsection that states the Docker file layout (see the convention below).
7. **CI/CD** — source control, pipelines, environments, migrations; a Mermaid pipeline diagram helps.
8. **Testing strategy** — the test pyramid and tools if a methodology (e.g. TDD) was chosen.
9. **Cross-cutting concerns** — security, observability/logging, performance, and (for web) SEO.
10. **Resolved / open technical choices** — a short list, marking resolved ones and linking the decision log.
11. **Out of scope** — explicit non-goals.

## Mermaid diagrams

Use Mermaid (renders in most Markdown viewers). Take the monochrome init prefix and the
diagram patterns from `../design-workflow/references/mermaid-snippets.md` — don't hardcode
the theme string here. Prefer a clean top-down flow with grouped subgraphs over many
crossing arrows; move minor relationships to a sentence under the diagram.

## Docker file layout convention

All Docker-related files must live inside a `docker/` folder — never loose at the repository root. This includes `Dockerfile`s, `docker-compose*.yml`, `.dockerignore`, entrypoint/wait scripts, and any image-specific config.

- **Single configuration** → one `docker/` folder at the repo root:
  ```
  docker/
    Dockerfile
    docker-compose.yml
    .dockerignore
    entrypoint.sh
  ```
- **Multiple configurations** (e.g. per service, or per environment) → a separate `docker/` folder for **each** one, namespaced as subfolders:
  ```
  docker/
    api/
      Dockerfile
      docker-compose.yml
    worker/
      Dockerfile
    web/
      Dockerfile
      docker-compose.yml
  ```
  Each configuration owns its own `Dockerfile` (and compose file when it needs one); do not share a single Dockerfile across distinct services.

In Infrastructure/CI-CD, reference these paths by name (e.g. `docker/api/Dockerfile`).

## Quality

- Keep it consistent with the decision log and ADRs; reference ADRs by number.
- When scope changes, update affected sections and fix cross-references.
- Mark deferred features clearly (e.g. "phase 2") so the spec reflects actual v1 scope.

See `templates/TECH-SPEC.template.md`. Reusable monochrome diagram patterns are in `../design-workflow/references/mermaid-snippets.md`.
