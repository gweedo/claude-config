---
name: ci-parity
description: |
  Bring a freshly scaffolded project to CI parity — make the local checks run exactly what CI
  runs, so the first PR isn't red. Use after scaffolding a project, when `make ci` or a CI
  pipeline fails on a repo that looks green locally, or before opening the first PR. Assumes a
  Next.js frontend with a FastAPI (Python) backend.
version: 1.0.0
allowed-tools: [Read, Glob, Bash, Edit, Write]
---

# CI Parity

A scaffold looks done before it is: the code runs locally but the first CI run comes back red,
because CI exercises checks the local setup never did. **CI parity** closes that gap — every
check in the pipeline has a local equivalent that passes first, so the failing step shows up on
your machine, not in the PR.

This skill is **stack-specific**: a Next.js frontend with a FastAPI (Python) backend. The
principle — mirror CI exactly — is portable; the mechanics below are not.

**Done only when `make ci` passes locally.** That is the completion criterion for the whole
skill: run it last (see Finish) and confirm green before opening the first PR.

## Parity items (satisfy every one)

1. **Frontend lockfile exists.** Run `npm install` in the frontend directory and commit
   `package-lock.json`. CI runs `npm ci`, which fails outright when the lockfile is missing.

2. **ESLint uses a flat config.** Add `eslint.config.mjs` extending `next/core-web-vitals` and
   `next/typescript`, and set the `lint` script in `package.json` to `eslint .` — never
   `next lint`, which is deprecated and prompts interactively, hanging CI.

3. **Every app entry point has a test.** At least one test file per app — a smoke test that
   renders the root page is enough. With no test file at all, Vitest exits 1 and coverage
   reports 0%, failing the gate.

4. **Non-testable scaffold files are excluded from coverage,** so the threshold measures real
   code rather than boilerplate:
   - Vitest (`vitest.config.ts`): exclude `**/*.config.*`, `app/layout.tsx`, `vitest.setup.ts`.
   - Python (`pyproject.toml`, under `[tool.coverage.run]` → `omit`):
     `app/infrastructure/database.py`, `app/settings.py`, `alembic/*`.

5. **A root `Makefile` mirrors the GitHub Actions steps exactly** — same commands, same order:
   - backend: `ruff check` → `mypy app` → `pytest --cov --cov-fail-under=80`
   - frontend: `eslint .` → `vitest run --coverage`
   - `make ci` runs both; `make install` installs dependencies and the pre-commit hooks.

6. **`.pre-commit-config.yaml` runs the same linters pre-commit** — the `ruff-pre-commit` hook
   for the backend, and a local hook running `eslint --fix` on staged frontend files. Wire its
   installation into `make install` so a fresh clone is covered.

## Finish

Run `make ci`. If it passes, the scaffold is at parity and the first PR will be green. If it
fails, the failing step **is** the parity gap — fix it here, not in CI, then rerun until green.
