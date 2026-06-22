# ask-matt review — Self-Improvement Loop

> Review of `PROTOCOL.md` + `DESIGN.md`. Source files were **not** modified; all proposed
> edits below are quoted before/after snippets only.

---

## 1. Which skill ask-matt selected, and why

**Selected: `/grill-me`** (the `grilling` skill, Standalone branch of ask-matt).

Reasoning, walking the router (`.claude/skills/ask-matt/SKILL.md`):

- The main-flow entry point is `/grill-with-docs`, but ask-matt qualifies it explicitly:
  *"Start here when you **have a codebase**: it's stateful, retaining what it learns in
  `CONTEXT.md` and ADRs."*
- This task has **no codebase**. `DESIGN.md §2/§3` describes the CLI as something
  *"we scaffold in pass 2"* — the `core/`, `cli/`, `adapters/` tree does not exist yet.
  There is nothing to retain `CONTEXT.md`/ADRs against.
- ask-matt's Standalone section resolves this exactly: *"`/grill-me` — the same relentless
  interview as `/grill-with-docs`, but for when you have **no codebase**. Stateless...
  Reach for it to sharpen any plan or design that doesn't live in a repo."*

So the correct router output is `/grill-me`. It is an **interview** flow. Because this review
runs autonomously and cannot interview the user, the rest of this document applies the grilling
lens by generating the sharp questions `/grill-me` would ask and proposing a reasoned,
doc-grounded answer/decision for each — which is the deliverable the interview would have
produced.

---

## 2. Prioritized improvements (weak now → proposed change)

Ordered by how badly each would bite during implementation.

### P0 — The classification rule double-counts and is order-sensitive
**Weak now:** `PROTOCOL §4` and `DESIGN §5` both classify *at log time using the
post-increment count*, then **recompute at wrap-up**. But `DESIGN §5` says classify is
"Called at **log time** with the post-increment count (so the 2nd identical log is already
`fixable`)." The 1st event of a pattern is logged `casual` with count 1; the 2nd is logged
`fixable` with count 2 — **but the 1st event's stored `classification` is never updated except
at wrap-up**, and only "for every event in the session." Cross-session is the gap: if sighting 1
was last week and sighting 2 is today, the *old* event keeps `classification: casual` forever in
`events.jsonl`, and the recap math only re-derives the current session's events. The pattern is
fixable but its founding event reads casual on audit.
**Proposed change:** State clearly that `classification` on an `Event` is a **historical
snapshot at log time** and is *never authoritative*; the authoritative status lives on the
**pattern** (`patterns.json.status`), which `loop rebuild` recomputes from the full log. Add this
to `DESIGN §5` and `§4.1` (annotate the `classification` field as "snapshot, non-authoritative").

### P0 — `pattern_key` collision / split risk has no enforcement, only etiquette
**Weak now:** `PROTOCOL §5` relies on the agent *remembering to run `loop list`* and picking a
good key. Nothing prevents (a) two near-synonym keys splitting a real recurrence
(`infra-leak-in-app` vs `infra-in-application-layer`), or (b) two genuinely different problems
colliding under one broad key, which then crosses the threshold falsely. This is the single
biggest correctness risk because the **entire value of the loop is the recurrence count**.
**Proposed change:** Add a cheap guardrail now, defer the expensive one. (1) Make `loop log`
**reject an unknown `pattern_key` unless `--new-pattern` is passed**, and on rejection print the
3 closest existing keys (simple normalized string distance — no embeddings needed). (2) Note in
`DESIGN §9` that pgvector is the *upgrade* to this, not the first line of defense. See snippet B.

