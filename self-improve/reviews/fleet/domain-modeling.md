# Domain-Modeling Review — Self-Improvement Loop

Lens: ubiquitous language, domain terminology, state machines.
Scope: `PROTOCOL.md` and `DESIGN.md` as updated (status state machine, `override`/`tombstone` events, `session_id` convention).
Verdict: **the model is close, but two vocabularies (`classification` and `status`) overlap in a way that will confuse readers and one state (`resolved`) is a dead-end. Fix both before pass 2.**

---

## 1. The central issue: `classification` vs `status` are two overlapping vocabularies

The docs use two enums that share values but are never explicitly reconciled:

| Term | Lives on | Values | Authority | Defined in |
|---|---|---|---|---|
| `classification` | Event (`events.jsonl`) | `casual` \| `fixable` | **Non-authoritative snapshot** at log time | DESIGN §4.1, §5; PROTOCOL §4 |
| `status` | Pattern (`patterns.json`) | `casual` \| `fixable` \| `issued` \| `resolved` | **Authoritative**, recomputed by `rebuild` | DESIGN §4.2, §7; PROTOCOL §7 |

The overlap (`casual`, `fixable` appear in both) is the problem. A reader sees `casual`/`fixable` in two places and cannot tell, without close reading, that:

- one is a per-event opinion frozen at write time, and
- the other is the current truth for the whole pattern.

DESIGN §4.1 and §5 already carry a defensive footnote ("Non-authoritative snapshot … never read an old event's `classification` to decide current state"). The need for that warning is the symptom: **the same words are doing two jobs.** A footnote patches the confusion; it does not remove it.

### Recommendation — distinguish, do not unify

Do **not** merge them into one field — they genuinely model different things (an event-level judgment vs a pattern-level lifecycle). Instead make them *lexically distinct* so the overlap disappears:

