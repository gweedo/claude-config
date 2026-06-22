# Claude Code PreToolUse hook (Windows / PowerShell version).
# Blocks dangerous git operations on the Bash matcher.
# Parses the hook JSON from stdin natively (no jq dependency).
# Mirrors hooks/block-dangerous-git.sh; selected by the OS dispatcher in settings.json.

$ErrorActionPreference = 'Stop'

$raw = [Console]::In.ReadToEnd()
try {
  $command = ($raw | ConvertFrom-Json).tool_input.command
} catch {
  exit 0
}
if ([string]::IsNullOrEmpty($command)) { exit 0 }

$dangerousPatterns = @(
  'push --force'
  'push -f '
  'push -f$'
  'push origin --delete'
  'push origin -d '
  'push.*([ :]main(\s|$)|refs/heads/main)'
  'git reset --hard'
  'reset --hard'
  'git clean -fd'
  'git clean -f'
  'git branch -D'
  'git checkout \.'
  'git restore \.'
)

foreach ($pattern in $dangerousPatterns) {
  if ($command -cmatch $pattern) {
    [Console]::Error.WriteLine("BLOCKED: '$command' matches dangerous pattern '$pattern'. The user has prevented you from doing this.")
    exit 2
  }
}

exit 0