### P1 — Open-issue dedup at wrap-up is underspecified (race + "open" definition)
**Weak now:** `PROTOCOL §7.3` / `DESIGN §6` say "skip if an open issue for that key already
exists." But: where is "an open issue for that key" looked up? `patterns.json.issue_url` (local,
can be stale) or a live GitHub query (network, source of truth)? If a teammate closed #42
manually, local state still says `issued` and the pattern silently never re-files. Also "open"
is undefined — does a `resolved`/closed-then-reopened issue count?
**Proposed change:** Specify the lookup order: wrap-up does a **live GitHub search by label
`self-improve` + the `pattern_key`** (embed the key in the issue body/marker), treats only
`state:open` as blocking, and reconciles `patterns.json` from that result. Local `issue_url` is a
cache, not the gate. Add a hidden HTML marker `<!-- pattern:infra-leak-in-app -->` to the issue
template (`DESIGN §6`) so the search is exact, not title-fuzzy.

### P1 — `status` lifecycle is declared but never transitioned
**Weak now:** `DESIGN §4.2` defines `status` values `casual | fixable | issued | resolved`, but
no command or rule ever moves a pattern to `issued` or `resolved`. `loop wrap-up` creates issues
but the spec doesn't say it writes `status: issued`. Nothing closes the loop to `resolved`.
**Proposed change:** Define the transitions explicitly: `wrap-up` sets `issued` + `issue_url`;
add a `loop resolve <pattern_key>` command (and/or have `wrap-up` flip to `resolved` when the
linked issue is closed during reconciliation). List this in `DESIGN §7`. Without it, "Recurrence
-over-time / did the fix stop the bleeding" (`DESIGN §9 Metrics`) is impossible.

### P1 — The CLI→FastAPI seam leaks I/O into "pure" core
**Weak now:** `DESIGN §2` claims `core` is "all logic as **pure functions** over plain data,"
but `DESIGN §3` puts `store.py` (reads/writes `events.jsonl`, `patterns.json`) *inside* `core/`.
File I/O is not pure. When FastAPI arrives (`§8`), concurrent writers to a single append-only
file and a derived JSON create a race the "same functions behind HTTP" story glosses over.
**Proposed change:** Split core into truly pure (`classify`, `build_recap`, `build_issue`,
`record_event` as a *transform* returning the new event + new rollup) and an **I/O port**
(`store.py`) that the adapter calls. Pure functions take `counts`/`events` as arguments and
return new data; the adapter is responsible for persistence and locking. Note the concurrency
constraint for the FastAPI phase (file lock or move to SQLite when multi-writer). See snippet C.

### P2 — `severity` is asserted by the agent with no rubric beyond three labels
**Weak now:** `PROTOCOL §4` gives one-line definitions for sev 1/2/3, but severity directly
triggers immediate `fixable` at 3 — a powerful lever set by a single subjective call. "safety
-relevant output" is the only concrete sev-3 anchor.
**Proposed change:** Add 1–2 concrete examples per level drawn from the existing ski-assistant
domain (the docs already use it), and state the tie-breaker rule: *when unsure between two
levels, pick the lower and rely on recurrence* — keeps sev-3's "act now" power rare and
trustworthy.

### P2 — No story for log corrections / wrong approvals
**Weak now:** `DESIGN §4.1` says append-only, "corrections are new events, never edits." Good for
audit, but there's no defined way to **retract** a mis-logged event (e.g. approved in haste, or a
wrong `pattern_key`). A bad event permanently inflates a count.
**Proposed change:** Add a `loop retract <event_id> --reason …` that appends a *tombstone* event
referencing the original; `loop rebuild` ignores tombstoned events when recomputing counts.
Preserves append-only while making counts correct. Add to `DESIGN §7` and the data model.

### P2 — `session_id` format is implied, not specified
**Weak now:** Examples mix `2026-06-20-ski` (`PROTOCOL §8`) with `sessions/2026-06-20.md`
(`DESIGN §3/§4.3`) — date-only filename vs date+slug id. Two sessions on one day collide on the
recap filename.
**Proposed change:** Define `session_id = <YYYY-MM-DD>[-<slug>]` and make the recap path
`sessions/<session_id>.md` (not date-only), so same-day sessions don't overwrite each other.
Reconcile `DESIGN §3` and `§4.3`.

