# Codebase-Design Review — Self-Improvement Loop (deep-module lens)

Scope: verify the five applied changes are correct/complete through the deep-module
lens, run the deletion test on `core/loop` and `EventLog`, check the §2/§3 seam map vs
prose, and surface PROTOCOL↔DESIGN contradictions and remaining shallow modules /
leaked invariants.

---

## Verdict on each applied change

### 1. `core/loop.py` use-case layer (`record_event`, `wrap_up`) — SOLID

Deletion test: delete `core/loop`. The orchestration sequence
(store → classify → rollup → recap → dedup → issue) reappears, duplicated, in **both**
the CLI command and the FastAPI handler. Complexity does not vanish; it multiplies
across two adapters. The module earns its keep.

The §8 snippet confirms depth: each adapter crosses *one* seam and is a one-liner
(`return to_out(core.loop.record_event(store, to_draft(p)))`). Small interface, real
behaviour behind it. The dedup policy is explicitly homed in `wrap_up` (§6 note), not
leaked into `issues.py`. Good.

Minor: `wrap_up` interface is fully named in §2 (`wrap_up(store, issues_gw)`) but the
§8 handler calls `core.loop.wrap_up(store, GithubGateway(repo), sid)` — three args, with
`sid` last. The arg list/order is informal across sections. Not a depth problem, but the
interface (which the skill defines as "everything a caller must know") is stated two
different ways. Pin one signature.

### 2. `core/ports.py` + `IssueGateway`, implemented by `adapters/github.py`, injected into `wrap_up` — SOLID

This is the "accept dependencies, don't create them" rule applied correctly: `wrap_up`
receives the gateway rather than constructing a `GithubGateway`. The seam is real, not
hypothetical: there are two adapters in practice — the live GitHub impl and the in-memory
fake the tests must use to exercise dedup/idempotency without the network. The "one
adapter = hypothetical seam, two = real seam" test passes.

One gap: §3's `tests/` lists `test_classify.py`, `test_store.py`, `test_recap.py` but
**no `test_loop.py`**. `core/loop` is now the deepest, highest-leverage module and the
only home of the dedup + idempotency invariants (§7, §6), yet it has no listed test
crossing its seam with a fake `IssueGateway`. The skill's "interface is the test surface"
principle says this is exactly the seam tests should hit. Add `test_loop.py`.

### 3. `store.py` as `EventLog` with `append()`/`rebuild()` the only public writers — NEEDS-WORK

Deletion test on `EventLog` itself: passes. Delete it and the append-to-JSONL + rollup
maintenance + the write-serialization constraint (file lock / SQLite, §8) reappear in
every writer. It hides persistence and concurrency behind a 2-method writer surface.
Deep module, correctly placed.

But the "**only** public writers" claim is contradicted by the lifecycle prose (see the
Seam-map section below). The invariant as written is leaked/violated by `issued` and
`resolved` status writes. The module shape is right; the *stated invariant* is not yet
true. Fix the prose or the model.

### 4. `recap.py` demoted to pure renderer of a `SessionView`; rule only in `classify.py` — SOLID

§5 is now unambiguous: "Wrap-up produces an already-classified `SessionView`; `recap.py`
is a pure renderer of it and must not re-derive classes, counts, or thresholds." §3 echoes
it ("render a pre-classified `SessionView` -> markdown (pure, no rules)"). The
classification rule has exactly one home (`classify.py`), invoked by `core/loop.wrap_up`.
This removes the earlier duplicated-rule smell. `recap` is now a shallow-but-legitimate
leaf renderer (rendering genuinely is thin work — acceptable; not every module must be
deep, and a pure formatter has no hidden invariant to leak).

### 5. promote/retract as appended `override`/`tombstone` events folded by `rebuild` — SOLID (with one consistency nit)

§4.1 models both as appended event shapes with `target_event_id`; `rebuild()` folds them
(override pins status, tombstone excludes from counts). This preserves append-only and
keeps the single source of truth in `events.jsonl` — corrections are new events, never
in-place edits. This is the right shape: it keeps `append()`/`rebuild()` as the only
writers for *these* operations and routes them through the same seam. Consistent with §7's
command table.

---

## Seam map (§2 box) vs prose — INCONSISTENT (primary finding)

The §2 box asserts: `EventLog (store port): append() · rebuild() are the only public
writers`. §3 repeats it: "append()/rebuild() are the ONLY public writers".

The prose contradicts this for `status`:

- §7 wrap-up row: "Sets pattern `status: issued` + `issue_url`."
- §7 `loop resolve` row: "Move a pattern to `status: resolved`."
- §7 lifecycle: "`issued`/`resolved` are **carried forward from issue state, not
  re-derived**" by `rebuild`.

