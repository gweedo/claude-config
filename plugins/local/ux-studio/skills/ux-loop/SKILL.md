---
name: ux-loop
description: Runs the UX loop, which builds UI with the ux-ui-designer agent, reviews it with the separate ux-reviewer agent, and has the Designer fix the Findings, capped at two Review passes. Leftovers are filed to the project's issue tracker after asking. Use when the user wants UI built and reviewed, or runs /ux-loop.
argument-hint: "<what to build or change> [routes]"
---

Run the **UX loop** (ux-studio `CONTEXT.md`) in this main session. You are the conductor: the two agents never see each other's context, so everything one needs from the other passes through you. Call them by name with the Agent tool: `ux-ui-designer` and `ux-reviewer` (they may be namespaced `ux-studio:ux-ui-designer` / `ux-studio:ux-reviewer`).

Run every agent call in the **foreground** (`run_in_background: false`) and wait for its result: each step consumes the previous step's output, and ending your turn while an agent runs ends the loop. If an agent is moved to the background anyway, wait for its completion notification before the next step; a started agent is not a finished one.

## 1. Brief

Turn the user's request into a brief: what to build or change, target routes/files, refinement vs redesign, and any look they named. If the target project or the routes are ambiguous, ask once before starting.

## 2. Build

Spawn `ux-ui-designer` with the brief. Keep its hand-back: changed routes, the run command and URL, and the Smoke check result. If the Smoke check failed, send it back once to fix before any review.

## 3. Review pass (at most 2)

Spawn `ux-reviewer` with **only**: the original brief, the routes, the run command/URL, and where the Project DESIGN.md lives. Give it none of the Designer's reasoning or hand-back narrative; that independence is the point (ADR-0003).

- `verdict: pass` with no blocking Findings: go to step 5.
- Otherwise, spawn `ux-ui-designer` with the Findings as its brief (all blocking ones, plus the minor ones worth doing), then run the next Review pass.

**Stop after the second Review pass** whatever its verdict (ADR-0004). The Findings still open after it are **Leftovers**.

## 4. Leftovers

Skip this step when there are none.

1. Show the user the Leftovers, blocking first.
2. Look for `docs/agents/issue-tracker.md` in the target project.
   - **Present**: ask the user whether to file them. On yes, file them following that doc's conventions, and the label for "needs triage" from `docs/agents/triage-labels.md`:
     - one issue per **blocking** Leftover
     - one grouped issue for all **minor** Leftovers
     - each issue gives the route and width, the source (Impeccable audit, Impeccable critique, Taste gate, Playwright), the evidence, and the fix direction
   - **Absent**: report them in chat only. Do not guess at a tracker.

## 5. Report

Tell the user, in a few lines: what was built (routes, how to run it), how many Review passes ran and their verdicts, Findings fixed, and the Leftovers with their issue links if filed.
