# Grill-Me Review — Self-Improvement Loop (UPDATED design)

> Adversarial stress-test of `PROTOCOL.md` + `DESIGN.md` after the additions of: a
> `core/loop` use-case layer, an `EventLog` store, an injected `IssueGateway` with
> live-GitHub-search dedup, a `casual→fixable→issued→resolved` status state machine,
> `override`/`tombstone` events, a reject-unknown-`pattern_key` guardrail, and
> `session_id` slugs.
>
> Method: grill-me — walk the design tree, hunt unstated assumptions, failure modes,
> and edge cases. Each item is a sharp question + a reasoned, decision-ready answer.
> Ordered by severity/blast-radius, not by document order.

---

## 1. What happens when GitHub is down (or rate-limited / token-expired) at wrap-up? [BLOCKER]

**Q.** Wrap-up's dedup now depends on a *live GitHub search* and then *creates* issues.
Both are network calls. If GitHub is unreachable, the search returns nothing —
does the loop then (a) treat "no open issue found" as license to create a fresh
issue (producing duplicates the moment GitHub returns), (b) crash mid-batch leaving
some patterns `issued` and some not, or (c) refuse cleanly? The design asserts
idempotency *"the live-search dedup guarantees this"* — but that guarantee
evaporates the instant the search call itself fails. This is the single most
dangerous gap, because the failure mode is silent duplicate-creation, which is
exactly what the live-search machinery was added to prevent.

**Proposed A.** Make the `IssueGateway` distinguish **"searched, found none"** from
**"could not search."** A failed/empty search must **never** be interpreted as
"safe to create." Concretely:
- `wrap_up` runs in two phases with an explicit barrier: **(1) reconcile + dedup
  decisions for the whole batch**, then **(2) create.** If any *search* call in
  phase 1 fails, abort phase 2 entirely with a non-zero exit and a
  "GitHub unreachable — recap written, 0 issues created, rerun wrap-up later"
  message. The recap (local, step 2 of §7) still gets written so the session isn't lost.
- Each *create* in phase 2 is followed by setting `status: issued` + `issue_url`
  for that pattern **before** moving to the next, so a mid-batch crash leaves a
  consistent partial state that a rerun completes (the rerun's live search now sees
  the already-created issues and skips them). This is the real source of
  idempotency — not the search alone, but search-then-create-then-persist per item.
- Add `--offline`/`--no-issues` already implied by `--dry-run`; document that
  `--dry-run` is the supported "GitHub is flaky, just show me" path.

---

## 2. Two agents log concurrently *before* the FastAPI phase — is the CLI really single-writer? [BLOCKER]

**Q.** §8 says "the CLI is single-writer" and defers locking to the HTTP phase. But
the whole selling point (PROTOCOL §1) is that *any* agent — Cowork, Claude Code, a
custom agent — drives the loop. Two Claude sessions open on the same repo, or one
session plus a wrap-up running in another terminal, both shell out to `loop log`.
Each does read-`patterns.json` → append-`events.jsonl` → rewrite-`patterns.json`.
That is a classic lost-update / torn-write race **today**, with zero HTTP involved.
The "single-writer" claim is an assumption, not a fact.

