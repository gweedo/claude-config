# Claude Code PreToolUse hook (Windows / PowerShell version).
# Non-blocking nudge: when a Bash command looks like a migration or deploy step,
# remind Claude to verify the real postcondition before marking it done.
# Mirrors hooks/verify-outcome-nudge.sh; selected by the OS dispatcher in settings.json.
# See skills/verify-outcome/SKILL.md and issue gweedo/claude-config#31.

$ErrorActionPreference = 'Stop'

$raw = [Console]::In.ReadToEnd()
try {
  $command = ($raw | ConvertFrom-Json).tool_input.command
} catch {
  exit 0
}
if ([string]::IsNullOrEmpty($command)) { exit 0 }

$stateChangingPatterns = @(
  'alembic (upgrade|downgrade)'
  'manage\.py migrate'
  '(prisma|knex|flyway|liquibase|sequelize).*migrate'
  'terraform apply'
  'az .*(containerapp|webapp|functionapp) (update|deploy|create)'
  'kubectl (apply|rollout)'
  'docker (push|deploy)'
  'helm (install|upgrade)'
)

foreach ($pattern in $stateChangingPatterns) {
  if ($command -imatch $pattern) {
    $context = "This looks like a migrate/deploy step. Before marking it done, verify the actual postcondition (tables/revision exist, new revision is serving real traffic) rather than trusting the exit code -- see the verify-outcome skill."
    $output = @{
      hookSpecificOutput = @{
        hookEventName      = 'PreToolUse'
        permissionDecision = 'allow'
        additionalContext  = $context
      }
    }
    $output | ConvertTo-Json -Compress
    exit 0
  }
}

exit 0
