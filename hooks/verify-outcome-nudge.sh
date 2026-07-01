#!/bin/bash
# Claude Code PreToolUse hook (Bash matcher).
# Non-blocking nudge: when a Bash command looks like a migration or deploy step,
# remind Claude to verify the real postcondition before marking it done.
# See skills/verify-outcome/SKILL.md and issue gweedo/claude-config#31.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

STATE_CHANGING_PATTERNS=(
  "alembic (upgrade|downgrade)"
  "manage\.py migrate"
  "(prisma|knex|flyway|liquibase|sequelize).*migrate"
  "terraform apply"
  "az .*(containerapp|webapp|functionapp) (update|deploy|create)"
  "kubectl (apply|rollout)"
  "docker (push|deploy)"
  "helm (install|upgrade)"
)

for pattern in "${STATE_CHANGING_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qEi "$pattern"; then
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":"This looks like a migrate/deploy step. Before marking it done, verify the actual postcondition (tables/revision exist, new revision is serving real traffic) rather than trusting the exit code — see the verify-outcome skill."}}
JSON
    exit 0
  fi
done

exit 0
