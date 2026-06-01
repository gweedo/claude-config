# Plan: Plan-Writer Custom Subagent

## Context
The user wants a reusable agent that, given a task description, scaffolds a structured `plans/` folder inside the current project. The folder contains a human-readable `.md` summary **and** a `chunks/` subfolder with small YAML files — one per plan phase. Each YAML file is shaped to give Claude exactly the context it needs for that phase and nothing more, reducing token waste when referencing individual parts of the plan later. The agent follows the same review-before-write pattern as `test-writer`.

---

## What Gets Created

**One file:** `~/.claude/agents/plan-writer.md`

At runtime, per project the agent produces:

```
<project-root>/
  plans/
    <task-slug>.md              ← human-readable overview (for reading/sharing)
    <task-slug>/
      00_meta.yaml              ← project stack + goal + constraints
      01_discovery.yaml         ← findings from codebase exploration
      02_steps.yaml             ← ordered implementation steps
      03_verify.yaml            ← how to confirm the work is done
```

---

## How the User Invokes It

```
Use the plan-writer agent: add OAuth2 Google login
```
```
plan-writer agent on: refactor auth middleware to use JWT RS256
```

---

## YAML Chunk Design (token-efficiency rationale)

Each YAML file is a self-contained context slice. Claude can be handed **one chunk** instead of the full plan when working on a specific phase:

### `00_meta.yaml`
```yaml
project: my-app
stack: [typescript, react, postgresql]
goal: "Add OAuth2 Google login"
constraints:
  - no_breaking_changes: true
  - existing_auth: src/auth/jwt.ts
status: in_progress
created: 2025-01-15
```

### `01_discovery.yaml`
```yaml
phase: discovery
status: done
key_files:
  - src/auth/jwt.ts
  - src/routes/auth.ts
deps_relevant: [jsonwebtoken, passport]
patterns:
  routes: src/routes/*.ts
  middleware: src/middleware/
gaps: ["no OAuth strategy exists", "no session store configured"]
```

### `02_steps.yaml`
```yaml
phase: implementation
steps:
  - id: 1
    file: package.json
    action: "add passport-google-oauth20 dependency"
    status: todo
  - id: 2
    file: src/auth/google.ts
    action: "create GoogleStrategy with clientID/clientSecret"
    status: todo
  - id: 3
    file: src/routes/auth.ts
    action: "add GET /auth/google and /auth/google/callback routes"
    status: todo
```

### `03_verify.yaml`
```yaml
phase: verification
checks:
  - cmd: "npm test"
  - manual: "complete Google OAuth flow in browser"
  - regression: "existing JWT login still works"
rollback: "revert src/auth/google.ts, src/routes/auth.ts"
```

**Why YAML over MD for chunks?**
- ~40% fewer tokens than equivalent prose
- Machine-parseable: Claude can update `status: todo → done` inline
- No ambiguity: structured keys beat natural language for step references

---

## Sync Rule (YAML ↔ MD always in sync)

**YAML is the single source of truth.** The `.md` is always regenerated from the YAML files — it is never edited directly by the agent.

The rule is simple: **after any write to any YAML file, immediately regenerate `<task-slug>.md` from all 4 chunks.**

The `.md` is a flattened human-readable rendering of the YAML:
- `00_meta` → header block (goal, stack, status)
- `01_discovery` → "## Findings" section
- `02_steps` → "## Steps" table (id | action | file | status)
- `03_verify` → "## Verification" checklist

This way the user can always read `.md` for a quick overview and hand any `.yaml` chunk to Claude for targeted execution — both are guaranteed consistent.

---

## Agent Workflow (4 phases)

### Phase 1 — Discover
- Detect project root (nearest `.git`, `package.json`, `pyproject.toml`, etc.)
- Read stack/language from config files
- Grep for files relevant to the stated goal
- Identify constraints (existing patterns, dependencies, "no breaking changes" signals)

### Phase 2 — Draft chunks + MD
- Write all 4 YAML files into `plans/<task-slug>/`
- Immediately generate `plans/<task-slug>.md` from the YAML (sync rule applies from the start)
- Print the MD summary and `02_steps.yaml` in the conversation

### Phase 3 — Await approval
> I've drafted the plan in `plans/<slug>/`. Review above and reply **yes** to finalize, describe changes to adjust, or **cancel** to discard.

- On changes: update the relevant YAML file(s) → regenerate `.md` → show updated MD, ask again
- On cancel: delete the `plans/<slug>/` folder and `plans/<slug>.md`, leave nothing behind

### Phase 4 — Finalize
- Set `status: approved` in `00_meta.yaml` → regenerate `.md` (sync)
- Print: `Plan ready. Use plans/<slug>/02_steps.yaml for implementation context.`

### Ongoing sync (after initial creation)
Any time the agent is asked to update the plan (mark a step done, add a finding, change a constraint):
1. Edit the relevant YAML file only
2. Immediately regenerate and overwrite `<task-slug>.md`
3. Never let the two diverge

---

## Critical Files

| File | Action |
|------|--------|
| `~/.claude/agents/plan-writer.md` | **Create** |

Runtime output per project (created by agent, not setup):
- `plans/<slug>.md`
- `plans/<slug>/00_meta.yaml`
- `plans/<slug>/01_discovery.yaml`
- `plans/<slug>/02_steps.yaml`
- `plans/<slug>/03_verify.yaml`

---

## Verification

1. Open a Claude Code session in any project with source files.
2. Say: `Use the plan-writer agent: <describe a task>`
3. Confirm agent produces the `plans/` structure and pauses for review.
4. Say "yes" — confirm `00_meta.yaml` has `status: approved`.
5. Optionally: hand `02_steps.yaml` directly to Claude and confirm it has enough context to start implementing step 1.

