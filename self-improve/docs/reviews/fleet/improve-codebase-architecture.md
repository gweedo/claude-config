# Deepening Review — Self-Improvement Loop (post-revision)

Lens: `improve-codebase-architecture` / `codebase-design` vocabulary (module, interface,
depth, seam, adapter, leverage, locality). The revision already landed the big moves: a
`core/loop` use-case layer, an `EventLog` store port, an injected `IssueGateway`, a
`casual → fixable → issued → resolved` status lifecycle, and `override`/`tombstone` events
that keep the JSONL append-only. Those are real deepenings and are not re-litigated here.

This review surfaces what stays **shallow or leaky once the design is built**. There is no
code yet, so each item is "this seam, as drawn, will concentrate maintenance pain." Prioritized
by leverage.

---

## 1. The derived-state invariant has two writers and no single fold — `patterns.json` (STRONG, highest leverage)

**The smell.** `patterns.json` is declared "derived from `events.jsonl`, always rebuildable"
(§4.2), yet the design has it mutated down **two independent paths**:

- `loop log` *bumps the count* and writes a classification incrementally (PROTOCOL §3 step 4,
  §4.2 `count`).
- `loop rebuild` *recomputes the whole rollup from scratch*, folding in `override`/`tombstone`
  (§4.1, §7).

Two code paths that must produce the same rollup is the textbook drift hazard: the incremental
bump and the from-scratch fold will diverge the moment a tombstone, an override, or a
status-lifecycle rule (`issued`/`resolved` "carried forward, not re-derived", §7) is involved.
The incremental path *cannot even see* a tombstone that arrives later, so the only correct value
is the rebuilt one — which means the incremental path is a shallow optimization sitting on top of
the real algorithm, duplicating it badly.

**The deeper shape.** Delete the incremental writer. Make **`rebuild()` the only producer of
`patterns.json`**, and have `loop log` call it (a full rebuild on a JSONL of this size is
microseconds — this is a knowledge log, not a hot path). The rollup becomes a **pure fold**
`fold(events) -> dict[pattern_key, Pattern]` living in `core/` (next to `classify`), with
`EventLog` only responsible for *reading the lines* and *atomically writing the snapshot*. Then
`patterns.json` is provably a cache: `fold(read())` is the definition, and the file is just a
materialized view.

**Why higher leverage.** This is the invariant the entire tool rests on — "the count is the
whole point of the loop" (PROTOCOL §5). Right now the invariant is enforced by *prose* ("can
always be rebuilt"), not by structure; a single code path makes it true by construction. It
passes the deletion test loudly: deleting the incremental bump concentrates all rollup logic in
one pure fold instead of smearing it across `log`, `rebuild`, `promote`, and `retract`. Every
future feature (pgvector merge, metrics, status reconciliation) then has exactly one place to
hook.

---

## 2. `EventLog.append()/rebuild()` is a shallow seam — the fold leaks across it (STRONG)

**The smell.** The store port advertises `append()` and `rebuild()` as "the only public
writers" (§2, §3). But `rebuild()` is doing two unrelated jobs welded together: (a) **I/O** —
read all JSONL lines, write `patterns.json` atomically; and (b) **domain folding** — interpret
`override`/`tombstone`, apply the status carry-forward rule, recompute counts. Job (b) is pure
domain logic that has no business behind a *storage* port. As drawn, `rebuild()` is a thin name
over a thick mix, and an Explore agent reading `store.py` will find classification/status rules
where it expected file handling — the worst kind of non-locality.

**The deeper shape.** Split the seam by *kind of complexity*, not by file:
- `EventLog` (store port): `append(event)`, `read() -> list[Event]`, `write_snapshot(rollup)`.
  Pure I/O + serialization + write-serialization (the lock from §8). No domain knowledge.
- `fold(events) -> Rollup` (pure, in `core/`): all the override/tombstone/status logic.
- `core/loop.rebuild()` = `store.write_snapshot(fold(store.read()))`. The orchestration is one
  line; the rule is testable without touching the filesystem.

