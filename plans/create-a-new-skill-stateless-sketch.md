# Plan: `devcontainer-init` Skill

## Context

The user wants a Claude Code skill that initializes a `.devcontainer` folder with basic configurations when invoked as a slash command (`/devcontainer`). The skill should support the three most common stacks (Node.js, Python, Generic Ubuntu) and create a ready-to-use `devcontainer.json` without manual scaffolding.

---

## Files to Create

```
C:\Users\Guido.DESKTOP-45P6U2C\.claude\plugins\marketplaces\claude-plugins-official\plugins\devcontainer-tools\
├── .claude-plugin\
│   └── plugin.json
└── skills\
    └── devcontainer-init\
        └── SKILL.md
```

---

## File Contents

### `.claude-plugin/plugin.json`

```json
{
  "name": "devcontainer-tools",
  "version": "1.0.0",
  "description": "Scaffolds .devcontainer configurations for Node.js, Python, and generic Ubuntu projects",
  "author": {
    "name": "ThisGweedo",
    "email": "guido.s1998@gmail.com"
  }
}
```

### `skills/devcontainer-init/SKILL.md`

YAML frontmatter:
- `name: devcontainer-init`
- `description:` triggers on `/devcontainer`, `/devcontainer-init`, or natural language like "initialize a devcontainer", "scaffold .devcontainer"
- `argument-hint: [node|python|generic]`
- `allowed-tools: [Read, Glob, Write, Bash]`

Skill body steps:
1. **Determine stack** — use `$ARGUMENTS` if it's `node`, `python`, or `generic`; otherwise `AskUserQuestion` to pick one
2. **Check for existing `.devcontainer`** — Glob for `.devcontainer/**`; warn and require confirmation before overwriting
3. **Validate prerequisites** (informational only, no abort) — check `package.json` (node) or `requirements.txt` (python)
4. **Write files** — create `.devcontainer/devcontainer.json` using the inline template for the chosen stack
5. **Report** — list created files and remind the user to "Reopen in Container" in VS Code

Templates (all inline in SKILL.md, no separate asset files):

| Stack   | Image                                                   | Ports       | postCreateCommand              | Extensions                            |
|---------|---------------------------------------------------------|-------------|--------------------------------|---------------------------------------|
| node    | `mcr.microsoft.com/devcontainers/javascript-node:20`   | 3000, 5173, 4173 | `npm install`             | ESLint, Prettier, Tailwind, Volar     |
| python  | `mcr.microsoft.com/devcontainers/python:3.12`          | 8000        | `pip install -r requirements.txt` | Python, Pylance, Black, Ruff       |
| generic | `mcr.microsoft.com/devcontainers/base:ubuntu`          | —           | —                              | none                                  |

---

## Edge Cases

| Situation | Handling |
|-----------|----------|
| `.devcontainer` already exists | Warn + ask confirmation; abort if declined |
| No `package.json` (node) | Warn but continue |
| No `requirements.txt` (python) | Warn but continue |
| Unrecognised/empty argument | Ask user to choose from the three presets |
| Mixed-case argument (`Node`, `PYTHON`) | Normalize to lowercase before matching |

---

## Verification

After implementation:
1. Open a project folder in VS Code with Claude Code
2. Run `/devcontainer` with no argument → should prompt for stack choice
3. Run `/devcontainer node` → should create `.devcontainer/devcontainer.json` without prompting
4. Run again in the same folder → should warn about existing folder and ask to confirm overwrite
5. Check the generated `devcontainer.json` matches the template for each stack