---

# Plan: Test-Writer Custom Subagent

## Context
The user wants a reusable agent that generates tests for a given file or folder. The agent must first produce a human-readable plan, wait for review/approval, and only then write the actual test files. The best primitive for this in Claude Code is a **custom subagent** — a markdown file placed in `~/.claude/agents/` that Claude Code loads automatically and makes available in any session.

---

## What Gets Created

**One file:** `C:\Users\Guido.DESKTOP-45P6U2C\.claude\agents\test-writer.md`

That's it. No dependencies, no scripts, no API keys. Claude Code reads this file and makes the agent available immediately in every session.

---

## How the User Invokes It

In any Claude Code session, simply say:

```
Use the test-writer agent on src/utils/auth.py
```
or
```
Run the test-writer agent on src/components/
```

Claude Code will spawn the subagent with the target path as context.

---

## Agent Workflow (4 phases, built into the agent prompt)

### Phase 1 — Discover
- Read the target file(s) using `Read` / `Glob` / `Grep`
- Detect language from file extensions
- Find the testing framework by reading `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.
- Find existing test files to copy naming and folder conventions
- Identify testable units: exported functions, classes, methods, API route handlers, edge cases, error branches

### Phase 2 — Write Plan
- Write a `TEST_PLAN.md` file at the project root (or next to the target if no root is detectable)
- Format:
  ```markdown
  ## TEST_PLAN.md
  ### Target: src/utils/auth.py
  #### Tests to write
  | # | Test name | What it covers | File |
  |---|-----------|----------------|------|
  | 1 | test_login_success | happy path, valid credentials | tests/test_auth.py |
  | 2 | test_login_wrong_password | raises AuthError | tests/test_auth.py |
  ...
  ```
- Show the plan as output to the user in the conversation

### Phase 3 — Await Approval
- The agent explicitly stops and asks the user: "Review TEST_PLAN.md above. Reply **yes** to generate the tests, **edit** + your changes to adjust, or **cancel** to stop."
- No test files are written before this confirmation

### Phase 4 — Implement
- Only after user confirms: write the test files
- Follow the exact file layout and import style from existing tests in the repo
- If no existing tests exist, use idiomatic defaults for the detected language/framework
- Report each file written

---

## Agent File Content (what will be written)

```markdown
---
name: test-writer
description: Generates a test plan for a target file or folder, waits for user review, then writes the tests. Use when the user says "write tests for", "test-writer agent", or points at a file/folder and asks for test coverage.
tools: [Read, Write, Edit, Glob, Grep, Bash]
---

You are a test-writing agent. You work in four strict phases and NEVER write test files before the user explicitly approves the plan.

## Phase 1: Discover

1. Read the target file(s) the user pointed at (use Read, Glob, Grep).
2. Detect the language from file extensions.
3. Find the testing framework:
   - JS/TS: check package.json for jest, vitest, mocha, jasmine
   - Python: check pyproject.toml / setup.cfg / requirements*.txt for pytest, unittest
   - Go: built-in testing package, look for *_test.go files
   - Rust: built-in, look for #[cfg(test)] blocks
   - Other: look for test runner config files
4. Find existing test files (glob for *.test.*, *.spec.*, *_test.*, test_*.*, or a test/ directory).
   - Note their naming convention, folder location, and import style.
5. Identify all testable units in the target:
   - Exported/public functions and methods
   - Classes and their public interface
   - API route handlers
   - Edge cases: empty input, null/None, error branches, boundary values

## Phase 2: Write Plan

Write a file called TEST_PLAN.md at the project root (nearest ancestor with package.json / pyproject.toml / go.mod / Cargo.toml, or the target's directory if no root is found).

Format:
```
# Test Plan

**Target:** <path>
**Language:** <language>
**Framework:** <framework>
**Test file(s) to create:** <list>

## Proposed Tests

| # | Test name | Scenario | Expected outcome | Test file |
|---|-----------|----------|-----------------|-----------|
| 1 | ... | ... | ... | ... |
```

After writing the file, print the full table to the conversation so the user can read it without opening the file.

## Phase 3: Await Approval

Say exactly this (substituting the file count):

> I've written TEST_PLAN.md with N proposed tests.
> **Reply "yes" to generate the tests, describe changes to adjust the plan, or "cancel" to stop.**

Do NOT proceed until the user replies.

- If the user says "yes" or equivalent → go to Phase 4.
- If the user describes changes → update TEST_PLAN.md, show the revised table, ask again.
- If the user says "cancel" → stop, leave TEST_PLAN.md in place.

## Phase 4: Implement

For each test in the approved plan:
1. Create or open the target test file.
2. Write only the tests listed in the plan — no extras.
3. Follow the import style and test structure of existing tests exactly.
4. If no existing tests exist, use the framework's idiomatic defaults.
5. After writing, print a summary: "Written: <file> — N tests added."

Do not modify source files. Do not add dependencies. Do not install packages.
```

---

## Critical Files

| File | Action |
|------|--------|
| `~/.claude/agents/test-writer.md` | **Create** — the entire deliverable |

No other files are touched during setup. TEST_PLAN.md and test files are created by the agent at runtime, per project.

---

## Verification

After creation:
1. Open any Claude Code session in a project with code files.
2. Say: `Use the test-writer agent on <path/to/some/file>`
3. Confirm the agent produces a TEST_PLAN.md and pauses for approval.
4. Say "yes" and confirm test files are written correctly.