### P3 — Testing strategy named but not scoped
**Weak now:** `DESIGN §3` lists `test_classify/test_store/test_recap` but `§7` gives no testing
intent. The highest-value tests (dedup/collision, cross-session promotion, wrap-up idempotency)
aren't called out, and there's no test for the GitHub adapter (the only network code).
**Proposed change:** Add a short "Testing" subsection: pure-core tests are table-driven over
`classify` (boundary: count 1→2, sev 2 vs 3); `store` round-trips append+rebuild; **wrap-up
idempotency** (running it twice creates no duplicate issues) with `adapters/github.py` mocked.
Call out that idempotency is the test that protects P1.

### P3 — Confirm the §10 open assumptions
See section 3 below — these are exactly what `/grill-me` would force to a decision.

---

## 3. The grilling questions /grill-me would ask — with proposed answers

Grounded in `DESIGN §10` and the gaps above. Each is a decision the interview would extract.

1. **Repo placement (§10.1).** Q: Does `claude-config/self-improve/` collide with the repo's
   existing layout (this review sits in an `AI Engeeniring/self-improve-loop/` tree, *not* in
   `claude-config`)? **Proposed answer:** The docs assume `gweedo/claude-config`, but the working
   copy lives elsewhere. Decide the canonical home **before** pass 2, because the issue template
   (`DESIGN §6`) hardcodes `self-improve/sessions/{date}.md` paths and the repo for issues
   (`§10.3`). Recommend: keep code + issues in `claude-config` (skills live there; `skill_edit`
   targets it anyway per `PROTOCOL §6`), and treat this design folder as the planning workspace.

2. **Stack (§10.2).** Q: `typer` + `pydantic`, confirmed? **Proposed answer:** Yes — `pydantic`
   models double as FastAPI request/response types (`§8`), so the CLI→service seam reuses them
   for free. No change.

3. **Issue target repo (§10.3).** Q: File issues on `claude-config` even when the *mistake*
   happened in a different project (e.g. the ski-assistant)? **Proposed answer:** Yes for
   `skill_edit`/`new_skill`/`instruction_update` (the fix lives in `claude-config`). But
   `fix:script` issues often belong in the **project where the code lives**. Add a
   `--issue-repo` override to `loop wrap-up` and a per-event `fix_type → repo` default, so script
   fixes land where the code is. (Currently `--repo` is single-valued — `PROTOCOL §8`.)

4. **Thresholds (§10.4).** Q: Is "2 occurrences" right, given cross-session counting? **Proposed
   answer:** Keep `>=2` and sev-ceiling `3` as the tunable constants, but **only after** the
   `pattern_key` collision guardrail (P0) exists — otherwise `>=2` fires on accidental key reuse.
   The threshold is only as trustworthy as the key.

5. **Unstated assumption — what counts as "the same session"?** Q: If work spans two calendar
   days or two machines, is it one session or two? **Proposed answer:** Session is a *unit of
   work the agent declares*, not a calendar day; hence the `-slug` in `session_id` (P2). Wrap-up
   is per-session-id.

6. **Unstated assumption — who runs wrap-up, and what if it never runs?** Q: Casual items only
   promote "in some future session" (`PROTOCOL §7`); if wrap-up is skipped, fixable items never
   become issues. **Proposed answer:** Add `loop list --status fixable --unissued` as a standing
   check, and recommend wrap-up as a session-close ritual in `PROTOCOL §7`. Optionally a
   `loop doctor` that flags fixable-but-unissued patterns across all history.

---

## 4. Concrete proposed edits (before/after — NOT applied)

### Snippet A — classification authority (`DESIGN.md §5`)
**Before:**
```
- Called again at **wrap-up** for every event in the session, because a pattern logged
  earlier as `casual` may have crossed the threshold later in the same session.
```
**After:**
```
- Called again at **wrap-up** for every event in the session, because a pattern logged
  earlier as `casual` may have crossed the threshold later.
- The `classification` stored on an Event is a **non-authoritative snapshot** taken at log
  time. The authoritative status is `patterns.json.status`, recomputed from the full log by
  `loop rebuild`. Never read an old event's `classification` to decide current state.
```

