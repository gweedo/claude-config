---
name: file-review
description: |
  Review one or more files for completeness and correctness after they were written or
  edited. Use when the user wants to review or double-check files, or "check everything."
  Stack- and language-agnostic.
version: 1.2.0
argument-hint: [path ...]
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, WebFetch, AskUserQuestion]
---

# File Review

Do a thorough, **tech-agnostic** review of files — "check everything." This skill makes
no assumptions about language, framework, or project type. It reviews any text/config
file by its general shape, never by a hardcoded stack.

The rule this skill enforces: **never report a file as done without reading it in full
and running the checklist below.** No skimming, no assuming a write succeeded.

---

## Step 1 — Determine the scope

Decide which files to review, in this order:

1. If `$ARGUMENTS` lists paths, review those (expand directories with Glob).
2. Otherwise review the files just created/edited in this session.
3. If neither is clear, use AskUserQuestion to ask which path(s) to review. Do not guess.

List the resolved file set back to the user before reviewing.

The user's argument is: `$ARGUMENTS`

---

## Step 2 — Read every file in full

For each file in scope, use Read on the **whole** file (not a fragment). Large files:
read in successive chunks until the end — do not stop early. A review of a file you have
not fully read is invalid.

---

## Step 3 — Per-file checks (generic)

Apply to every file, regardless of type:

- **Well-formed for its format.** If the file is a structured format (JSON, YAML, TOML,
  XML, INI, etc.), verify it parses. Prefer a parser already available on the system via
  Bash (e.g. `python -c`, `jq`, `node`) — pick by file extension, don't assume one
  toolchain exists. If no parser is available, fall back to a structural read (balanced
  braces/brackets/quotes, consistent indentation).
- **Complete, not truncated.** No abrupt EOF, no half-written blocks, no unclosed
  delimiters, no empty file that should have content.
- **No leftover placeholders.** Grep for `TODO`, `FIXME`, `XXX`, `PLACEHOLDER`,
  `<...>`, `CHANGEME`, `lorem ipsum`, and merge-conflict markers (`<<<<<<<`, `=======`,
  `>>>>>>>`).
- **Encoding / whitespace.** No stray BOM where it doesn't belong, no obvious mojibake,
  no mixed line endings within one file.
- **Internally consistent.** Keys/sections/headings aren't duplicated or contradictory.

---

## Step 4 — Cross-file checks

Across the whole set:

- **References resolve.** Any path, filename, import, include, link, or `$ref` a file
  points at should exist (Glob/Read to confirm) or be clearly external.
- **Names agree.** Identifiers, versions, and shared values used in more than one file
  match (e.g. a name declared in one file and referenced in another).
- **No contradiction or accidental duplication** between files that describe the same
  thing.
- **Nothing expected is missing.** If the set implies a companion file (a referenced
  script, template, or config), flag its absence.

---

## Step 5 — LLM code support check (MANDATORY when a devcontainer is in scope)

If the reviewed set includes a devcontainer config (`.devcontainer/devcontainer.json` or a
`devcontainer.json` at any path), you **must** check it for **LLM code support** and, if
none is present, do the same thing `devcontainer-init` does: **ask the user and offer to
install it**. This is a deliberate, narrow exception to this skill's "review, don't edit"
rule — it applies *only* to adding LLM code support, nothing else.

1. **Define what counts.** Read the sibling skill's data at
   `../devcontainer-init/references/defaults.json` → `llmCodeSupport` (`feature`,
   `featureOptions`, `extension`, `verifyCommand`, `note`). Stay tech-agnostic — take the
   feature ref and extension id from that file, never hardcode them here.
2. **Look for it in the config.** "LLM code support" means the CLI is actually installed,
   i.e. `llmCodeSupport.feature` appears as a key under the top-level `"features"` object.
   The editor `extension` alone does **not** count — it adds editor integration but does
   not install the CLI in the container.
