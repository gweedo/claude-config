# Mermaid Snippets (monochrome)

Reusable diagram patterns for the docs. Mermaid renders in most Markdown viewers (GitHub, VS Code). Prefer diagrams over hand-aligned ASCII (which breaks easily).

## Monochrome theme directive

Prefix any diagram with this to render white/black with no color fills:

```
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
```

## Layout tips
- Prefer a clean **top-down** flow with **grouped subgraphs** over many crossing arrows.
- Combine parallel edges into one; move minor relationships to a sentence under the diagram.
- Keep node labels short; use `<br/>` for a second line.

## Pattern: system architecture (grouped)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
flowchart TD
    User["Users"] --> Edge["Edge / CDN"]
    subgraph Compute[" Compute "]
        FE["Frontend"] -->|"API"| BE["Backend"]
    end
    Edge --> FE
    BE --> DB[("Database")]
```

## Pattern: layered / dependency rule

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','fontFamily':'sans-serif'}}}%%
flowchart TB
    Interfaces --> Application
    Application --> Domain
    Infrastructure -- "implements interfaces" --> Domain
```

## Pattern: data model (ER)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','fontFamily':'sans-serif'}}}%%
erDiagram
    A ||--o{ B : "has"
    A { uuid id PK
        string name }
    B { uuid id PK
        uuid a_id FK }
```

## Pattern: CI/CD pipeline

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#ffffff','primaryBorderColor':'#333333','primaryTextColor':'#000000','lineColor':'#333333','clusterBkg':'#ffffff','clusterBorder':'#999999','fontFamily':'sans-serif'}}}%%
flowchart TD
    PR["PR"] --> CHK["lint · test · coverage gate · scans"]
    CHK -->|"merge"| BUILD["build (SHA tag) · push"]
    BUILD --> STG["deploy staging · migrate"]
    STG --> E2E{"E2E on staging"}
    E2E -->|"approve"| GREEN["prod green @ 0% · health+smoke"]
    GREEN -->|"flip 100%"| PROD["production"]
    PROD -. "rollback" .-> PREV["revert to previous"]
```
