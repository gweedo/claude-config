#!/bin/bash
# Claude Code hook: Sync configuration to GitHub on session end
# Triggered by the Stop hook in settings.json

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"

cd "$CLAUDE_DIR" || exit 0

# Check if there are any changes to tracked config files
status=$(git status --porcelain \
  settings.json \
  settings.local.json \
  .gitignore \
  agents/ \
  hooks/ \
  memory/ \
  plugins/local/ \
  skills/ \
  2>/dev/null)

[ -z "$status" ] && exit 0

# Stage only config files (never credentials or ephemeral state)
git add \
  settings.json \
  settings.local.json \
  .gitignore \
  agents/ \
  hooks/ \
  memory/ \
  plugins/local/ \
  skills/ \
  2>/dev/null || true

git commit -m "Auto-sync $(date '+%Y-%m-%d %H:%M')" && git push 2>/dev/null || true
