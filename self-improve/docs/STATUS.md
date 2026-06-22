# Self-Improvement Loop — STATUS

_Last updated: 2026-06-22_

A living snapshot of where the project stands, what's verified, what's left, and the
skill routing for the remaining work. Companion to `../README.md` (start here),
`PROTOCOL.md` (rules), `DESIGN.md` (architecture), `GLOSSARY.md` (vocabulary), and
`IMPLEMENTATION_NOTES.md` (pass-2 deviations).

---

## 1. Where we are

| Phase | State | Evidence |
|---|---|---|
| **Pass 1 — design** | ✅ merged | PR #10. `PROTOCOL.md` + `DESIGN.md`, hardened via skill-driven review (`reviews/`). |
| **Pass 2 — implementation** | ✅ merged | PR #11. `siloop/` package, Python 3.8, zero third-party deps. |
| **Pass 2 — hardening gaps** | 🚧 mostly closed | T8 contract test done (PR #13, **33 tests green**); labels created. See §3. |
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
- **GitHub adapter (T8)** — stubbed-HTTP contract: dedup query (`label:self-improve` + `state:open`
  + exact marker), marker match → ref / non-match → None, **failed search raises** (never silent
  empty), create/comment/ensure-labels endpoints, 422-on-existing-label non-fatal.
- **CLI** — smoke-tested end to end (log → recurrence → reject-unknown → list → wrap-up --dry-run).

## 3. Open gaps (prioritized)

1. ✅ **[done] GitHub adapter contract test — DESIGN §11 T8.** PR #13. The last untested module is
   now covered; full suite **33 green**, offline.
2. **[P1, partly done] Live setup.** ✅ `self-improve` + four `fix:*` labels created on
   `gweedo/claude-config`. Remaining: export the token at run time — `export
   GITHUB_TOKEN=$(gh auth token)` (the gateway reads `GITHUB_TOKEN`).
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

T8 (§3.1) and the labels (§3.2) are done. The next step is the **first real run** (§3.3): export
`GITHUB_TOKEN=$(gh auth token)` and drive the loop from an actual session — log a real event, then
`loop wrap-up`. FastAPI / pgvector (§1) and the P2 items stay deferred until the loop has been
exercised against reality a few times.