**Why higher leverage.** This is what makes the store a **deep** module: a two-line interface
(`read`/`append`/`write_snapshot`) hiding nontrivial concerns (atomicity, the §8 file lock,
later SQLite), while the genuinely tricky part — folding corrections — sits in pure code with
full locality and trivial tests. It also unblocks item #1: once the fold is the only producer,
the store no longer needs a `rebuild` that knows domain rules at all. Pairs with #1; do them
together.

---

## 3. The status lifecycle is a state machine with no module — its invariant lives in comments (STRONG)

**The smell.** `casual → fixable → issued → resolved` with the load-bearing rule that
"`issued`/`resolved` are carried forward from issue state, not re-derived" (§7, §5, §4.1). This
is a real state machine with **forbidden transitions** (you must not let a `rebuild` knock an
`issued` pattern back to `fixable`, or it re-files a duplicate issue). Today that rule is enforced
by a *sentence in §7* and the discipline of whoever writes `rebuild`. The transition logic is
implicitly scattered across `log` (sets casual/fixable), `wrap_up` (→ issued), `resolve`
(→ resolved), `rebuild` (must preserve issued/resolved), and wrap-up reconciliation (→ resolved
when issue found closed). Five call sites, one unwritten contract.

**The deeper shape.** Give the lifecycle a home: a tiny pure function
`next_status(current, derived_class, issue_state) -> Status` that *is* the transition table —
the only place that knows "issued beats a recomputed fixable" and "a closed issue → resolved."
`fold()` (#1/#2) calls it per pattern; `wrap_up` and `resolve` route through it too. The
forbidden-transition rule stops being prose and becomes a row in a table that a test pins down
exhaustively.

**Why higher leverage.** Idempotent wrap-up (PROTOCOL §7) and no-duplicate-issues are *the*
correctness guarantees of the loop, and both depend entirely on this transition being right under
rebuild. A future agent operating this codebase needs to answer "can a rebuild ever re-file a
closed issue?" by reading one function, not by tracing five commands and trusting a comment.

---

## 4. The `pattern_key` matcher is the load-bearing deep module — but it's hidden inside the CLI (STRONG / worth exploring)

**The smell.** Recurrence counting depends entirely on `pattern_key` *not splitting*. The guard
— "reject unknown key, show 3 closest by normalized string distance, `--new-pattern` to confirm"
(PROTOCOL §5, §7) — is described as a `loop log` (CLI adapter) behavior. The CLI is exactly where
it should *not* live: it's pure domain policy ("are these the same pattern?"), it's the seam
where pgvector later substitutes in (§9), and §10 ¶4 explicitly says the tunable threshold "is
only meaningful once the collision guardrail is in place." That's a core invariant wearing an
adapter's clothes.

**The deeper shape.** A `PatternMatcher` port in `core/ports.py` with one method:
`nearest(key, known_keys) -> list[Candidate]`. The default adapter is string-distance; pgvector
is the second adapter — and per the design vocabulary, *two adapters make the seam real*, not
hypothetical. `record_event` in `core/loop` consults the matcher and either accepts, or returns a
"did you mean…" rejection that the CLI *renders*. The decision lives in core; the CLI only formats
the three candidates.

**Why higher leverage.** This is the single most leveraged seam for the tool's whole premise
(trustworthy counts). Putting it behind a port now means the pgvector upgrade (§9) is a drop-in
adapter swap with zero core change — the design *says* pgvector is "the later upgrade," so draw
the seam where the upgrade plugs in. Built into the CLI instead, the FastAPI adapter (§8) would
have to *re-implement* the guard, and the two would drift.

---

## 5. `IssueGateway` straddles dedup-search and reconciliation — risk of a fat, awkward port (WORTH EXPLORING)

**The smell.** The gateway must support: create an issue, **live-search** open issues by label +
hidden `pattern=` marker (for dedup, §6/§7), and **reconcile** issue open/closed state to flip
`status` (§7 `resolve`/wrap-up). If the port grows method-by-method to match GitHub's surface
(`search`, `create`, `get_state`, …), it becomes a shallow pass-through — its interface as
complex as the GitHub REST shape it wraps, which fails the depth test.

**The deeper shape.** Keep the port phrased in the loop's own language, not GitHub's:
`open_issue_for(pattern_key) -> IssueRef | None` (the dedup question, hiding the label+marker
query), `file_issue(payload) -> IssueRef`, `issue_state(ref) -> open|closed`. The marker
convention and search syntax stay *inside* `adapters/github.py`. `core/loop.wrap_up` asks the
loop-language question; only the adapter knows it's a `state:open label:self-improve` query.

**Why higher leverage.** Lower than #1–#4 because it touches one workflow, but it's the seam the
FastAPI growth path crosses unchanged, and it's where a future "auto-implement agent" (§9) or a
GitLab/Linear backend would attach. A loop-language port means swapping issue backends never
touches core. Medium leverage, cheap to get right at design time.

---

## 6. Two "is there an open issue?" deduplications that must agree but are described separately (WORTH EXPLORING)

**The smell.** Idempotency is guaranteed twice: wrap-up's per-pattern live-search dedup (§7
step 3 / §6), and the standing catch `loop list --status fixable --unissued` (PROTOCOL §7).
These answer the same question — "does this fixable pattern still need an issue?" — but are
written as separate features. If `--unissued` trusts the cached `issue_url` while wrap-up trusts
the live search, a manually-closed issue makes them disagree, and the two surfaces give the user
contradictory worklists.