**Proposed A.** Don't defer the lock to Phase 5. Put a cheap advisory **file lock**
around `EventLog.append()` and `rebuild()` now (e.g. `portalocker`, cross-platform —
this repo is on Windows, so `fcntl` alone won't do). The append to `events.jsonl`
must be a single `O_APPEND` write of one line (atomic for small writes on local FS),
and the derived `patterns.json` rewrite must happen *inside the same lock* and via
write-temp-then-`os.replace` (atomic rename) so a reader never sees a half-written
rollup. Critically: treat `events.jsonl` as the only source of truth and
`patterns.json` as a rebuildable cache (the design already says this) — so even a
lost `patterns.json` update is recoverable by `loop rebuild`. The lock makes the
common path correct; the rebuild makes the worst case survivable. State explicitly:
**JSONL append is the commit point; patterns.json is best-effort cache.**

---

## 3. Who authorizes an `override` (promote), and can the loop promote without a human? [HIGH]

**Q.** `loop promote` appends an `override` event that *pins* a pattern to `fixable`
and survives rebuild. PROTOCOL §9 says "approval is mandatory" for logging and issue
creation — but is promotion covered? An override is strictly more powerful than a log:
it overrides the *algorithm's* judgment. If an agent can call `loop promote` on its
own reasoning, the agent can manufacture issues for one-off events at will, eroding
the "sev-3 act-now power stays rare and trustworthy" principle (PROTOCOL §4).

**Proposed A.** Promotion is a **human-gated** action, same bar as issue creation.
`loop promote` requires `--reason` (already) and should be invoked only after explicit
user OK, mirrored in PROTOCOL §9's approval rule — add promotion (and resolve, and
retract) to the enumerated approval-required list so it isn't read as log-only. The
agent may *propose* a promotion inline ("this is a sev-3 one-off, promote?") but the
human runs/approves it. Record the human intent in the `override.reason`. This keeps
the override's authority scarce by construction.

---

## 4. Can a `tombstone` itself be wrong — and how do you untombstone? [HIGH]

**Q.** A `tombstone` retracts a mis-logged event and `rebuild()` drops it from counts.
Append-only means you never edit — so what undoes a *mistaken* tombstone? If I retract
the wrong `event_id`, the count silently drops and a real recurring pattern can fall
back below the threshold (demoting `fixable`→`casual`), suppressing an issue. There's
no "un-retract" command, and because counts are recomputed, the demotion is invisible
unless someone re-reads the recap.

**Proposed A.** Two parts. (1) **A tombstone is itself just an event**, so the
correction for a bad tombstone is *another* event that nullifies it — define a
`tombstone` targeting a `tombstone` (or simpler: `rebuild` honors only the *latest*
override/tombstone per `target_event_id`, so a second `override`-style "reinstate"
event with `{action: reinstate}` wins). Pick one and document the last-writer-wins
rule explicitly in §4.1. (2) **Guardrail at retract time:** `loop retract` prints the
event it's about to tombstone (title + pattern + the resulting new count for that
pattern) and requires confirmation, and warns loudly if the retraction would
**demote a currently-`issued` pattern** — because retracting under an open issue is
almost always a mistake (the issue still exists on GitHub). Demoting an `issued`
pattern should be refused unless `--force`, and should never auto-close the GitHub issue.

---

## 5. The state machine has no edge for "issued pattern recurs again." [HIGH]

