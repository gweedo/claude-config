# self-improve — GLOSSARY

The domain's sharp-edged vocabulary, in one place. The whole design rests on a few
distinctions that are easy to blur (especially **verdict vs status**); this is the
authoritative reference for them. See `PROTOCOL.md` for the rules and `DESIGN.md` for the
data model.

---

## The core distinction: verdict vs status

These are deliberately two different words with two **disjoint** vocabularies so they can
never be confused.

| | **verdict** | **status** |
|---|---|---|
| Belongs to | a single **event** | a **pattern** |
| Values | `casual` \| `fixable` | `casual` \| `fixable` \| `issued` \| `resolved` |
| Computed by | `classify(severity, count)` at log time | `next_status(...)` inside `fold()`, over the whole log |
| Authority | a **non-authoritative snapshot**, frozen when logged | the **authoritative** lifecycle state |

**Rule of thumb:** to ask "is this being acted on right now?", read the pattern's
**status** — never an old event's verdict. The verdict is a historical footprint; the
status is the live truth, always recomputed.

---

## Terms

**Event** — One approved record of a single mistake, appended as one JSON line to
`events.jsonl`. Immutable: corrections are *new* events, never edits. Carries `type`,
`pattern_key`, `severity`, `verdict`, `fix_type`, `root_cause`, etc. (DESIGN §4.1).

**Signal** — A mistake worth flagging. There are exactly **four signal types**:
- `code_failure` — code didn't run / a test failed / wrong output.
- `misunderstood_intent` — the agent solved the wrong problem; you had to re-explain.
- `wrong_approach` — code worked but the design was wrong (e.g. leaked infra into the
  domain layer).
- `repeated_correction` — a small style/convention fix you keep making.

**Pattern** — A class of recurring mistake, identified by its `pattern_key`. The unit the
loop actually reasons about. Its rollup (count, max severity, status, issue link) lives in
`patterns.json`, keyed by `pattern_key`.

**`pattern_key`** — A short, stable, kebab-case name for the *pattern* (not the instance):
`infra-leak-in-app`, `missing-type-hints`. It's how recurrence is counted, so reuse beats
inventing — a near-duplicate key splits the count and hides a real pattern. `loop log`
**rejects an unknown key** (showing the 3 closest) unless `--new-pattern` is passed
(PROTOCOL §5).

**severity** — A 1–3 judgment set at log time: `1` cosmetic, `2` real but contained, `3`
serious (security / data loss / safety). Severity-3 is `fixable` immediately, even as a
one-off. Tie-breaker: pick the **lower** and let recurrence promote it.

**recurrence_count** — How many times a `pattern_key` has been logged across all sessions
(tombstoned events excluded). The second sighting promotes a `casual` pattern to `fixable`.

**casual / fixable / issued / resolved** — The pattern **status** lifecycle:
`casual` (tracked, accruing a count) → `fixable` (crossed the threshold) → `issued` (a
GitHub issue exists) → `resolved` (fix landed). A signal event on a `resolved` pattern is a
**regression** and re-opens it to `fixable` (DESIGN §7).

**`fix_type`** — The proposed remedy on each event, mapped to a GitHub label:

| `fix_type` | Label | Meaning |
|---|---|---|
| `script` | `fix:script` | Automatable — a script/test/CI rule resolves it. |
| `skill_edit` | `fix:skill` | An existing skill needs editing. |
| `new_skill` | `fix:new-skill` | A capability gap — scaffold a new skill. |
| `instruction_update` | `fix:instructions` | Update CLAUDE.md / project rules / a skill description. |

**`fold(events)`** — The single pure function that materializes `patterns.json` from the
log: `fold(events) -> {pattern_key: Pattern}`. The **only** producer of derived state, so
`patterns.json` can never desync — it's a provable cache, not a second source of truth.

**`rebuild`** — `write_snapshot(fold(read()))`. Regenerates `patterns.json` from
`events.jsonl` alone. Offline, idempotent, and **lossless** (reconstructs status and
issue links exactly).

**`classify` / `next_status`** — The two pure rule functions. `classify` returns an
event's verdict from severity + count; `next_status` is the transition table that knows the
forbidden moves (an `issued` pattern is never silently demoted and re-filed). Each has
exactly one home; renderers and adapters never re-implement them.

**Non-signal events** — Four event shapes the fold interprets besides signals, each
last-writer-wins per target (DESIGN §4.1):
- `override` — promotes a pattern to `fixable` (`loop promote`); survives rebuild.
- `tombstone` — retracts a mis-logged event (`loop retract`); excluded from counts. A
  tombstone of a tombstone reinstates.
- `issue_filed` — appended by wrap-up when it creates an issue; fold derives `issued` +
  `issue_url` from it.
- `resolved` — appended by `loop resolve`; fold derives `resolved`.

**Session / `session_id`** — A unit of work the agent declares, `<YYYY-MM-DD>[-<slug>]`
(e.g. `2026-06-20-ski`). Groups events for the recap.

**Recap** — The human-readable `sessions/<session_id>.md` written at wrap-up. A **pure
render** of a `SessionView`; it re-derives nothing (counts/statuses come pre-computed).

**Wrap-up** — End-of-session step: recompute statuses, write the recap, and file one
GitHub issue per fixable un-issued pattern. **Idempotent** — dedup is a live GitHub search
→ create → append `issue_filed`, per item under the store lock, so a rerun creates no
duplicate.

**Store / `EventLog`** — The persistence port: `read()` / `append()` / `write_snapshot()`,
pure I/O only. The JSONL append is the commit point; the snapshot is best-effort cache.

**Ports** — The seams that keep the core pure: `IssueGateway` (GitHub), `PatternMatcher`
(key similarity). Adapters implement them; pure functions never touch network or
filesystem. This is what lets the same use cases back the CLI today and a FastAPI service
later (DESIGN §8).

**dedup marker** — The hidden `<!-- self-improve:pattern={key} -->` comment in each issue
body. Wrap-up matches it by **exact string equality** (not GitHub fuzzy search) so a key
that's a substring of another can't false-merge (DESIGN §6).