**The deeper shape.** One predicate in core: `needs_issue(pattern, gateway) -> bool`, defined as
"fixable AND no open issue per the gateway." Both `wrap_up` and `list --unissued` call it. The
"never trust the cache as the gate" rule (§6) then has a single enforcement point instead of two
prose reminders.

**Why higher leverage.** Modest, but it removes a latent contradiction between two user-facing
commands and collapses the dedup rule to one home. Naturally falls out of #5 (`open_issue_for`).

---

## 7. The multi-writer concurrency constraint is deferred to "the store's responsibility" — but the boundary isn't drawn yet (SPECULATIVE / note for Phase 5)

**The smell.** §8 correctly says HTTP makes append+rollup concurrent and pushes serialization
into the store ("file lock, or SQLite"). That's the right home. The latent issue: with the
*incremental* `patterns.json` bump (item #1), the critical section is "append line **and**
read-modify-write the rollup" — a wide, error-prone lock. The constraint is real but its size is
set by a decision item #1 can shrink.

**The deeper shape.** Adopting #1 (rebuild-only producer) makes the locked region just
`append(event)` — a single append to JSONL, the one operation that's already close to atomic.
The snapshot becomes a recompute-after, not a mutate-under-lock. So the concurrency story gets
*easier* for free once the derived-state writer is singular. No action now beyond noting that #1
de-risks §8; if `patterns.json` stays incrementally mutated, the Phase-5 lock must wrap both
files together.

**Why lower leverage.** It's a Phase-5 concern and entirely downstream of #1. Listed so the
connection isn't lost: **fix #1 and the FastAPI concurrency constraint largely dissolves.**

---

## Top recommendation

Tackle **#1 + #2 together** (collapse to a single pure `fold`, make `EventLog` pure I/O), then
**#3** (lift the status machine into one `next_status` function the fold calls). These three are
the same underlying deepening seen from three angles: *all derived state must flow through one
pure function over the append-only log.* That single move makes `patterns.json` a provable cache,
gives the store real depth, turns the status invariant from a comment into a tested table, and —
per #7 — shrinks the future FastAPI concurrency problem to a single-line append lock.

**#4** (the `PatternMatcher` port) is the highest-leverage *new seam*: it protects the count the
whole tool depends on and is exactly where pgvector plugs in later. Do it before the CLI hardens
the guard in place.

For a future agent operating this codebase, the win is locality: "how is a pattern classified,
counted, corrected, and issued?" should be answerable by reading `core/` pure functions — not by
tracing `log`, `rebuild`, `wrap_up`, `resolve`, and a GitHub adapter and trusting four prose
invariants to stay in sync.