So `issued`/`resolved` are written into `patterns.json` by *neither* `append()` (no
`issued`/`resolved` event shape is defined — §4.1 defines only `override` and
`tombstone`) *nor* `rebuild()` (which by its own statement does not re-derive them).
That implies a **third, undocumented writer** mutating `patterns.json` directly,
which breaks the "only public writers" invariant the seam map advertises.

This is both a seam-map/prose inconsistency **and** a leaked invariant: the rule
"all writes go through `append()`/`rebuild()`" is stated but not actually upheld by the
model. Two clean resolutions, pick one:

  a. Model `issued`/`resolved` as appended event shapes (e.g. `issued`/`resolved`
     events carrying `pattern_key` + `issue_url`), folded by `rebuild()` like
     `override`/`tombstone`. Then `append()`/`rebuild()` really are the only writers and
     the "not re-derived" caveat disappears — rebuild reconstructs them from the log. This
     is the consistent extension of change #5 and keeps `events.jsonl` the sole source of
     truth (§4.2 still holds).

  b. Keep a direct `patterns.json` status writer but **document it as a third public
     writer** and correct the §2/§3 "only" claim (e.g. "`append()`/`rebuild()` are the
     only writers of *counts/derived rollup*; `set_status()` writes issue-lifecycle
     state"). Weaker — it reintroduces a non-log-derived field into the otherwise
     fully-derivable `patterns.json`, contradicting §4.2's "always be rebuilt from it".

Option (a) is the deeper, more locality-preserving fix and aligns with §4.2. Recommend (a).

---

## PROTOCOL ↔ DESIGN contradictions introduced by the edits

No new hard contradiction was introduced by the edits between the two documents on the
core mechanics — classification rule (PROTOCOL §4 vs DESIGN §5), pattern-key guard
(PROTOCOL §5 vs DESIGN §7/§10.4), live-search dedup + idempotency (PROTOCOL §7 vs DESIGN
§6), and promote/retract (PROTOCOL §8 vs DESIGN §4.1/§7) all line up.

Two soft mismatches worth tightening:

- **`loop resolve` arg shape.** PROTOCOL §8 shows `loop resolve infra-leak-in-app
  --reason …` (positional `pattern_key`); DESIGN §7 agrees (`loop resolve <pattern_key>`).
  Consistent — good. But the `resolved`-status write path is the very thing flagged above;
  whichever resolution you pick in the seam-map section must be reflected back into
  PROTOCOL §8's description so the two docs don't diverge on *how* resolve persists.

- **Where `record_event`/the use-case layer is surfaced to the agent.** PROTOCOL §3/§8
  speaks only of `loop log`; DESIGN §2/§8 introduces `core.loop.record_event`. That is
  correct layering (PROTOCOL is agent-facing, DESIGN is engineering), not a contradiction
  — noting it only so a later edit doesn't "helpfully" leak `record_event` into PROTOCOL.

---

## Remaining shallow modules / leaked invariants

- **`classify` constants are duplicated as prose across two files.** Threshold `>= 2`
  and severity ceiling `3` live in `classify.py` (DESIGN §5, "constants … easy to tune")
  but the same numbers are restated in PROTOCOL §4, DESIGN §4 examples, and §10.4. The
  *rule* now has one code home (good), but the *magic numbers* are echoed in three
  documents. Not a module-shape defect; flag it so a tuning change updates all prose, or
  the docs reference the constant rather than restate it.

- **`classification` snapshot on `Event` (§4.1/§5).** Correctly demoted to
  "non-authoritative snapshot" with an explicit "never read it to decide current state"
  warning. This is a deliberately fenced leaked field — acceptable as documented, but it
  remains a latent footgun (a future caller can still read it). Consider whether it needs
  to be persisted at all, since authoritative status is always `patterns.json.status`
  recomputed by rebuild. Dropping it would remove the invariant entirely rather than
  guarding it with a comment.

- **`issue_url` lives in two places** — on the `Event` (§4.1) and on the pattern rollup
  (§4.2), plus the live-search reconciliation (§6/§7) declares the pattern copy a "cache,
  never the gate." Three representations of one fact. The gating rule is clearly homed
  (live search in `wrap_up`), so this is contained, but it's the same cache-coherence
  hazard the snapshot warning addresses. Worth a one-line note that the event-level
  `issue_url` is also non-authoritative.

No genuinely shallow pass-through module remains. `recap`/`issues` are thin but are pure
leaf renderers with no hidden invariant — legitimately thin, not shallow-in-the-bad-sense.

---

## Summary

Four of five applied changes are solid; #3 (`EventLog` "only writers") is needs-work
because the `issued`/`resolved` status write path contradicts the very invariant the §2/§3
seam map advertises — the single most important issue to resolve, ideally by modelling
status transitions as appended events folded by `rebuild()` (option a). The use-case layer
and port injection are correctly deep and testable; add a missing `test_loop.py` so the
deepest module is exercised through its seam. No hard PROTOCOL↔DESIGN contradiction was
introduced; tighten the `wrap_up` signature statement and the duplicated threshold
constants.
