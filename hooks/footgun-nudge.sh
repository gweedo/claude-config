#!/bin/bash
# Claude Code PreToolUse hook (Edit|Write matcher).
# Non-blocking nudge: when a file being written/edited matches a catalogued
# footgun's area glob, inject its rule + why into context before the edit.
# See self-improve/docs/FOOTGUN_SURFACING.md and issue gweedo/claude-config#32.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

CATALOG="$HOME/.claude/self-improve/footguns.json"
[ -f "$CATALOG" ] || exit 0

NORM_PATH="${FILE_PATH//\\//}"

while IFS= read -r entry; do
  [ -z "$entry" ] && continue
  RULE=$(echo "$entry" | jq -r '.rule')
  WHY=$(echo "$entry" | jq -r '.why')
  while IFS= read -r glob; do
    [ -z "$glob" ] && continue
    if [[ "$NORM_PATH" == $glob ]]; then
      CONTEXT="Catalogued footgun for this file: ${RULE} -- ${WHY}"
      CONTEXT_JSON=$(printf '%s' "$CONTEXT" | jq -Rs '.')
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":%s}}\n' "$CONTEXT_JSON"
      exit 0
    fi
  done < <(echo "$entry" | jq -r '.area_globs[]?')
done < <(jq -c '.footguns[]?' "$CATALOG" 2>/dev/null)

exit 0
