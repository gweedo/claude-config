# [PROJECT NAME] — Technical Specification

**Status:** Draft
**Date:** [YYYY-MM-DD]
**Owner:** [Name]
**Related:** `../DECISIONS.md`, `STRUCTURE.md`, `adr/`

This specification describes how [PROJECT NAME] is built and operated. The *why* behind each major choice is in the ADRs (`adr/`); the running decision summary is in `DECISIONS.md`.

---

## 1. Overview

[What the system is. Primary goals. Fixed constraints (language, cloud, budget, deadline, compliance).]

---

## 2. Architecture overview

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
flowchart TD
    User["Users"] --> Edge["Edge / entry point"]
    Edge --> App["Application / service(s)"]
    App --> Data[("Datastore")]
```

[Short narrative. List components and reference the relevant ADRs.]

---

## 3. Components

### 3.1 [Component / service name]
- [Language, framework, key libraries.]
- [Internal structure / pattern. If layered or DDD, show the layout and dependency rule.]

### 3.2 [Component / service name]
- [...]

---

## 4. Data model

[Summary of entities and relationships. Full field detail in `STRUCTURE.md`.]

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','fontFamily':'sans-serif'}}}%%
erDiagram
    ENTITY_A ||--o{ ENTITY_B : "relationship"
    ENTITY_A { uuid id PK
               string name }
    ENTITY_B { uuid id PK
               uuid a_id FK }
```

---

## 5. API design

[Surfaces (public/admin/etc.), contract conventions, pagination, auth.]

---

## 6. Infrastructure

| Concern | Service / tool | Notes |
|---|---|---|
| Compute | [ ] | [ ] |
| Datastore | [ ] | [ ] |
| Storage | [ ] | [ ] |
| Edge / CDN | [ ] | [ ] |
| Secrets | [ ] | [ ] |
| Region | [ ] | [ ] |

[Secrets handling, IaC tool.]

### Containerization

All Docker assets live under a `docker/` folder — one subfolder per configuration when there is more than one. Fill in the actual layout:

```
docker/
  [config]/
    Dockerfile
    docker-compose.yml
```

---

## 7. CI/CD

- **Source control:** [ ]
- **Pipelines:** [ ]
- **Environments:** [ ]
- **Migrations:** [ ]

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
flowchart LR
    Dev["Push / PR"] --> CI["Build + test"]
    CI --> Reg["Artifact registry"]
    Reg --> STG["Staging"]
    STG --> PROD["Production"]
```

---

## 8. Testing strategy

[If a methodology was chosen (e.g. TDD), describe the test pyramid and tools.]

| Layer | Scope | Tools |
|-------|-------|-------|
| Unit | [ ] | [ ] |
| Integration | [ ] | [ ] |
| E2E | [ ] | [ ] |

---

## 9. Cross-cutting concerns

### Security
- [ ]

### Observability & logging
- [ ]

### Performance
- [ ]

<!-- For web projects, add an SEO subsection. -->

---

## 10. Resolved / open technical choices

1. [Choice] — [RESOLVED: …] or [open: options].

---

## 11. Out of scope

- [Explicit non-goals.]
