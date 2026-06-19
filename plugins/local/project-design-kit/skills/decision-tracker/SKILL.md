---
name: decision-tracker
description: >
  Record, review, and manage project decisions and open questions in a living DECISIONS.md. Use when
  the user wants to log a decision or choice, see what's been decided, or track what's still undecided.
metadata:
  version: "0.1.0"
---

# Decision Tracker

Maintain a single living decision log so the whole team stays aligned without relying on chat history.

## Location

Keep the log at `docs/DECISIONS.md` (create it from `templates/DECISIONS.template.md` if it does not exist). Read and update this one file.

## Recording a decision

After any meaningful choice (stack, infra, methodology, scope, data model), append an entry:

```markdown
### [Short decision title]
- **Date**: YYYY-MM-DD
- **Decision**: What was decided (1–2 sentences).
- **Rationale**: Why this option won.
- **Trade-off noted**: What it costs (optional).
- **Status**: ✅ Final | 🔄 Provisional | ❌ Reversed
- **Decided by**: [Name or "Team"]
```

Prompt after a choice: "Should I log this in the decision tracker?"

## Tracking open questions

When something is undecided or owned by someone else:

```markdown
### ❓ [Question]
- **Context**: Why it must be decided.
- **Options on the table**: A, B, C.
- **Blocks**: What downstream work depends on it (optional).
- **Owner**: Who decides.
- **Target date**: When it's needed.
```

## Reviewing

On "what have we decided" / "show the log": read `docs/DECISIONS.md`, group by topic (stack, infra, methodology, content/product, data), and highlight anything Provisional or with attached open questions.

## Maintenance

- When a decision changes, move the old one to a **Superseded** section with a note — keep history, don't silently overwrite.
- When scope changes, re-scan the log for entries that have gone stale and update their status.
- Keep one date format and consistent status emojis.

See `templates/DECISIONS.template.md` for the full skeleton.
