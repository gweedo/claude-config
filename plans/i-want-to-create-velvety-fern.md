# Plan: Fix Mobile Stretching + Auto-Branch Hook

## Context

The portfolio's mobile layout is "stretched" — content overflows horizontally on small screens. The root cause is `.section-heading` (line 205 of `index.html`) has `white-space: nowrap` but the override to `white-space: normal` only kicks in at `max-width: 600px`. On phones between 600–900px (all modern phones in portrait), headings like "Experience" render as a single oversized unwrapping line, forcing the layout wider than the viewport. Two secondary issues compound this: the footer keeps its full 56px horizontal padding on mobile, and `about-stats` stays in a 2-column grid until 600px.

The user also wants a `PreToolUse` hook that auto-creates a git branch whenever Claude is about to edit files while on `main`, so future work always lands on a feature branch.

---

## Part 1 — Mobile CSS Fixes

**File:** [index.html](index.html) — only the `@media` blocks need to change.

### Fix 1 — Move section heading wrap to 900px (main fix)

In the `@media (max-width: 900px)` block (line 424), add:
```css
.section-heading { white-space: normal; }
```
Remove it from the `@media (max-width: 600px)` block (it can stay there too, but the 900px rule fixes the real range).

### Fix 2 — Footer padding on mobile

In the `@media (max-width: 900px)` block, change:
```css
footer { flex-direction: column; gap: 8px; text-align: center; }
```
to:
```css
footer { flex-direction: column; gap: 8px; text-align: center; padding: 20px 24px; }
```

### Fix 3 — About stats single column earlier

In the `@media (max-width: 900px)` block, add:
```css
.about-stats { grid-template-columns: 1fr 1fr; }
```
(keeps 2-col at 900px but it's already constrained by the grid — can leave or reduce to `1fr` at 600px which already exists)

Actually — leave `about-stats` as-is; it's fine at 2-col down to 600px. Focus on the two real issues.

---

## Part 2 — Auto-Branch Hook

**File:** [.claude/settings.json](.claude/settings.json)

Add a `PreToolUse` hook matching `Edit|Write` tools. Before any file edit, if the current branch is `main`, it auto-creates a timestamped `work/` branch:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -Command \"$b = git branch --show-current 2>$null; if ($b -eq 'main') { $ts = Get-Date -Format 'yyyyMMdd-HHmm'; git checkout -b \\\"work/$ts\\\" }\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo Reminder: rewrite plan/PLAN.md with the current project state before finishing."
          }
        ]
      }
    ]
  }
}
```

---

## Execution Order

1. Create branch `fix/mobile-responsive` manually (before the hook is in place)
2. Apply the CSS fixes to `index.html`
3. Update `.claude/settings.json` with the `PreToolUse` hook
4. Commit both changes on the feature branch
5. Push and open a PR → merge → auto-deploy

---

## Critical Files

| File | Change |
|------|--------|
| [index.html](index.html) | Add `white-space: normal` + `padding` fix to 900px media query |
| [.claude/settings.json](.claude/settings.json) | Add `PreToolUse` auto-branch hook |

---

## Verification

1. Open DevTools → toggle mobile device (375px width) — section headings should wrap, no horizontal scroll
2. Check footer at 375px — padding should be `24px`, not `56px`
3. On next edit session: start on `main`, make an edit → confirm a `work/YYYYMMDD-HHmm` branch is auto-created
