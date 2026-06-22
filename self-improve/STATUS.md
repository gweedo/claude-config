# Self-Improvement Loop — STATUS

_Last updated: 2026-06-22_

A living snapshot of where the project stands, what's verified, what's left, and the
skill routing for the remaining work. Companion to `PROTOCOL.md` (rules), `DESIGN.md`
(architecture), and `IMPLEMENTATION_NOTES.md` (pass-2 deviations).

---

## 1. Where we are

| Phase | State | Evidence |
|---|---|---|
| **Pass 1 — design** | ✅ merged | PR #10. `PROTOCOL.md` + `DESIGN.md`, hardened via skill-driven review (`reviews/`). |
| **Pass 2 — implementation** | ✅ merged | PR #11. `siloop/` package, **27 tests green**, Python 3.8, zero third-party deps. |
| **Pass 2 — hardening gaps** | 🚧 in progress | See §3. The GitHub adapter contract test is the one open coverage gap. |
| **Phase 3 — FastAPI service** | ⏸ deferred | DESIGN §8. Only when agents need to call the loop over HTTP. |
| **Future options** | ⏸ deferred | DESIGN §9: pgvector dedup, auto-implement agent, metrics. |

## 2. What is verified (under test)

- **Classification** — `classify` boundary corners (count 1↔2 × severity 2↔3).
- **Status machine** — `next_status` incl. the forbidden moves (issued not demoted; regression re-opens).
- **fold()** — count/verdict, tombstone drop, tombstone-of-tombstone reinstate, override pin,
  issue_filed→issued, resolved, regression, and **idempotent + lossless** folding.
- **pattern_key matcher** — reject-unknown + 3-closest (token + edit distance).
- **issues** — marker, label mapping, secret-scrub refusal.
- **recap** — renders a fixed `SessionView`, re-derives nothing.
- **Use cases** — `record_event` verdict/status, **wrap-up idempotency** (no duplicate on rerun),
  **GitHub-down safety** (no create on a failed search), **lossless rebuild through the store**
  (nuke `patterns.json`, reconstruct from `events.jsonl` incl. `issued`/`issue_url`).
- **CLI** — smoke-tested end to end (log → recurrence → reject-unknown → list → wrap-up --dry-run).

## 3. Open gaps (prioritized)

1. **[P0] GitHub adapter contract test — DESIGN §11 T8.** `adapters/github.py` is the only
   module with no test, and it's the network seam the dedup/idempotency guarantee rests on at
   runtime. Needs stubbed-HTTP coverage: search query builds the right `label + marker +
   state:open`; create returns the issue URL; a failed search **raises** (never returns empty).
   _Blocks pointing the tool at a real repo._
2. **[P1] Live setup.** Ensure the `self-improve` + `fix:*` labels exist on `gweedo/claude-config`;
   set `GITHUB_TOKEN`. One-time, required before the first real wrap-up.
3. **[P1] First real run.** Drive the loop from an actual working session (PROTOCOL §1): log a
   real event when something goes wrong, wrap-up at session end. The only validation against
   reality rather than tests.
4. **[P2] Map `state_reason` on close** (grill-me #9) — `completed` → resolved vs
   `not_planned` → re-surface. Conservative default today: only explicit `loop resolve` resolves.
5. **[P2] Two-repo dedup for `--issue-repo`** — confirm the live search targets the repo the issue
   is filed into, per pattern.

## 4. Skill routing for the remaining work (via ask-matt)

Confirmed by an actual `ask-matt` run (after enabling model-invocation of the skill):

- There **is a working codebase** and the gaps are **small, well-defined, single-session** — not
  idea-sharpening (skip `/grill-with-docs`), no runnable question to prototype, and not a
  multi-session build needing a PRD (skip `/to-prd` → `/to-issues`).
- Router outcome: the terminal **`/implement`** step ("build it here, in the same context window").
- `tdd` is **not** part of ask-matt's router map (it routes the main-flow skills only); TDD is just
  the *technique* applied inside `/implement` for the test-first T8 contract (red → green).
- Contrast: the design phase routed to `/grill-me` — different stage, different skill.

## 5. Recommended next action

Run **`/implement`** on gap §3.1 (the T8 contract test, TDD-style), then do the §3.2 label setup so
the loop can be driven for real. FastAPI / pgvector (§1) stay deferred until the loop has been
exercised manually a few times.