**Q.** Lifecycle is `casual→fixable→issued→resolved`. A pattern at `issued` has an
open GitHub issue. Then the *same mistake happens again* next session and gets logged.
What is the new event's classification, and what does wrap-up do? `classify()` only
returns `casual|fixable` — it has no concept of `issued`. So the event snapshot says
`fixable`, but the pattern is already `issued`. Does wrap-up try to create a second
issue (dedup catches it — good), or does the recurrence get lost? More importantly:
**a recurrence after an issue was filed is the most valuable signal in the whole
system** (the fix didn't land, or the issue is being ignored) and the design has no
explicit handling for it.

**Proposed A.** Define the transition explicitly: logging against an `issued` (or
`resolved`) pattern is allowed; the event's snapshot classification is irrelevant
(non-authoritative per §4.1). At wrap-up, for a pattern already `issued`, dedup finds
the open issue and **skips creation but posts a comment** on it ("recurred again in
session X, event <id>, now seen N×") and bumps `count`/`last_seen`. For a pattern that
was `resolved` but recurs, wrap-up **re-opens** (transition `resolved→fixable→issued`,
or reopen the existing closed issue) and flags it prominently in the recap as a
**regression** — this is exactly the "no regression in a follow-up session"
acceptance criterion (§6) firing. Add `issued→issued (recur)` and `resolved→fixable
(regression)` to the §7 lifecycle text; right now both are undefined.

---

## 6. Live-search dedup is a string-marker match — what's the false-merge / false-split risk? [HIGH]

**Q.** Dedup matches on label `self-improve` + hidden marker `<!-- self-improve:pattern={key} -->`,
counting `state:open`. Two failure shapes: **(a) false split** — the marker is in the
issue *body*; GitHub search on body text is full-text and tokenizes/eventual-consistency-lags,
so a freshly-created issue may not be searchable for seconds-to-minutes, meaning a
rapid second wrap-up creates a duplicate despite the marker. **(b) false merge** —
if a `pattern_key` is a substring of another (`infra-leak` vs `infra-leak-in-app`),
naive marker search could match the wrong issue. Also: who guarantees the
`self-improve` label even *exists* in the target repo (and in `--issue-repo`, a
*different* repo that may never have seen this tool)?

**Proposed A.**
- **Exact-match the marker, not full-text:** fetch candidate issues by label
  `self-improve` (a structured filter, not full-text) and then match the marker line
  by **exact string equality** (`pattern={key} -->`) in the body, in our own code, not
  via GitHub's fuzzy search ranking. This kills the substring false-merge.
- **Tolerate search lag** by relying on the per-item persist barrier from Q1: within a
  single wrap-up run, track patterns already issued *in this run* in memory so we never
  double-create within one invocation even before GitHub indexes them. Cross-invocation
  duplicates are then only possible if someone runs two wrap-ups within the indexing
  window — document that as the one residual race and gate wrap-up behind the same file
  lock as §2/Q2.
- **Ensure labels exist:** wrap-up idempotently creates the `self-improve` +
  `fix:*` labels in the target repo (and `--issue-repo`) before filing. A missing label
  must not silently drop the dedup marker.

---

## 7. `--issue-repo` routes `fix:script` issues elsewhere — but where does dedup look, and where does the marker live? [MEDIUM-HIGH]

**Q.** §7 lets `fix:script` issues land in the project repo (`gweedo/ski-assistant`)
while everything else goes to `claude-config`. So a single wrap-up now files into **two
repos**. The dedup live-search must therefore search the *correct* repo per pattern.
Does it? And `patterns.json.issue_url` is a single field — if the same `pattern_key`
somehow has issues in both repos (e.g. fix_type changed between sessions, or a manual
mis-file), which URL wins? Also: the provenance block hardcodes
`self-improve/sessions/{date}.md` — a path that doesn't exist in the *project* repo,
so the link is dead for `--issue-repo` issues.

**Proposed A.**
- Dedup search target = **the repo the issue would be filed into**, computed per
  pattern from its `fix_type` + `--issue-repo` rule, *before* searching. One pattern →
  one target repo deterministically (the routing rule is a pure function of `fix_type`),
  so the "same key in two repos" case can only arise if `fix_type` changed; handle that
  by keying dedup on (pattern_key) within (resolved target repo) and treating a
  fix_type change as a new routing target → re-file is acceptable and the old issue is
  reconciled/closed-as-moved.
- Make the provenance recap link an **absolute URL** into `gweedo/claude-config`
  (where recaps always live), not a repo-relative path, so cross-repo issues link back
  correctly.

---

## 8. Reject-unknown-`pattern_key` uses string distance — does the guardrail fight the user or get rubber-stamped away? [MEDIUM-HIGH]

**Q.** `loop log` rejects an unknown key and shows the 3 closest by normalized string
distance, requiring `--new-pattern` to proceed. Two opposing failure modes: **(a)**
the guardrail is *too eager* — every genuinely-new pattern requires `--new-pattern`,
which an agent will quickly learn to *always* pass, turning the guardrail into noise it
rubber-stamps (defeating the count-protection purpose). **(b)** String distance is the
wrong metric — `raw-sql-in-router` and `sql-string-in-handler` are the same pattern
with ~0 string overlap, so the suggestion list won't surface the true duplicate, and
the user dutifully creates a near-dup with `--new-pattern`. The design even concedes
pgvector is "the later upgrade" — implying the string version is known-weak.

**Proposed A.** Keep the guardrail but make it *cheap to comply correctly and slightly
costly to bypass*: (1) when `--new-pattern` is used, **echo the new key into the recap's
"new patterns this session" line** and into the wrap-up summary, so creating a new key
is *visible* and reviewable — social pressure replaces hard enforcement. (2) Lower the
false-negative rate without pgvector by matching on **tokenized kebab parts** (Jaccard
over `{raw, sql, in, router}`) in addition to edit distance — catches reordered/synonym-
free dups that pure string distance misses. (3) Accept that semantic dups
(`raw-sql`/`sql-string`) are genuinely out of reach until pgvector and say so — but
mitigate by the visible-new-key review in (1), which is where a human catches it.
The point: the guardrail's job in v1 is *make collisions visible*, not *prevent all of
them*.

---

## 9. Wrap-up reconciliation flips `issued→resolved` when "the issue is found closed" — closed how? [MEDIUM]

**Q.** §7: a pattern goes to `resolved` either via `loop resolve` or "wrap-up
reconciliation when the issue is closed." But GitHub issues close for many reasons:
fix merged, closed as stale, closed as duplicate, closed as "won't fix," or closed by a
bot. Auto-marking `resolved` on *any* closed state conflates "we fixed it" with "we
gave up." Then the regression detector (Q5) won't fire correctly, and the recap claims
a fix landed when it didn't.

**Proposed A.** Reconciliation should map GitHub's **close reason** (the API exposes
`state_reason`: `completed` vs `not_planned`) to loop status: `completed` →
`resolved`; `not_planned`/`duplicate` → a distinct `closed_unfixed` status (or back to
`fixable` with a note) so it re-surfaces in `loop list --unissued`. Don't treat
"closed" as a monolith. If we don't want a new status in v1, the conservative default
is: **only `loop resolve` (an explicit human act) sets `resolved`**; wrap-up
reconciliation merely *reports* "linked issue is closed — run `loop resolve` if the fix
actually landed," and never auto-resolves. Pick the conservative default for v1.

---

## 10. `session_id` slugs and recaps — what about a session that spans midnight, or two sessions same slug same day? [MEDIUM]

**Q.** §5/§10: `session_id = <YYYY-MM-DD>[-<slug>]`, recap path
`sessions/<session_id>.md`, "a session is a unit of work the agent declares, not a
calendar day." Good — but: (a) who *generates* the slug, and what stops two
declared-but-distinct sessions from colliding on `2026-06-20-ski` (overwriting the
recap)? (b) A long session crossing midnight: events get one `session_id` but the date
prefix is now "wrong" for half of them — is that fine? (c) Wrap-up writes
`sessions/<session_id>.md` — does it overwrite an existing recap (re-running wrap-up) or
append? Idempotent issue creation is handled, but recap-file idempotency isn't stated.

**Proposed A.** (a) The agent proposes a slug at session start; `loop log`/`wrap-up`
**refuse to silently reuse** a `session_id` that already has a *closed/wrapped* recap —
either require a distinct slug or an explicit `--resume`. Day-collision is solved by the
slug being required-distinct, not by the date. (b) Midnight-crossing is fine: the
`session_id` is a label, not a date assertion; the authoritative time is each event's
`ts` (UTC). Document that the date prefix is "when the session started," nothing more.
(c) Wrap-up **overwrites** the recap deterministically (it's a pure render of the
session view — re-rendering yields the same file), which is consistent with wrap-up's
idempotency claim. State this explicitly so no one builds append logic.

---

## 11. `patterns.json` is "always rebuildable" — but `issued`/`resolved` are carried forward, not re-derived. So is rebuild actually lossless? [MEDIUM]

**Q.** §4.2 says `patterns.json` is *derived* and `loop rebuild` regenerates it from
`events.jsonl`. But §7 says `issued`/`resolved` are **carried forward from issue state,
not re-derived**. These two statements conflict: if I delete `patterns.json` and run
`loop rebuild`, where do `issued`/`resolved` and `issue_url` come from? They are *not*
in the event log unless an event records them. So rebuild from scratch would silently
**demote every issued/resolved pattern back to casual/fixable** and lose every
`issue_url` — then the next wrap-up re-files duplicate issues (dedup saves us only if
GitHub is up, see Q1/Q6). The "single source of truth is the JSONL" claim is **false**
for issue status.

**Proposed A.** Make issue-state transitions **first-class events** so the log truly is
the source of truth: when wrap-up files an issue, append an `issue_filed` event
(`{pattern_key, issue_url, repo}`); `loop resolve` appends a `resolved` event. Then
`rebuild()` folds these in exactly like `override`/`tombstone`, and `issued`/`resolved`/
`issue_url` *are* re-derivable — rebuild becomes genuinely lossless and the SSoT claim
holds. (Alternative, weaker: rebuild reconciles status by live-searching GitHub for the
markers — but that re-introduces the network dependency and Q1's failure mode into a
command that should be offline-safe.) Choose the event-sourced option; it's the only
one consistent with the design's own append-only / rebuildable principles.

---

## 12. `affected_paths` and `summary` carry file paths and prose into a *public-by-default* GitHub issue — secret-scrub is a manual rule. [MEDIUM-LOW]

**Q.** PROTOCOL §9 forbids secrets in the log "by rule," enforced by the agent's
judgment. But the log feeds the issue template verbatim (`summary`, `root_cause`,
`proposed_fix`, `affected_paths`, even `event_ids`). If the repo is public, a leaked
path like `src/config/prod_credentials.py` or a root-cause that quotes an error
message containing a token gets published to GitHub. The guardrail is "be careful,"
which is the weakest possible control for a data-exfiltration path.

**Proposed A.** Add a **mechanical pre-publish scrub** in `build_issue` (it's pure, so
this is testable): run the issue body through a regex denylist (common token shapes:
`gh[pousr]_…`, AWS keys, `-----BEGIN … PRIVATE KEY-----`, `password=`, long
hex/base64 blobs) and **refuse to file** (or redact + warn) on a hit, rather than
trusting the agent's restraint. This converts a soft rule into an enforced gate at the
one choke point (issue creation) where leakage actually becomes public. Keep the
human "no secrets" rule too, but defense-in-depth: the machine catches what the agent
misses.

---

## Priority summary

- **Blockers (fix before pass-2 build):** #1 (GitHub-down duplicate creation),
  #2 (concurrent CLI writers — the "single-writer" assumption is false today).
- **High:** #3 (who approves override), #4 (wrong/irreversible tombstone),
  #5 (recurrence after issued — the highest-value undefined signal),
  #6 (dedup marker false-split/merge + missing labels).
- **Medium-high → medium:** #7 (two-repo dedup + dead provenance links),
  #8 (string-distance guardrail rubber-stamping / semantic blindness),
  #9 (closed≠resolved), #10 (session_id collisions & recap idempotency),
  #11 (rebuild is not lossless for issue status — contradicts the SSoT claim).
- **Medium-low:** #12 (no mechanical secret scrub before publishing to GitHub).

**Single most dangerous unstated assumption:** that the live-GitHub-search dedup
*guarantees* idempotency. It only does so when GitHub is reachable, indexed, and the
process doesn't die mid-batch — none of which the design currently ensures (#1, #6, #11).
Idempotency must come from a **per-item search→create→persist barrier under a write
lock**, with the JSONL (including issue-state events) as the true source of truth — not
from the search call alone.
