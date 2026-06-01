# Plan: Nightly Claude config auditor subagent

## Context

The user's global Claude install at `~/.claude/` is already git-backed and has a `Stop`-hook sync (`hooks/sync-to-github.sh`) that pushes config changes to `origin/main` whenever a session ends. That covers *writing* changes — but nothing currently *validates* them, catches stale state, or runs on a fixed schedule.

The user wants a dedicated subagent that fires every night, audits the global config, and surfaces anything broken or unsynced as a reviewable pull request (not a direct push to main). This adds a verification layer on top of the existing sync, and gives the user a daily change-review surface.

## Design overview

Two artifacts:

1. **`~/.claude/agents/config-auditor.md`** — a new subagent file matching the style of [plan-writer.md](.claude/agents/plan-writer.md). It encodes the audit checks and the branch+PR flow.
2. **A scheduled routine** — created via the `/schedule` skill (`CronCreate` under the hood). Cron `0 3 * * *` (03:00 daily). The routine's prompt is short: "Invoke the `config-auditor` subagent against `~/.claude/`. Report what was found."

The audit is centralized in the subagent's system prompt so it can also be invoked ad-hoc (`@config-auditor`) any time the user wants a manual check, not only nightly.

## Audit checks (all four from user selection)

| # | Check | Pass criteria | On fail |
|---|-------|---------------|---------|
| 1 | `settings.json` + `settings.local.json` valid JSON | `python -m json.tool` exits 0 | Record the parse error; do NOT attempt auto-fix (risk of corrupting hooks) |
| 2 | Frontmatter in `agents/`, `commands/`, `skills/**/*.md` | Each .md starts with `---` block; `name:` present and equals filename stem; `description:` present | Record the file + missing field; do NOT auto-fix (user owns agent definitions) |
| 3 | Untracked/uncommitted files under tracked dirs | `git status --porcelain` against the same paths `sync-to-github.sh` already tracks (`settings*.json`, `.gitignore`, `agents/`, `hooks/`, `memory/`, `plugins/local/`) is empty | Stage these files into the audit branch (the auditor is the safety net when the Stop hook didn't fire) |
| 4 | Stale plans + broken plugin refs | `plans/*.md` mtime within 30 days; every path referenced by `plugins/local/marketplace.json` (and any `plugins/config.json`) exists on disk | List stale plans (info only, do not delete); list broken refs (info only, do not auto-fix) |

The audit produces a markdown report and — if there are any findings or any staged files — opens a PR.

## Sync flow (when findings exist)

```
cd ~/.claude
BRANCH="nightly-audit/$(date +%Y-%m-%d)"
git checkout -b "$BRANCH"        # or reset if branch already exists from earlier same-day run
# (stage files from check #3 if any)
git add settings.json settings.local.json .gitignore agents/ hooks/ memory/ plugins/local/
git commit -m "Nightly audit $(date +%Y-%m-%d): <N> findings"
git push -u origin "$BRANCH"
gh pr create --title "Nightly audit $(date +%Y-%m-%d)" --body "<full markdown report>"
```

PR body sections:
- **Summary** — counts per check
- **JSON validation** — pass/fail per settings file
- **Frontmatter validation** — table of `file | issue`
- **Sync gap** — table of files that were uncommitted (now staged in this PR)
- **Stale plans** — list (no action taken)
- **Broken plugin refs** — list (no action taken)

If all four checks pass and there's nothing to stage, the auditor exits silently with `"All checks passed — no PR opened"` and does not create a branch.

## Files to create

| Path | Purpose |
|------|---------|
| `~/.claude/agents/config-auditor.md` | The new subagent (frontmatter + system prompt with the audit logic above) |
| Schedule routine (no local file — created via `/schedule` skill, lives in Anthropic-side cron) | Nightly trigger at 03:00 |

## Subagent file: schema

```yaml
---
name: config-auditor
description: Nightly auditor for the global ~/.claude/ config. Validates settings JSON, agent/skill/command frontmatter, detects unsynced files, and flags stale plans + broken plugin refs. Opens a PR with findings.
tools: [Read, Glob, Grep, Bash, Edit, Write]
---
```

The system prompt body codifies:
- Exact paths to audit (`$HOME/.claude/`)
- The 4 checks in order, each with the pass criteria and on-fail action above
- The branch+PR flow (using `gh` CLI — already used elsewhere in the user's setup)
- "If nothing found, exit with a short message and do NOT create a branch or PR"
- Idempotency: if a `nightly-audit/<today>` branch already exists, force-update it rather than failing

## Critical files to reference

- [`~/.claude/hooks/sync-to-github.sh`](.claude/hooks/sync-to-github.sh) — source of truth for which paths are "tracked config" (reuse the same list in check #3)
- [`~/.claude/agents/plan-writer.md`](.claude/agents/plan-writer.md) — style template for the new subagent file (YAML frontmatter shape, prose style)
- [`~/.claude/settings.json`](.claude/settings.json) — existing Stop hook stays untouched; auditor is additive

## Scheduling step

After the subagent file is written, invoke `/schedule` with:
- Cron: `0 3 * * *`
- Routine name: `nightly-claude-config-audit`
- Prompt: `Run the config-auditor subagent on ~/.claude/. If it opens a PR, report the URL.`

The `/schedule` skill walks through routine creation — no separate file to author.

## Push the new subagent to GitHub

After the local file `~/.claude/agents/config-auditor.md` is created, it must be pushed to `origin/main` so the remote nightly routine can find it when it clones `gweedo/claude-config`. The first scheduled run is **2026-05-24 03:00 Rome**, so the push needs to land before then.

Steps (run from `~/.claude`):

```bash
cd ~/.claude
git status --porcelain agents/config-auditor.md   # confirm untracked
git add agents/config-auditor.md
git commit -m "Add config-auditor subagent for nightly config audit"
git push origin main
```

Verify push succeeded:

```bash
git log origin/main -1 --oneline
gh browse agents/config-auditor.md   # optional: open on GitHub
```

The existing `Stop` hook (`sync-to-github.sh`) would also push this file the next time a session ends, but pushing explicitly now removes timing risk for the first nightly run.

## Verification

1. **Subagent file lints**: `python -c "import yaml; yaml.safe_load(open('agents/config-auditor.md').read().split('---')[1])"` — frontmatter parses.
2. **Manual dry-run**: open a fresh Claude session, type `@config-auditor`, confirm it runs all 4 checks and either reports "all clear" or opens a PR. Inspect the PR diff before merging.
3. **Deliberate-fail test**: temporarily break `settings.local.json` JSON (add a trailing comma), re-invoke, confirm check #1 catches it and the PR body lists the parse error.
4. **Routine confirmation**: `/schedule list` should show `nightly-claude-config-audit` with `0 3 * * *`. Wait one cycle (or trigger with `/schedule run nightly-claude-config-audit`) and confirm a PR appears on GitHub the next morning if anything was off.

## Rollback

- Delete `~/.claude/agents/config-auditor.md`.
- `/schedule delete nightly-claude-config-audit`.
- No changes to `settings.json` or `sync-to-github.sh`, so the existing Stop-hook sync is unaffected by removing the auditor.