**Option A (preferred): rename the event field to a verdict noun.**
Event carries `verdict: casual | fixable` (the agent's call at capture time). Pattern carries `status: casual | fixable | issued | resolved`. Now "classification" stops being an overloaded word; `verdict` is unmistakably the snapshot, `status` is unmistakably the lifecycle. The `classify()` function returns a `Verdict`.

**Option B: keep `classification` on the event, rename the two shared status values.**
Pattern status becomes `tracking | actionable | issued | resolved` (where `tracking`≈casual, `actionable`≈fixable). Heavier — it churns PROTOCOL §4's whole "casual vs fixable" framing, which is otherwise good. Not recommended.

Either way, the rule is: **two concepts, two disjoint vocabularies.** Pick A.

> Whichever is chosen, PROTOCOL §4 ("Classification — casual vs fixable") and DESIGN §5 ("Classification algorithm") must be retitled and cross-referenced to the pattern `status` machine in DESIGN §7 / PROTOCOL §7. Right now §4/§5 describe the *event* judgment and §7 describes the *pattern* lifecycle, but nothing in §4/§5 tells the reader "this feeds the pattern status machine in §7."

---

## 2. The `status` state machine is under-specified

Declared transitions (DESIGN §7, PROTOCOL §7):

```
casual ──(recurrence≥2 OR severity==3)──▶ fixable ──(wrap-up files issue)──▶ issued ──(resolve / reconcile-closed)──▶ resolved
```

### Gaps

**G1 — `resolved` is a dead-end; recurrence after resolution is undefined.**
The task's own question: *what happens to a `resolved` pattern that recurs again?* The docs have no answer. A new event with a resolved `pattern_key` will bump `count` and re-trigger the §5 rule, but §7 explicitly says `issued`/`resolved` are **carried forward, not re-derived** by `rebuild`. So a resolved pattern that recurs is stuck in `resolved` while accruing new events that everyone is told to ignore. That is a silent correctness hole: a regression of a previously fixed pattern produces **no new issue**.
*Fix:* define a `resolved → fixable` (or a distinct `regressed`) transition triggered when a new (non-tombstoned) event lands on a `resolved` pattern. Note the issue template already bakes in "No regression of the pattern in a follow-up session" (DESIGN §6) as acceptance criteria — so regression detection is in-scope intent but missing from the machine.

**G2 — `casual → resolved` and `fixable → resolved (without issue)` are undefined.**
`loop resolve <pattern_key>` (PROTOCOL §8, DESIGN §7) can be run against any pattern. What if I resolve a `casual` pattern (decide it's a non-problem)? Or a `fixable` one that never got an issue? The machine only documents `issued → resolved`. Either forbid these (resolve only operates on `issued`) or add the transitions explicitly. A "won't-fix / dismissed" terminal state may be the cleaner model for "casual thing I want to stop tracking."

**G3 — Split authority across `rebuild` is a latent inconsistency.**
`rebuild` recomputes `casual`/`fixable` from the log but **carries forward** `issued`/`resolved` from issue state (DESIGN §7). So `patterns.json` is only *partly* derived from `events.jsonl` — contradicting DESIGN §4.2's claim that "`patterns.json` is **derived** from `events.jsonl` and can always be rebuilt from it." The `issued`/`resolved` facts actually derive from **GitHub** (live search, §6) plus the `override` events. State this precisely: the source of truth for `casual`/`fixable` is the JSONL; the source of truth for `issued`/`resolved` is GitHub issue state (cached in `patterns.json`). Otherwise "rebuild from the log" overpromises.

**G4 — `override` (promotion) lands a pattern at `fixable` but the machine entry-point is unstated.**
PROTOCOL §8 / DESIGN §4.1: `loop promote` appends an `override` event that pins a pattern's status. This is a `casual → fixable` jump that bypasses the §5 rule. The state machine in §7 only lists "recurrence/severity" as the `casual → fixable` trigger; manual promotion is a second, equally valid trigger and should be drawn on the diagram.

**G5 — `tombstone` can move a pattern *backwards* and that is undocumented.**
Retracting the 2nd event of a pattern drops its count from 2 to 1, so `rebuild` would recompute `fixable → casual`. That is fine and probably intended, but it means transitions are **not monotonic** and `casual`/`fixable` is fully re-derivable each rebuild (good), while `issued`/`resolved` is not (per G3). Worth one explicit sentence: "retraction can demote `fixable → casual`; it cannot demote `issued`/`resolved` (those are gated on issue state)."

### Proposed complete state machine

```
                    promote (override event)
        ┌───────────────────────────────────────────┐
        │                                            ▼
   ┌────────┐  count≥2 OR sev==3       ┌─────────┐  wrap-up files issue   ┌────────┐
   │ casual │ ───────────────────────▶ │ fixable │ ─────────────────────▶ │ issued │
   └────────┘                          └─────────┘                        └────────┘
        ▲   │                               ▲ │                              │
        │   │ retract drops count<2         │ │ new event on resolved        │ resolve /
        └───┘ (rebuild: fixable→casual)     │ │ pattern (REGRESSION)         │ issue closed
                                            │ │                              ▼
                                            │ └──────────────────────── ┌──────────┐
                                            └──────────────────────────▶│ resolved │
                                              regression re-opens        └──────────┘
```

Every state now has a defined exit, and `resolved` is no longer a black hole.

---

## 3. Term-by-term consistency audit

| Term | Defined once? | Issue |
|---|---|---|
| `event` | Yes (DESIGN §4.1) | Consistent. But note `override`/`tombstone` are also "events" with a different shape — see below. |
| `pattern` | Implicitly (DESIGN §4.2) | **Never given a one-line definition.** Used heavily; deserves a glossary entry. A pattern is the *recurring* thing; an event is an *instance*. Make that instance↔type relationship explicit. |
| `signal` | PROTOCOL §2 | Consistent, but **only in PROTOCOL.** DESIGN never uses "signal" — it jumps straight to `type`. A DESIGN reader won't know "the four signals" = the `type` enum. Add a bridge: "each signal is recorded as an event `type`." |
| `type` | DESIGN §4.1 | **Overloaded.** `type` now spans two disjoint families: the four *signals* (`code_failure`…) and the two *corrections* (`override`, `tombstone`). They are not signals and don't carry `severity`/`fix_type`/`pattern_key` the same way. Recommend splitting conceptually: either a separate field (`kind: signal | correction`) or document that `type` has two sub-enums with different required fields. As written, an `override` event in `events.jsonl` has undefined values for half the §4.1 columns. |
| `fix_type` | PROTOCOL §6, DESIGN §4.1 | Consistent across both. Good. |
| `severity` | PROTOCOL §4, DESIGN §4.1 | Consistent (1–3 scale). Good. |
| `classification` | PROTOCOL §4, DESIGN §4.1/§5 | The §1 problem. Overlaps `status`. |
| `status` | DESIGN §4.2/§7, PROTOCOL §7 | The §1/§2 problem. Lifecycle under-specified. |
| `override` | DESIGN §4.1, PROTOCOL §8 | Term is clear, but it is *also* called a "promotion" (PROTOCOL §4, `loop promote`). Two names for one concept: pick "promotion" as the domain verb and "override" as the event `type` recording it, and say so. |
| `tombstone` | DESIGN §4.1, PROTOCOL §8 | Also called a "retraction" (`loop retract`). Same as above: "retraction" = the act, `tombstone` = the event. Fine if stated. |
| `session_id` | DESIGN §10, §4.1 | `<YYYY-MM-DD>[-<slug>]`. Consistent. DESIGN §10 gives the strong definition ("a unit of work the agent declares, not a calendar day") — good. But §4.1 example and §3 layout still imply 1 recap file per `session_id` while §10 allows same-day slugged sessions; the recap path `sessions/<session_id>.md` is correct, just make sure no prose still says "one recap per day." |
| `pattern_key` | PROTOCOL §5, DESIGN §4.1 | Consistent and well-guarded. Good. |
| `recurrence_count` / `count` | PROTOCOL §4 / DESIGN §4.2 | **Two names for one number.** PROTOCOL calls it `recurrence_count`; DESIGN's `patterns.json` calls it `count`; §5 code calls the param `count_for_pattern`. Pick one (`count` in storage, "recurrence count" in prose) and note the synonym. |

---

## 4. Recommendation: yes, add an explicit glossary (CONTEXT.md) and one ADR

There is currently **no single terms table**; definitions are scattered across PROTOCOL §2/§4/§5/§6 and DESIGN §4. A reader must assemble the vocabulary from both files. For a tool whose entire value is a *shared ubiquitous language* across multiple agents reading PROTOCOL.md, this is exactly the case where a glossary pays off.

### Proposed `CONTEXT.md` (glossary)

```md
# Self-Improvement Loop

A portable, agent-driven loop that captures engineering mistakes as approved
events, learns which are systematic, and turns those into GitHub issues.

## Language

**Event**:
A single approved record of one observed mistake, appended to `events.jsonl`.
The instance, not the type. Immutable once written.
_Avoid_: log entry, incident.

**Signal**:
One of the four mistake categories an agent watches for (`code_failure`,
`misunderstood_intent`, `wrong_approach`, `repeated_correction`). Recorded as an
event's `type`.
_Avoid_: trigger, detection.

**Pattern**:
A recurring class of mistake, identified by a stable `pattern_key`. Many events
roll up into one pattern. The pattern — not the event — carries the authoritative
lifecycle.
_Avoid_: rule, category, group.

**Pattern key**:
The stable kebab-case identifier that groups events into a pattern and against
which recurrence is counted.
_Avoid_: tag, slug, label.

**Verdict** (proposed rename of event `classification`):
The agent's `casual`/`fixable` call for a single event at capture time. A
non-authoritative snapshot; never the source of current truth.
_Avoid_: classification (overloaded with status), grade.

**Status**:
The authoritative lifecycle state of a *pattern*: `casual → fixable → issued →
resolved` (+ regression back to `fixable`). `casual`/`fixable` derive from the
log; `issued`/`resolved` derive from GitHub issue state.
_Avoid_: state (when ambiguous), classification.

**Severity**:
A 1–3 judgment of blast radius set when logging an event. 3 forces `fixable` even
as a one-off.

**Fix type**:
The proposed remedy channel for a pattern: `script`, `skill_edit`, `new_skill`,
`instruction_update`. Maps 1:1 to a GitHub `fix:*` label.
_Avoid_: remedy, action.

**Promotion** (event `type: override`):
Manually forcing a `casual` pattern to `fixable` for a severe one-off. Recorded as
an `override` event so it survives `rebuild`.
_Avoid_: escalation, upgrade.

**Retraction** (event `type: tombstone`):
Withdrawing a mis-logged event. Recorded as a `tombstone`; excluded from all counts
on `rebuild`.
_Avoid_: deletion, undo (the log is append-only — nothing is deleted).

**Session**:
A unit of work the agent declares, identified by `session_id`
(`<YYYY-MM-DD>[-<slug>]`). Groups events for one recap. Not a calendar day.

**Recurrence count**:
The number of non-retracted events sharing a `pattern_key`. Stored as `count` in
`patterns.json`. The threshold (≥2) is the core promotion trigger.

**Wrap-up**:
The end-of-session pass that recomputes statuses, writes the recap, and files
issues for fixable, un-issued patterns. Idempotent.
```

### Proposed ADR

One ADR clears the §1 bar (hard to reverse — it touches the on-disk event schema and every doc; surprising — readers will ask "why two words for casual/fixable?"; a real trade-off — merge vs distinguish vs rename):

**`docs/adr/0001-event-verdict-vs-pattern-status.md`** — *"Separate the event-level verdict from the pattern-level status."* Records: the decision to keep them as distinct concepts, the rename of the event field to `verdict`, that `casual`/`fixable` no longer appear on two entities under the same name, and that pattern `status` is split-source (log for casual/fixable, GitHub for issued/resolved). A second short ADR for "regression re-opens a resolved pattern" (G1) is optional but defensible since it also touches the rebuild contract.

---

## 5. Priority summary

1. **(High) Resolve `classification`/`status` overlap** — rename event field to `verdict` (§1, Option A). Removes the need for the defensive footnotes and the single biggest source of reader confusion.
2. **(High) Define `resolved` regression exit** (G1) — currently a correctness hole: a re-occurring fixed pattern files no new issue.
3. **(Medium) Pin down `loop resolve` legal source states** (G2) and **document split authority of `rebuild`** (G3) — DESIGN §4.2's "fully derived" claim is currently false.
4. **(Medium) Split `type` into signal vs correction** (§3) — `override`/`tombstone` don't fit the §4.1 event schema.
5. **(Low) Unify synonyms**: recurrence_count/count, promotion/override, retraction/tombstone — pick a canonical term, list the other under _Avoid_.
6. **(Low) Add the bridge sentence** linking "signal" (PROTOCOL) to event `type` (DESIGN).
7. Adopt the `CONTEXT.md` glossary above and ADR-0001.

No edits were made to `PROTOCOL.md` or `DESIGN.md`.