3. **If the feature is missing**, use AskUserQuestion:

   ```
   question: "This devcontainer has no LLM code support installed (CLI feature absent). Add it?"
   options:
     - Yes — add it (Recommended)   <llmCodeSupport.note>
     - No  — leave as is
   ```

   - If **yes**: Edit the config to add `llmCodeSupport.feature` (mapped to
     `featureOptions`) under a top-level `"features"` object, and ensure
     `llmCodeSupport.extension` is in `customizations.vscode.extensions`. Report it under
     a "Fixed" line in Step 7 and surface `verifyCommand` + the auth note.
   - If **no**: record it as a ⚠ finding in Step 7 ("LLM code support absent — declined").
4. **If the feature is present**, record it as ✅ in Step 7 and make no change.

If no devcontainer config is in scope, skip this step entirely.

---

## Step 6 — Version currency check (best-effort, informational)

For any **version-bearing declaration** in the files — a pinned dependency, a base image
tag, a runtime/language version, a tool version, a schema or API version — assess whether
it is current. Stay tech-agnostic: reason from the **shape of the version and how it is
pinned**, never from hardcoded knowledge of one ecosystem.

1. **Identify the pin generically.** Find version-shaped values (`name@1.2.3`,
   `repo:1-foo-bar`, `>=2.0,<3`, `version = "4.5.6"`, `*-bookworm`, lockfile entries, a
   `requires`/`engines` field). Record the current value and how tightly it is pinned —
   **exact**, **range**, or **floating** — since that governs whether an update is even
   in scope.

2. **Check whether a newer version exists — only when it is cheap and tech-neutral.** Use
   a source the file already implies, discovered not assumed:
   - the package manager that owns the manifest, **if its CLI is already present** (an
     "outdated"-style query) — detect it, don't hardcode a toolchain;
   - otherwise the registry/index the pin already points at (a tags or releases endpoint)
     via WebFetch or `curl`.
   If neither is reachable, mark the result **unknown** and stop — never invent a "latest"
   version.

3. **Classify each version and report — never edit.** This skill informs; it does not bump
   anything.
   - ✅ **current** — already latest within the pin's intent.
   - ⬆ **update available, low risk** — newer **minor/patch** within the same major;
     usually safe. State that a newer version exists.
   - ⚠ **update available, may break** — newer **major**, or the pinned version is
     yanked/EOL, or the jump crosses a documented breaking boundary. Report as "newer
     version available — verify before updating," with the reason it may break.
   - ❔ **unknown** — could not verify (offline, private/unknown registry, unrecognized
     version scheme).

   In every case the action is the same: **state that a newer version is available** (and
   which), plus its risk class. Do **not** change the pin — major bumps especially are
   surfaced, not applied. Classification comes from the version number's shape and the
   pin's tightness, not language-specific rules.

---

## Step 7 — Report findings

Output a per-file checklist with clear status and `path:line` for anything actionable:

```
file-review — N file(s)

path/to/file-a        ✅ ok
path/to/file-b        ⚠ 2 issues
  • file-b:14 — unresolved reference to ./missing.json
  • file-b:30 — leftover TODO

Cross-file:
  ⚠ version mismatch: file-a says 1.2.0, file-c says 1.1.0

LLM code support:
  ✅ devcontainer.json — Claude Code feature present
  (or: ⚠ absent — declined  /  Fixed: added Claude Code feature  /  n/a — no devcontainer in scope)

Versions:
  ✅ file-a:3 — runtime pinned 3-foo, current
  ⬆ file-b:8 — dep 1.4.2 pinned; 1.6.0 available (low risk, minor)
  ⚠ file-c:5 — base image :2-bar; :3-bar available (major — verify before updating)
  ❔ file-d:9 — pin 7.1.0; latest unknown (registry not reachable)

Summary: 1 ok, 1 with warnings, 0 failed.
```

Use ✅ (clean), ⚠ (warning, non-blocking), ❌ (broken/invalid). If everything passes,
say so explicitly. Do not propose or apply fixes unless the user asks — this skill
reviews; it does not edit. **The sole exception is Step 5** (adding LLM code support to a
devcontainer), which edits only after the user says yes.
