---
name: devcontainer-init
description: |
  Scaffold a .devcontainer (devcontainer.json) for the current project. Use when the user
  wants to set up or initialize a development container — for a Node.js, Python, or generic stack.
version: 1.4.0
argument-hint: [node|python|generic]
allowed-tools: [Read, Glob, Write, Edit, AskUserQuestion]
---

# Devcontainer Init

Scaffold a `.devcontainer` folder with a ready-to-use `devcontainer.json` for the current project.

This skill is **stack-agnostic**: it knows nothing about specific languages or tools on
its own. Every stack — its label, base image, ports, `postCreateCommand`, extensions,
settings, detection signals, and prerequisite checks — is declared as data in
`references/defaults.json`, and the file content to write lives in
`references/templates/<stack>.devcontainer.json`. Adding or changing a stack means
editing those reference files only, never this skill body. The folder layout is
documented in `references/folder-tree.md`.

**Rule (applies to every step): stay tech-agnostic.** Take all feature refs, options,
extension ids, templates, and commands from `references/defaults.json` — never hardcode
them in this body.

---

## Step 1 — Scan the project folder FIRST

Always inspect the project before proposing anything. Do **not** ask the user to pick a
stack, and do **not** write any file, until this scan is done — its results drive the
later steps.

1. Read `references/defaults.json`.
2. For each stack under `stacks`, run Glob for every pattern in that stack's
   `detectGlobs` array (in the current working directory). A stack "matches" if any of
   its globs return results. Stacks with an empty `detectGlobs` (e.g. the fallback
   stack) never match by detection.
3. Tally which stacks matched:
   - **exactly one** matched → that is the detected stack (lead with it in Step 2).
   - **more than one** matched → the project is multi-stack (e.g. a monorepo). Do not
     silently pick one; surface all matches in Step 2 and let the user choose, noting
     that a single-stack template covers only part of the repo.
   - **none** matched → no detection; fall back to asking with no pre-selection.
4. Also Glob for `CLAUDE.md` and `.claude/**`; if present, read them for any stated
   stack, tooling, or version constraints and honor those over the defaults.

Briefly report what the scan found before moving on.

---

## Step 2 — Determine the target stack

- If `$ARGUMENTS` (lowercased) matches a key under `stacks` in `references/defaults.json`,
  use that stack — but cross-check it against the Step 1 scan and flag any mismatch.
- Otherwise, use AskUserQuestion with one option per key under `stacks`, using each
  stack's `label` as the option description. **Lead with the stack(s) the Step 1 scan
  detected** and mark them "(detected)":

  ```
  question: "Which stack should I generate the devcontainer for?"
  options:
    - <detected stack> — <label>   (detected)
    - <other stacks>   — <label>
  ```

  Wait for the answer before continuing.

The user's argument is: `$ARGUMENTS`

---

## Step 3 — Check for an existing `.devcontainer`

Use Glob with pattern `.devcontainer/**` in the current working directory.

- If results are returned, use AskUserQuestion:

  ```
  question: "A .devcontainer folder already exists. Overwrite its contents?"
  options:
    - Yes, overwrite
    - No, cancel
  ```

  If the user chooses "No, cancel" (or any non-affirmative), stop immediately and reply:
  > "Cancelled — no files were changed."

---

## Step 4 — Validate stack prerequisites (warn only, do not abort)

Read `references/defaults.json` and look up `stacks.<stack>.prerequisiteFile` and
`stacks.<stack>.prerequisiteWarning` for the chosen stack.

- If `prerequisiteFile` is non-null, use Glob for that file in the project root.
- If it is not found, note the corresponding `prerequisiteWarning` to repeat in Step 7.
- If `prerequisiteFile` is `null`, no validation is needed.

---

## Step 5 — Write the files

