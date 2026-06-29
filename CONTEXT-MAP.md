# Context Map

This repo (`~/.claude` config) is multi-context: shared agent/skill/hook config at the
root, plus self-contained sub-projects that each own their domain language.

| Context | CONTEXT.md | What it covers |
| ------- | ---------- | -------------- |
| Security scan | `security-scan/CONTEXT.md` | CVE/freshness scanning capability (oracle / scanner / definer) |
| Self-improve | `self-improve/CONTEXT.md` | Self-improvement loop project (created lazily by `/domain-modeling`) |

System-wide architectural decisions live in `docs/adr/`. Context-scoped decisions live
under `<context>/docs/adr/` (e.g. `security-scan/docs/adr/`).

Read the `CONTEXT.md` for the context you're working in. If a listed `CONTEXT.md` doesn't
exist yet, proceed silently — `/domain-modeling` creates them lazily.
