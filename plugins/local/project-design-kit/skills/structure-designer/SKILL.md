---
name: structure-designer
description: >
  Design an application's structure and data model — surface/sitemap, data models with an ER diagram,
  API endpoints, and (for web) page layout and SEO. Use when the user wants to design the data model,
  sitemap, API surface, or entity relationships. Produces docs/architecture/STRUCTURE.md.
metadata:
  version: "0.1.0"
---

# Structure Designer

Design the information architecture and data model: what surfaces the system exposes, what it stores, and how clients reach it.

## Location

Write to `docs/architecture/STRUCTURE.md` from `templates/STRUCTURE.template.md`.

## What to produce

1. **Surface / sitemap** — for a web app, the page tree with URL patterns (use the product's content language for public URLs if that aids SEO); for an API/service, the resource map. Note navigation and any redirects.
2. **Data models** — one table per entity with fields, types, and notes. Call out:
   - primary keys, unique keys, nullable foreign keys;
   - value-object-worthy fields (validated wrappers);
   - what is stored vs referenced (e.g. store file URLs, not blobs);
   - which entities are v1 vs deferred (mark "phase 2").
3. **Relationships** — list them and include a Mermaid `erDiagram`.
4. **API endpoints** — group by surface (e.g. public read vs authenticated admin). Show method, path, and purpose; note pagination and filters.
5. **Page layout** (web) — section order for key page types.
6. **SEO** (web) — meta fields, canonical, structured data, sitemap/robots, internal linking.

## Consistency rules

- Keep entities, endpoints, and scope in lockstep with `DECISIONS.md` and the tech spec. If a feature is deferred, remove it from v1 surfaces/endpoints/models and mark it "phase 2" — do not leave it implied as v1.
- Every v1 entity that users manage needs corresponding admin endpoints; every browsable entity needs read endpoints and (for web) an archive page.
- When scope changes, re-scan this doc for stale "optional"/"if used" notes and fix them.

See `templates/STRUCTURE.template.md`. Reusable monochrome diagram patterns are in `../design-workflow/references/mermaid-snippets.md`.
