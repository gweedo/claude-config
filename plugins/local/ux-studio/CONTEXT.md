# UX Studio

A local plugin that bundles a UX/UI builder agent and a UX review agent with the
third-party design skills they share (Impeccable, Taste, Playwright CLI, and an
index over awesome-design-md). Exists so frontend work gets built to a high design
bar and judged by an agent that didn't build it.

## Language

### Agents

**Designer**:
The agent that builds or changes UI (`ux-ui-designer`). Runs Impeccable's
shape → build → polish workflow and ends its own loop with a Smoke check, not a
taste judgement.
_Avoid_: Builder, frontend agent

**Reviewer**:
The agent that judges UI it did not build (`ux-reviewer`). Sees only the running
page and the brief, never the Designer's reasoning. Read-only by instruction.
Within this context only; distinct from agent-orchestra, which has no Reviewer role.
_Avoid_: Critic, QA

**Review pass**:
One run of the Reviewer against a running page: Playwright snapshots/screenshots,
Impeccable `audit` + `critique`, and the Taste gate where it applies. Produces a
findings list handed back to the Designer.
_Avoid_: QA pass, review loop

**Smoke check**:
The Designer's own closing check: the page renders, no console errors, key
breakpoints don't break. Deliberately excludes judging how good it looks.
_Avoid_: Self-review, verification

**UX loop**:
The build → Review pass → fix cycle, run by the `ux-loop` skill in the main session.
Capped at two Review passes. The only path besides an explicit user request that
invokes the Reviewer; the Reviewer is never auto-delegated.
_Avoid_: Review loop, iteration

**Finding**:
One issue a Review pass reports, ranked by severity (blocking or minor) and tagged
with its source (Impeccable audit, Impeccable critique, Taste gate, or Playwright). Returned to
the caller; the Reviewer never writes files.
_Avoid_: Bug, comment, issue

**Leftover**:
A Finding still open when the UX loop hits its cap. With the user's go-ahead, filed
to the project's issue tracker per its `docs/agents/issue-tracker.md` (one issue per
blocking Leftover, minor ones grouped, labelled for triage); reported in chat when
the project has no tracker set up.
_Avoid_: Backlog item, residual

### Skills

**Vendored skill**:
A third-party skill copied into `skills/` and pinned to an upstream commit SHA in
`vendor.lock` (the single source of truth; `VENDOR.md` is generated from it).
Changed only by `scripts/sync-vendor.sh`, never edited by hand.
_Avoid_: Installed skill, dependency

**On-demand folder**:
A subfolder of a Vendored skill (lock column `on_demand`) that sync never downloads
or touches. Fetched at the pinned SHA on first use by `scripts/fetch-on-demand.sh`
and git-ignored. Today: Taste's `assets/`.
_Avoid_: Excluded folder, assets cache

**Primary workflow**:
Impeccable. Governs app UI, dashboards, components and design systems end to end.
_Avoid_: Main skill

**Taste gate**:
Applying the Taste skill (`design-taste-frontend`) as an extra pass/fail bar on
marketing and company websites only. Never applied to app UI.
_Avoid_: Taste review, style check

**Reference design**:
One `DESIGN.md` from the awesome-design-md library, picked by site and fetched on
demand at the pinned SHA. Inspiration or a starting base, never shipped as-is.
_Avoid_: Template, theme

**Project DESIGN.md**:
The target project's own design-system document, which the Designer creates or
extends. The source of truth both agents read before working.
_Avoid_: Style guide, design doc
