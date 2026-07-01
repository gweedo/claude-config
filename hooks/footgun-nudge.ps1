# Claude Code PreToolUse hook (Windows / PowerShell version).
# Non-blocking nudge: when a file being written/edited matches a catalogued
# footgun's area glob, inject its rule + why into context before the edit.
# Mirrors hooks/footgun-nudge.sh; selected by the OS dispatcher in settings.json.
# See self-improve/docs/FOOTGUN_SURFACING.md and issue gweedo/claude-config#32.

$ErrorActionPreference = 'Stop'

$raw = [Console]::In.ReadToEnd()
try {
  $filePath = ($raw | ConvertFrom-Json).tool_input.file_path
} catch {
  exit 0
}
if ([string]::IsNullOrEmpty($filePath)) { exit 0 }

$catalogPath = Join-Path $HOME '.claude/self-improve/footguns.json'
if (-not (Test-Path $catalogPath)) { exit 0 }

try {
  $catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json
} catch {
  exit 0
}

$normPath = $filePath -replace '\\', '/'

foreach ($footgun in $catalog.footguns) {
  foreach ($glob in $footgun.area_globs) {
    if ($normPath -like $glob) {
      $context = "Catalogued footgun for this file: $($footgun.rule) -- $($footgun.why)"
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
}

exit 0
