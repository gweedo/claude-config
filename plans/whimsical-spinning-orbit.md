# Plan: Refactor Hooks into Separate Scripts

## Context
Currently, the Stop hook has an inline bash command embedded in `~/.claude/settings.json`. This refactoring moves hook scripts into a dedicated `~/.claude/hooks/` directory to improve maintainability, make scripts independently testable, and make it easier to add more hooks in the future.

## Current State
- **Location**: `~/.claude/settings.json`
- **Current Hook**: Stop hook with inline command (git status check → commit → push workflow)
- **Problem**: Long bash command embedded in JSON, hard to edit/test, not scalable for multiple hooks

## Proposed Approach

### 1. Create Directory Structure
```
~/.claude/
├── hooks/                    # New hooks directory
│   └── sync-to-github.sh    # Extract Stop hook script
├── settings.json            # Update to reference script
└── .gitignore              # No changes needed
```

### 2. Extract Hook Script
- **File**: `~/.claude/hooks/sync-to-github.sh`
- **Content**: Extract the current Stop hook bash command into a standalone script
- **Current command**:
  ```bash
  cd ~/.claude && status=$(git status --porcelain settings.json settings.local.json .gitignore 2>/dev/null) && [ -n "$status" ] && git add settings.json settings.local.json .gitignore && git commit -m "Auto-sync $(date '+%Y-%m-%d %H:%M')" && git push 2>/dev/null || true
  ```

### 3. Update Hook Configuration
- **File**: `~/.claude/settings.json`
- **Change**: Replace inline command with call to script using $HOME variable
- **New hook structure**:
  ```json
  {
    "type": "command",
    "shell": "bash",
    "command": "bash \"$HOME/.claude/hooks/sync-to-github.sh\"",
    "statusMessage": "Syncing Claude config to GitHub...",
    "async": true
  }
  ```

## Files to Modify/Create
- **Create**: `~/.claude/hooks/` directory
- **Create**: `~/.claude/hooks/sync-to-github.sh` (Stop hook script)
- **Modify**: `~/.claude/settings.json` (update Stop hook to reference script)
- **Check**: `~/.claude/.gitignore` (ensure hooks/ is NOT excluded so scripts are version-controlled)

## Implementation Details
- Scripts will be tracked in git (not in .gitignore)
- Structure allows easy addition of more hook scripts (e.g., `pre-commit.sh`, `post-tooluse.sh`, etc.)
- Each script should be standalone and self-contained

## Verification
1. `~/.claude/hooks/sync-to-github.sh` created with extracted bash command
2. Script is executable (chmod +x added if needed)
3. `settings.json` Stop hook references the script: `bash ~/.claude/hooks/sync-to-github.sh`
4. Run test session: Hook fires at session end, commits and pushes to GitHub
5. Verify scripts are committed to GitHub repo (not in .gitignore)