### Snippet B — pattern_key guardrail (`PROTOCOL.md §5`)
**Before:**
```
- Before inventing a key, check `loop list` for an existing one that fits. Reuse beats
  inventing — a near-duplicate key splits the count and hides a real pattern.
```
**After:**
```
- Before inventing a key, check `loop list` for an existing one that fits. Reuse beats
  inventing — a near-duplicate key splits the count and hides a real pattern.
- Enforced, not just advised: `loop log` **rejects an unknown `pattern_key`** and prints the
  3 closest existing keys (normalized string distance). Pass `--new-pattern` to confirm a
  genuinely new one. This is the first line of defense against count-splitting; pgvector
  similarity (DESIGN §9) is the later upgrade, not the starting point.
```

### Snippet C — pure core vs I/O port (`DESIGN.md §2`)
**Before:**
```
The **core** holds all logic as pure functions over plain data. The **CLI** is a thin
adapter today; a **FastAPI** service is the same functions behind HTTP later (§8). This
separation is the DDD-flavoured part: domain logic never depends on the delivery
mechanism.
```
**After:**
```
The **core** splits in two: **pure functions** (`classify`, `record_event` as a transform,
`build_recap`, `build_issue`) that take data in and return data out, and an **I/O port**
(`store.py`) that the adapter uses to persist. Pure functions never touch the filesystem or
network. The **CLI** is a thin adapter today; a **FastAPI** service is the same pure
functions behind HTTP later (§8). Persistence and write-serialization are the adapter's job
— see §8 for the multi-writer concurrency constraint (file lock, or SQLite, once HTTP is
multi-client).
```

### Snippet D — issue dedup marker (`DESIGN.md §6`)
**Before:**
```
**Title:** [{fix_label}] {title}

### Pattern
`{pattern_key}` — seen {count}× (severity {max_severity})
```
**After:**
```
<!-- self-improve:pattern={pattern_key} -->
**Title:** [{fix_label}] {title}

### Pattern
`{pattern_key}` — seen {count}× (severity {max_severity})
```
plus a note: *Wrap-up dedups by live GitHub search on label `self-improve` + this marker,
counting only `state:open` issues; `patterns.json.issue_url` is a cache, not the gate.*

### Snippet E — open assumptions resolved (`DESIGN.md §10`)
**Before:**
```
3. Issues filed on `gweedo/claude-config` itself (your earlier choice).
4. Threshold = 2 occurrences; severity ceiling = 3. Tunable.
```
**After:**
```
3. Issues filed on `gweedo/claude-config` by default; `fix:script` issues may target the
   project repo where the code lives via `--issue-repo` (see CLI §7).
4. Threshold = 2 occurrences; severity ceiling = 3. Tunable — but only meaningful once the
   `pattern_key` collision guardrail (PROTOCOL §5) is in place, since the count is only as
   trustworthy as the key.
5. `session_id = <YYYY-MM-DD>[-<slug>]`; recap path is `sessions/<session_id>.md` so same-day
   sessions don't collide.
```

---

## 5. Summary

ask-matt routes this to **`/grill-me`** (no codebase yet → Standalone interview, not the
stateful `/grill-with-docs`). Applying that lens, the plan's biggest implementation risks are:
(1) **classification authority is ambiguous** — `Event.classification` is treated as both a
snapshot and a source of truth; pin status to the pattern; (2) **`pattern_key` collision/split
has no enforcement** — the whole loop's value is the count, so add a reject-unknown-key
guardrail before relying on pgvector; (3) **wrap-up dedup is underspecified** — define live
GitHub lookup + a hidden pattern marker + only-open-counts; (4) **the "pure core" seam leaks
file I/O** — split pure functions from a `store` port and name the multi-writer concurrency
constraint for the FastAPI phase; plus the `status` lifecycle, log retraction, `session_id`
format, and a testing focus on wrap-up idempotency.
