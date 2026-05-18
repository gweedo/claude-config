# Claude Code Configuration

Personal Claude Code configuration backup, auto-synced to GitHub at the end of every session.

## What's tracked

| Path | Purpose |
|------|---------|
| `settings.json` | Claude Code preferences (theme, model, notifications, hooks) |
| `settings.local.json` | Machine-local overrides (not pushed if sensitive) |
| `.gitignore` | Files excluded from this repo |
| `agents/` | Custom subagents (`.md` files loaded automatically by Claude Code) |
| `hooks/` | Shell scripts triggered by Claude Code lifecycle events |
| `memory/` | Persistent memory files used across sessions |

## What's not tracked

Excluded by `.gitignore`:
- `.credentials.json` — auth tokens
- `projects/` — per-session conversation history
- `sessions/` — session state
- `cache/`, `backups/`, `shell-snapshots/`, `ide/` — ephemeral runtime data

## Auto-sync

The `hooks/sync-to-github.sh` script runs automatically on every Claude Code session end (`Stop` hook). It stages changes to the tracked paths above and pushes them to this repo.

Hook is registered in `settings.json`:
```json
"hooks": {
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "bash \"$HOME/.claude/hooks/sync-to-github.sh\"",
      "async": true
    }]
  }]
}
```

## Custom agents

Agents in `agents/` are picked up automatically by Claude Code. Invoke them in any session by describing what you want — Claude will route to the matching agent.

| Agent | Purpose |
|-------|---------|
| `test-writer.md` | Analyzes a file or folder, proposes a test plan for review, then writes tests on approval |

## Restore on a new machine

```bash
git clone https://github.com/gweedo/claude-config.git ~/.claude
```

Claude Code will pick up settings, agents, and hooks automatically on next launch.