1. Read `references/templates/<stack>.devcontainer.json` (the chosen stack's template).
2. Write its contents verbatim to `.devcontainer/devcontainer.json`.

The templates already include the baseline extensions described in
`references/default-extensions.md` — no merging is required.

---

## Step 6 — Add LLM code support (MANDATORY — always ask)

The templates ship the LLM **editor extension** only; that does **not** install a coding
assistant *inside* the container. Always ask the user whether they want LLM code support
installed — never decide for them — and install it **independently of the stack** as a
devcontainer **feature**, so the CLI is present at build time on `node`, `python`, and
`generic` alike.

1. Read `llmCodeSupport` from `references/defaults.json` (`feature`, `featureOptions`,
   `extension`, `verifyCommand`, `note`).
2. Use AskUserQuestion (this prompt is mandatory):

   ```
   question: "Install LLM code support (<llmCodeSupport.label>) into the container? It adds the CLI as a stack-independent devcontainer feature, not just the editor extension."
   options:
     - Yes — add it (Recommended)   <llmCodeSupport.note>
     - No  — extension only
   ```

3. If **yes**: Edit `.devcontainer/devcontainer.json` to add a top-level `"features"`
   object (create it if absent) with `llmCodeSupport.feature` as a key mapped to
   `llmCodeSupport.featureOptions`. Ensure `llmCodeSupport.extension` is in the
   `customizations.vscode.extensions` array (it already is in the templates — add it only
   if missing). Record `verifyCommand` to surface in Step 8 so the user can confirm the
   CLI after the container builds.
4. If **no**: leave the file as written (extension only) and note in Step 8 that the CLI
   was not installed and how to add it later.

---

## Step 7 — Initialize global git config (MANDATORY — always ask)

A freshly built container has **no git identity** and none of the usual quality-of-life
defaults, so commits fail or get attributed to the wrong author. Always offer to seed a
global git config. Apply it **independently of the stack** so `node`, `python`, and
`generic` are all covered.

1. Read `gitConfig` from `references/defaults.json` (`template`, `targetFile`,
   `placeholders`, `applyCommand`, `note`).
2. Use AskUserQuestion (this prompt is mandatory):

   ```
   question: "Initialize a global git config (<gitConfig.label>) in the container? It's layered in via include.path, so it won't clobber an existing ~/.gitconfig."
   options:
     - Yes — add it (Recommended)   <gitConfig.note>
     - No  — skip git config
   ```

3. If **yes**:
   - Ask for the committer identity with AskUserQuestion (one question, two fields are
     fine to combine into sequential prompts): the git **user name** and **email** to
     embed. If the user declines to provide them, leave the placeholders in place and
     flag in Step 9 that they must be filled before committing.
   - Read `references/templates/gitconfig.template`, substitute
     `gitConfig.placeholders.name` and `gitConfig.placeholders.email` with the answers,
     and Write the result to `gitConfig.targetFile`.
   - Edit `.devcontainer/devcontainer.json` to ensure `gitConfig.applyCommand` runs on
     create: append it to the existing `postCreateCommand` with ` && ` if one is present,
     otherwise add `postCreateCommand` set to `gitConfig.applyCommand`.
4. If **no**: write nothing and note in Step 9 that git identity must be configured
   manually inside the container before the first commit.

---

## Step 8 — Offer to install Claude skills/plugins

A devcontainer rebuild starts from a clean `.claude/skills/`, so always ask whether to
seed project skills now. Use AskUserQuestion:

```
question: "Want me to install Claude Code skills into this project (.claude/skills/) too?"
options:
  - Yes — run the skills-install skill
  - No  — skip skills
```

- If yes, invoke the companion **`skills-install`** skill (same `devcontainer-tools`
  plugin), which installs the default skill set and offers optional skills from the
  configured GitHub sources.
- If no, skip — mention they can run `/skills-install` later.

---

## Step 9 — Report results

After writing the file, output a summary, for example:

```
Scan:
  Detected <stack> (<matched signal>).

Created:
  .devcontainer/devcontainer.json  (<stack> preset)
  .devcontainer/gitconfig          (or: skipped — git config not initialized)

LLM code support:
  Added <llmCodeSupport.label> as a devcontainer feature  (or: skipped — extension only)

Git config:
  Wrote .devcontainer/gitconfig and wired it via include.path  (or: skipped)

Skills:
  Installed default skill set into .claude/skills/  (or: skipped)

Next steps:
  • Open this folder in VS Code and select "Reopen in Container" to start the devcontainer.
  • Adjust forwardPorts or extensions in .devcontainer/devcontainer.json as needed.
  • After the container builds, verify the assistant CLI: `<llmCodeSupport.verifyCommand>`.
```

If a prerequisite warning was noted in Step 4, repeat it here as a reminder. If LLM code
support was installed, remind the user the CLI ships unauthenticated (per
`llmCodeSupport.note`). If it was skipped, note it can be added later by re-running this
skill or adding the `llmCodeSupport.feature` to `.devcontainer/devcontainer.json`.

If git config was written but the identity placeholders were left unfilled, remind the
user to replace `gitConfig.placeholders.name`/`.email` in `.devcontainer/gitconfig`
before committing. If git config was skipped, note it can be added later by re-running
this skill or running `git config --global user.name`/`user.email` inside the container.
