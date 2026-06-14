# Default VS Code extensions

Baseline `customizations.vscode.extensions` that every `.devcontainer/devcontainer.json` should
include, regardless of stack. These are already baked into every file under
`references/templates/` (also listed in `references/defaults.json` as
`baselineExtensions`), so a fresh scaffold needs no extra step. Use this file when
reviewing an *existing* `.devcontainer/devcontainer.json` for missing baseline extensions.

## All stacks (baseline)

- `anthropic.claude-code`
- `github.vscode-github-actions`
