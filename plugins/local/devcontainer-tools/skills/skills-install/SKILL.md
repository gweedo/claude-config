---
name: skills-install
description: |
  Install Claude Code skills into this project's .claude/skills/ from configured GitHub
  sources (a personal repo and public skill repos). Use when the user wants to install or
  sync project skills, or set up the default skill set.
version: 1.0.0
allowed-tools: [Read, Bash, AskUserQuestion]
---

# Skills Install

Installs Claude Code skills into `.claude/skills/` for the current project, driven by
`references/skills-registry.json`.

- **Default skills** are always installed, no confirmation needed.
- **Optional skills** must be offered to the user via AskUserQuestion before installing.

The actual install logic lives in `scripts/install-skills.sh`:

```bash
scripts/install-skills.sh                  # install all default skills
scripts/install-skills.sh --list-optional  # print "name<TAB>description" for optional skills
scripts/install-skills.sh <name> [<name>...]  # install specific skills by name
```

---

## Step 1 — Install default skills

Always run, without asking:

```bash
bash scripts/install-skills.sh
```

Currently this installs:
- `impeccable` — via `npx impeccable skills install`
- `mattpocock-skills` — shallow clone of https://github.com/mattpocock/skills into
  `.claude/skills/mattpocock-skills`

---

## Step 2 — Offer optional skills

Run:

```bash
bash scripts/install-skills.sh --list-optional
```

- If the output is empty, skip to Step 3.
- Otherwise, parse each `name<TAB>description` line and use AskUserQuestion
  (`multiSelect: true`) to ask which optional skills to install, e.g.:

  ```
  question: "Install any optional skills?"
  options:
    - <name 1> — <description 1>
    - <name 2> — <description 2>
  ```

- For each selected skill, run:

  ```bash
  bash scripts/install-skills.sh <name>
  ```

  (multiple names can be passed in one call)

---

## Step 3 — Report results

Summarize what was installed and where (`.claude/skills/<dest>` for each skill), and
note any skills that were skipped.

---

## Adding skills to the registry

Edit `references/skills-registry.json`:

- `sources` — named GitHub repos (`repo` URL + `ref`), reused by multiple skills.
  `ref` may be a branch, tag, or commit SHA — the installer shallow-fetches it.
- `skills[]` — one entry per installable skill:
  - `name` — unique identifier (used on the CLI and in AskUserQuestion)
  - `description` — shown for optional skills
  - `default` — `true` = always installed, `false` = optional
  - `type` — `"git"` (clone from a `source` and copy `path`, or the whole repo if
    `path` is `""`, into `.claude/skills/<dest>`) or `"npx"` (run `command` as-is)

To add skills from the personal repo (`https://github.com/gweedo/claude-config`,
already registered as the `personal` source), add entries with
`"type": "git", "source": "personal", "path": "<subdir-in-repo>"`.
