# Runbook — running the retrospective-improvement issues

These six issues came out of the three retrospectives. **Each one is deliberately *not*
fully-specified**: it opens with a "Decision to study together" section, so the first job in
every session is to pair with the maintainer and *decide*, not to start coding. Run each in its
own fresh session.

> **Two issues live in a different repo.** The `verify-outcome` and footgun-surfacing issues are
> config/tooling work, so they were moved to **`gweedo/claude-config`** (#31, #32). The other
> four stay in **`gweedo/allarounder`**. Open each session in the repo named in its row.

## Recommended order

| Order | Repo | Issue | Title | Blocked by |
|---|---|---|---|---|
| 1 | allarounder | #77 | ADR "Est. monthly cost" line + MVP-sizing axis | — |
| 2 | claude-config | #31 | `verify-outcome` — gate "done" on an observed postcondition | — |
| 3 | allarounder | #80 | Build-artifact parity check | — |
| 4 | claude-config | #32 | Surface footguns at write-time (self-improve) | — |
| 5 | allarounder | #79 | Real-infra critical-path tests | **claude-config#31** |
| 6 | allarounder | #82 | Environment-parity deploy playbook | **claude-config#31** |

#77, claude-config#31, #80, claude-config#32 are independent and can run in any order (or in
parallel sessions). **Do claude-config#31 before #79 and #82** — both reuse its "assert the real
outcome" vocabulary, and both carry a merge-check step that needs #31 to exist first.

## How every session should go

1. **Read first** — the issue body, and the retrospective it cites (paths below).
2. **Study together (do this before any edit).** Walk the "Decision to study together" section
   with the maintainer. Use the `grilling` and/or `domain-modeling` (decision-mapping) skills to
   stress-test options. Do not start implementing until the decision is made.
3. **Record the decision** — an ADR (`domain-modeling` skill) or a short note in the issue —
   *before* writing code. This is the first acceptance criterion on every issue.
4. **Implement** the agreed approach.
5. **Verify** the acceptance criteria (use the `verify` skill where it applies) and update the
   issue checkboxes.

> Retrospectives:
> - `retrospective-infra-cost-overprovisioning-2026-06-25.md`
> - `retrospective-infra-cost-review-2026-06-29.md`
> - `retrospective-skills-orchestrator-2026-06-25.md`

---

## Paste-ready kickoff prompts

Open a new session **in the repo named in each heading** and paste the matching block.

### #77 — ADR cost line + MVP-sizing axis
```
Work on issue #77 in gweedo/allarounder. Read the issue, then read
retrospective-infra-cost-overprovisioning-2026-06-25.md and
retrospective-infra-cost-review-2026-06-29.md.
Do NOT start editing yet. First walk the "Decision to study together" section with me —
grill the options for where the cost line lives, granularity, MVP-sizing gate strength, and
backfill scope. Record the decision (ADR or issue note) before implementing. Then implement,
verify the acceptance criteria, and tick the boxes.
```

### claude-config#31 — verify-outcome gate  (repo: gweedo/claude-config)
```
Work on issue #31 in gweedo/claude-config. Read the issue, then read the
retrospective-skills-orchestrator-2026-06-25.md retro from the allarounder project
(Theme A and section 7).
Do NOT start editing yet. First study the "Decision to study together" section with me:
skill vs hook/gate vs both, which step-types to cover at v1, and how it relates to the existing
verify / qa / diagnosing-bugs skills (extend vs new). Record the decision before implementing.
Then implement, verify, and tick the boxes.
```

### #80 — build-artifact parity check
```
Work on issue #80 in gweedo/allarounder. Read the issue, then read
retrospective-skills-orchestrator-2026-06-25.md (Theme D).
Do NOT start editing yet. First decide with me: allowlist-lint vs image-content assert vs both,
pre-commit vs CI, fail-hard vs warn, and what seeds the required-paths list. Record the decision
before implementing. Then implement, verify, and tick the boxes.
```

### claude-config#32 — surface footguns at write-time  (repo: gweedo/claude-config)
```
Work on issue #32 in gweedo/claude-config. Read the issue, then read the
retrospective-skills-orchestrator-2026-06-25.md retro from the allarounder project
(Theme E and the institutional-memory section).
This likely touches the self-improve project at ~/.claude/self-improve/.
Do NOT start editing yet. First decide with me: trigger mechanism (PreToolUse hook vs orchestrator
injection vs self-improve emitting entries), how footguns are tagged to code areas, and how this
composes with existing memory recall. Record the decision before implementing. Then implement,
verify, and tick the boxes.
```

### #79 — real-infra critical-path tests  (repo: gweedo/allarounder; do claude-config#31 first)
```
Work on issue #79 in gweedo/allarounder. Read the issue and its blocker gweedo/claude-config#31,
then read retrospective-skills-orchestrator-2026-06-25.md (Themes B/C and the admin-login marathon).
Do NOT start editing yet. First do the "Decision to study together" section with me, INCLUDING
the merge check: decide whether this stays independent or folds into claude-config#31. Then decide
testcontainers vs CI service container, scaffold-default vs opt-in skill, and login-smoke depth.
Record the decision before implementing. Then implement, verify, and tick the boxes.
```

### #82 — environment-parity deploy playbook  (repo: gweedo/allarounder; do claude-config#31 first)
```
Work on issue #82 in gweedo/allarounder. Read the issue and its blocker gweedo/claude-config#31,
then read retrospective-skills-orchestrator-2026-06-25.md (Theme G) and
retrospective-infra-cost-review-2026-06-29.md.
Do NOT start editing yet. First do the "Decision to study together" section with me, INCLUDING
the merge check (stay independent vs fold into claude-config#31). Then decide: is "staging mirrors prod" ever
a default, what the per-env gate checklist contains, and doc vs skill vs handoff-extension.
Record the decision before implementing. Then implement, verify, and tick the boxes.
```
