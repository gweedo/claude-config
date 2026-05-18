#!/bin/bash
# Claude Code hook: Sync configuration to GitHub on session end

cd ~/.claude && status=$(git status --porcelain settings.json settings.local.json .gitignore 2>/dev/null) && [ -n "$status" ] && git add settings.json settings.local.json .gitignore && git commit -m "Auto-sync $(date '+%Y-%m-%d %H:%M')" && git push 2>/dev/null || true
