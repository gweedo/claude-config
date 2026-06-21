# Self-Improvement Loop — DESIGN

Architecture and data design for the loop. Companion to `PROTOCOL.md` (the rules the
agent follows). This document is the engineering reference for the CLI we scaffold in
pass 2.

---

## 1. Goals & non-goals

**Goals**
- Capture engineering mistakes as they happen, with your approval.
- Learn which mistakes are *systematic* (recurrence + severity), not one-offs.
- Turn systematic mistakes into well-formed GitHub issues for later implementation.
- Be **tool-agnostic**: any agent can drive it via files + a CLI. No lock-in to Cowork.
- Keep everything **git-tracked and diffable** so the knowledge is reviewable and portable.

**Non-goals**
- It does **not** edit code or skills. It produces issues; a separate pass implements them.
- It is **not** a real-time monitor/daemon. The working agent is the sensor.
- No database in v1. Plain files. (pgvector dedup is a documented future option, §9.)

---

## 2. Architecture overview

```
            ┌──────────────────────── core ─────────────────────────────────────────────────┐
            │  loop.py (use cases):  record_event(store, draft)   wrap_up(store, issues_gw)   │
            │  pure parts:  classify · fold · next_status · build_recap · build_issue · suggest │
            │  EventLog (store port): read() · append() · write_snapshot() — pure I/O only      │
            └───────▲───────────────────────────────────────────────────┬───────────────────┘
                    │                          ports │ (IssueGateway, PatternMatcher)
   adapters ►  CLI (loop.py)  ── pass 1 ──┐                          GitHub issues (handoff)
                    │                      │
              FastAPI (later) ── pass 3 ──┘
                    │
            ┌───────┴───────────────────────────────────────────┐
   storage  │  events.jsonl  patterns.json  sessions/<session_id>.md │ (git-tracked files)
            └────────────────────────────────────────────────────┘
```

The **core** splits in two: **pure functions** (`classify`, `fold`, `next_status`,
`build_recap`, `build_issue`, `suggest_keys`) that take data in and return data out, and
**use-case functions** (`record_event`, `wrap_up`) in `core/loop.py` that orchestrate them.
Persistence lives behind an `EventLog` store port, network behind an `IssueGateway` port,
and pattern-similarity behind a `PatternMatcher` port — pure functions never touch the
filesystem or network. The **CLI** is a thin adapter today; a **FastAPI** service is the
same use cases behind HTTP later (§8). This separation is the DDD-flavoured part: domain
logic never depends on the delivery mechanism.

**One producer of derived state.** `patterns.json` is never mutated incrementally. It is the
materialized output of a single pure fold, `fold(events) -> dict[pattern_key, Pattern]`
(which calls `classify` and `next_status` per pattern). `rebuild()` is literally
`store.write_snapshot(fold(store.read()))`, and `loop log` rebuilds after appending — a full
fold over a knowledge-log-sized JSONL is microseconds. This makes `patterns.json` a *provable*
cache: there is no code path that can desync it from the append-only log. Persistence and
write-serialization are the store adapter's job — see §8 for the multi-writer concurrency
constraint, which #1's single-producer design shrinks to a one-line append lock.

---

## 3. Repo layout

> Assumed placement inside `gweedo/claude-config`. Adjust once we confirm the repo's
> existing conventions.

```
claude-config/
└── self-improve/
    ├── PROTOCOL.md            # agent rulebook (already drafted)
    ├── DESIGN.md              # this file
    ├── events.jsonl           # append-only event log (source of truth)
    ├── patterns.json          # pattern registry: key -> rollup (counts, status, issue)
    ├── sessions/
    │   └── 2026-06-20-ski.md  # one recap per session; path is sessions/<session_id>.md
    ├── core/
    │   ├── __init__.py
    │   ├── models.py          # Event, Pattern, FixType, Severity, Verdict, Status (enums)
    │   ├── loop.py            # use cases: record_event(), wrap_up() — both adapters call these
    │   ├── ports.py           # IssueGateway + PatternMatcher protocols (seams, no impl here)
    │   ├── store.py           # EventLog: pure I/O — read()/append()/write_snapshot() only
    │   ├── classify.py        # the recurrence + severity rule -> Verdict (pure)
    │   ├── fold.py            # fold(events) -> rollup; the ONLY producer of patterns.json (pure)
    │   ├── status.py          # next_status(current, verdict, issue_state) -> Status (transition table)
    │   ├── patterns.py        # suggest_keys(key, known) -> 3 closest (pure; PatternMatcher default)
    │   ├── recap.py           # render a pre-classified SessionView -> markdown (pure, no rules)
    │   └── issues.py          # build GitHub issue payloads + pre-publish secret scrub (pure)
    ├── cli/
    │   └── loop.py            # argparse/typer adapter -> core.loop use cases
    ├── adapters/
    │   └── github.py          # the only place that talks to GitHub; implements IssueGateway
    ├── tests/
    │   ├── test_classify.py   # boundary corners: count 1↔2, severity 2↔3
    │   ├── test_fold.py       # rollup fold; override/tombstone/issue_filed/resolved folding
    │   ├── test_store.py      # read/append/write_snapshot round-trip on tmp_path
    │   ├── test_patterns.py   # suggest_keys reject-unknown + 3-closest
    │   ├── test_issues.py     # build_issue marker + label mapping + secret scrub
    │   ├── test_recap.py      # render from a fixed SessionView; re-derives nothing
    │   ├── test_loop.py       # record_event + wrap_up idempotency w/ FakeIssueGateway
    │   ├── test_github.py     # IssueGateway adapter contract, stubbed HTTP
    │   └── fakes.py           # FakeIssueGateway (in-memory), fixed clock/id factories
    └── pyproject.toml
```

---

## 4. Data model

### 4.1 `events.jsonl` — one JSON object per line (append-only)

| Field | Type | Notes |
|---|---|---|
| `id` | str (uuid4) | Unique event id. |
| `ts` | str (ISO-8601) | UTC timestamp. |
| `session_id` | str | e.g. `2026-06-20-ski`. Groups events for the recap. |
| `type` | enum | `code_failure` \| `misunderstood_intent` \| `wrong_approach` \| `repeated_correction`. |
| `pattern_key` | str | kebab-case; the recurrence key (PROTOCOL §5). |
| `title` | str | One-line label. |
| `summary` | str | What happened, no secrets. |
| `root_cause` | str | The high-level *why* — the actual point of the loop. |
| `severity` | int | 1–3. |
| `verdict` | enum | `casual` \| `fixable`. The agent's per-event call at capture time — a **non-authoritative snapshot**. The authoritative pattern lifecycle is `patterns.json.status` (§4.2); the two vocabularies are kept lexically distinct on purpose (event = `verdict`, pattern = `status`). Never read an old event's `verdict` to decide current state. |
| `fix_type` | enum | `script` \| `skill_edit` \| `new_skill` \| `instruction_update`. |
| `proposed_fix` | str | Concrete approach. |
| `affected_paths` | list[str] | Files/dirs involved. |
| `approved` | bool | Always `true` once written (capture requires approval). |

> **Determinism.** `id` (uuid4) and `ts` (now) are injected via a `clock`/`id_factory` passed
> into `record_event`, defaulting to the real ones, so tests produce byte-stable events. The
> event has **no `issue_url`** — issue linkage is a pattern-level fact (§4.2), reached only
> through issue-state events below, so there is one home for it, not two.

Append-only means the log is an audit trail; corrections and lifecycle changes are new events,
never edits. `rebuild()`/`fold()` interpret four non-signal event shapes, each carrying a
`target` (`target_event_id` or `pattern_key`) — last-writer-wins per target:

- **`type: "override"`** — a promotion (PROTOCOL §4 / `loop promote`). Carries
  `override: {verdict, reason}` and `target_event_id`; pins a pattern to `fixable`. Survives rebuild.
- **`type: "tombstone"`** — a retraction of a mis-logged event (`loop retract`). References the
  original `target_event_id`; excluded from all counts. A later `tombstone` of a `tombstone`
  reinstates the event (last-writer-wins), so a wrong retraction is itself correctable.
- **`type: "issue_filed"`** — appended by `wrap_up` when it creates an issue. Carries
  `{pattern_key, issue_url, repo}`; `fold()` derives `status: issued` + `issue_url` from it.
- **`type: "resolved"`** — appended by `loop resolve` (or wrap-up reconciliation on a
  `state_reason: completed` close). Carries `{pattern_key, reason}`; `fold()` derives
  `status: resolved`. A new signal event landing on a `resolved` pattern is a **regression** →
  `fold()` returns it to `fixable` (see §7).

Because issue-state lives in the log as events, `fold()` is **lossless**: deleting
`patterns.json` and rebuilding reconstructs `status` and `issue_url` exactly — GitHub is the
external effect, the log is the record of it.

### 4.2 `patterns.json` — rollup keyed by `pattern_key`

```json
{
  "infra-leak-in-app": {
    "count": 2,
    "max_severity": 2,
    "status": "fixable",        // casual | fixable | issued | resolved
    "first_seen": "2026-06-12T09:14:00Z",
    "last_seen": "2026-06-20T17:02:00Z",
    "event_ids": ["…", "…"],
    "issue_url": "https://github.com/gweedo/claude-config/issues/42",
    "fix_type": "instruction_update"
  }
}
```

Every field above is **derived** by `fold(events)` — `count`/`max_severity`/`event_ids` from the
signal events (minus tombstoned ones), `status`/`issue_url` from the `issue_filed`/`resolved`
events. `patterns.json` can therefore always be rebuilt from `events.jsonl` alone (`loop
rebuild`), with **no** value carried forward out-of-band: the JSONL is the single source of
truth, fully and losslessly. `patterns.json` is a materialized cache, never authoritative.

### 4.3 `sessions/<session_id>.md` — the recap

```markdown
# Session 2026-06-20-ski — recap

## Logged this session (3)
- ⚙️ code_failure · `aineva-missing-field` · sev 2 · casual (1×)
- 🧭 wrong_approach · `infra-leak-in-app` · sev 2 · **fixable (2×)** → issue #42
- ✏️ repeated_correction · `missing-type-hints` · sev 1 · casual (1×)

## Promoted to issues (1)
- #42 [fix:instructions] Enforce repository-only data access

## Still casual / watching (2)
- `aineva-missing-field` (1×), `missing-type-hints` (1×)
```

---

## 5. Verdict & status

Two distinct concepts, two disjoint vocabularies (see PROTOCOL §4):
- **`verdict`** (`casual | fixable`) — `classify()`'s call for a single event.
- **`status`** (`casual | fixable | issued | resolved`) — a *pattern's* lifecycle, produced by
  `next_status()` inside `fold()`.

```python
def classify(event: Event, count_for_pattern: int) -> Verdict:
    if event.severity == 3 or count_for_pattern >= 2:
        return Verdict.FIXABLE
    return Verdict.CASUAL

def next_status(current: Status, verdict: Verdict, issue_state: IssueState | None) -> Status:
    # the transition table — the ONLY place that knows the forbidden moves:
    #   a recomputed `fixable` must NOT knock an `issued` pattern back and re-file a duplicate;
    #   a signal event on a `resolved` pattern is a regression -> back to `fixable`.
    ...
```

- `classify` is a total function of two inputs; `next_status` is the transition table. Both are
  pure and live in `classify.py` / `status.py`, called by `fold()` — **one home each**, never
  re-implemented in a renderer or an adapter.
- The `verdict` stored on an Event is a **non-authoritative snapshot** at log time; the
  authoritative pattern `status` is whatever `fold(events)` currently computes.
- Wrap-up produces an already-resolved `SessionView`; `recap.py` is a pure renderer of it and
  must not re-derive verdicts, counts, statuses, or thresholds.
- Threshold (`>= 2`) and severity ceiling (`3`) are constants in `classify.py` — easy to tune.

---

## 6. GitHub issue template

One issue per fixable `pattern_key` (skip if an open issue for that key already exists).

> **Dedup lookup.** Wrap-up decides "does an open issue already exist?" by a **live GitHub
> search** on label `self-improve` + the hidden marker below, counting only `state:open`
> issues as blocking. `patterns.json.issue_url` is a cache reconciled from that result, never
> the gate — a manually-closed issue must not silently suppress re-filing. The dedup decision
> lives in `core/loop.wrap_up` against the injected `IssueGateway` port (§2), so `issues.py`
> stays pure and the policy has exactly one home.

```markdown
<!-- self-improve:pattern={pattern_key} -->
**Title:** [{fix_label}] {title}

### Pattern
`{pattern_key}` — seen {count}× (severity {max_severity})

### Root cause
{root_cause}

### Proposed fix ({fix_type})
{proposed_fix}

### Affected files
- {path_1}
- {path_2}

### Acceptance criteria
- [ ] {derived from proposed_fix}
- [ ] No regression of the pattern in a follow-up session

### Provenance
- First seen: {first_seen} · Last seen: {last_seen}
- Source recap: https://github.com/gweedo/claude-config/blob/main/self-improve/sessions/{session_id}.md
- Event ids: {event_ids}

_Labels: `self-improve`, `{fix_label}`_
```

The recap link is an **absolute URL** into `claude-config` (where recaps always live) so
`--issue-repo` issues filed in a *different* repo still link back. Dedup matches the marker by
**exact string equality** on `pattern={key} -->` (not GitHub's fuzzy full-text search), so a
`pattern_key` that is a substring of another can't false-merge. Wrap-up idempotently ensures the
`self-improve` + `fix:*` labels exist in the target repo (and `--issue-repo`) before filing.
`build_issue` runs a **mechanical secret scrub** (regex denylist: `gh[pousr]_…`, AWS keys,
`-----BEGIN … PRIVATE KEY-----`, `password=`, long hex/base64) and refuses to file on a hit —
defense-in-depth behind PROTOCOL §9's human rule, enforced at the one point where leakage goes public.

**Labels:** `self-improve` (always) + one of `fix:script` / `fix:skill` /
`fix:new-skill` / `fix:instructions`. These let a downstream implementer agent filter
its queue (e.g. only pick up `fix:script` for autonomous work).

---

## 7. CLI design (pass 2)

| Command | Purpose |
|---|---|
| `loop log … [--new-pattern]` | Append an approved event; print resulting `verdict` + pattern `status`. Rejects an unknown `pattern_key` (shows the 3 closest) unless `--new-pattern` is passed. |
| `loop list [--status] [--session] [--pattern] [--unissued]` | Review open/casual/fixable items + counts. `--unissued` surfaces fixable patterns with no open issue. |
| `loop promote <event_id> --reason …` | Force a casual item to fixable (severe one-off). Appends an `override` event; survives `rebuild`. |
| `loop retract <event_id> --reason …` | Retract a mis-logged event. Appends a `tombstone`; `rebuild` drops it from counts. |
| `loop wrap-up [--session] [--repo] [--issue-repo] [--dry-run]` | Recompute, write recap, create issues. Each created issue appends an `issue_filed` event (→ `fold` derives `status: issued` + `issue_url`). `--issue-repo` routes `fix:script` issues to the project repo. |
| `loop resolve <pattern_key> --reason …` | Append a `resolved` event (→ `fold` derives `status: resolved`). |
| `loop rebuild` | Regenerate `patterns.json` = `write_snapshot(fold(read()))`; folds in `override`/`tombstone`/`issue_filed`/`resolved`. Offline, lossless. |

**`status` lifecycle** (the transition table in `status.py`):

```
   casual ──(count≥2 OR sev==3, §5)──▶ fixable ──(wrap-up: issue_filed event)──▶ issued
     ▲ │                                  ▲ │                                       │
     └─┘ retract drops count<2            │ └─ signal event on resolved pattern     │ resolved event,
         (fold: fixable→casual)           │    = REGRESSION: resolved→fixable        │ or close=completed
                            promote ──────┘                                          ▼
                            (override event)                                     resolved
```

Every state is re-derived by `fold()` from the log on each `rebuild` — **nothing is carried
forward out-of-band**. Forbidden move enforced in `next_status`: a recomputed `fixable` never
demotes an `issued` pattern (which would re-file a duplicate); only an explicit close/resolve or
a regression moves it. A signal event landing on a `resolved` pattern re-opens it as a
regression, surfaced prominently in the recap (this is the "no regression in a follow-up
session" acceptance criterion, §6, firing). `loop resolve` legal only on `issued`/`fixable`;
resolving a `casual` is a no-op with a warning.

> **GitHub-down safety.** Wrap-up runs in two phases under the store lock: **(1)** dedup all
> patterns via live search, **(2)** for each needing an issue: create → append `issue_filed` →
> next. If any *search* in phase 1 fails, abort phase 2 with a non-zero exit and "GitHub
> unreachable — recap written, 0 issues created, rerun later" — a failed search is **never**
> read as "safe to create." The per-item create→append barrier means a mid-batch crash leaves a
> consistent partial state a rerun completes. Idempotency comes from this barrier, not from the
> search call alone.

Implementation notes: `typer` for the CLI (clean type-hinted commands), `pydantic`
models in `core/models.py` (consistent with your stack), no network calls outside
`adapters/github.py`. Secrets (GitHub token) come from env vars only.

---

## 8. Growth path: CLI → FastAPI

Because all logic lives in `core/`, the service is a thin second adapter:

```python
@router.post("/events")
def log_event(p: EventIn) -> EventOut:                  # one call into core.loop
    return to_out(core.loop.record_event(store, to_draft(p)))
@router.post("/sessions/{sid}/wrap-up")
def wrap_up(sid: str, repo: str) -> WrapUpReport:       # one call; gateway injected
    return core.loop.wrap_up(store, GithubGateway(repo), sid)
@router.get("/patterns")
def list_patterns(status: str | None = None): ...
```

Both adapters cross **one seam each** into `core/loop`; orchestration
(store → classify → rollup → recap → dedup → issue) lives in core, not the handler, so the
FastAPI handler is the same thin shell as the CLI command. Same files, same functions, now
reachable over HTTP so your agents call it as a service.

> **Concurrency constraint.** Even the CLI is not safely single-writer — two agent sessions on
> one repo both shell out to `loop log`. So the store takes a cross-platform advisory file lock
> (e.g. `portalocker`; `fcntl` alone won't do on Windows) **now**, not at Phase 5. Because
> derived state has a single producer (§2), the locked region is just `EventLog.append()` — one
> `O_APPEND` line write — followed by an out-of-lock recompute-and-`os.replace` of the snapshot;
> a lost snapshot write is always recoverable by `loop rebuild`. **The JSONL append is the commit
> point; `patterns.json` is best-effort cache.** Move to SQLite if the log ever outgrows files.
> The pure core is unaffected — this is purely the store adapter's responsibility. Dockerise
> alongside your other services at Phase 5.

---

## 9. Future options (not in v1)

- **pgvector dedup.** Embed each event summary; when logging, surface "similar past
  events" so near-duplicate `pattern_key`s get merged automatically. Ties directly into
  your RAG roadmap.
- **Auto-implement agent.** A scheduled agent that pulls `fix:script` issues, opens a PR,
  and assigns the rest to you.
- **Metrics.** Recurrence-over-time chart per pattern — see whether fixes actually stop
  the bleeding.

---

## 10. Open assumptions to confirm

1. Code + issues live in `claude-config/self-improve/` (skills live there; `skill_edit`
   targets it per PROTOCOL §6). This design folder is the planning workspace — confirm the
   canonical home before pass 2, since the issue template (§6) hardcodes `self-improve/...` paths.
2. Python + `typer` + `pydantic` for the CLI — confirmed. `pydantic` models double as the
   FastAPI request/response types (§8), so the CLI→service seam reuses them for free.
3. Issues filed on `gweedo/claude-config` by default; `fix:script` issues may target the
   project repo where the code lives, via `--issue-repo` (§7).
4. Threshold = 2 occurrences; severity ceiling = 3. Tunable — but only meaningful once the
   `pattern_key` collision guardrail (PROTOCOL §5) is in place, since the count is only as
   trustworthy as the key.
5. `session_id = <YYYY-MM-DD>[-<slug>]`; recap path is `sessions/<session_id>.md` so same-day
   sessions don't collide. A session is a unit of work the agent declares, not a calendar day;
   the date prefix is "when it started," the authoritative time is each event's UTC `ts`. Wrap-up
   **overwrites** the recap (a pure render of the session view), consistent with idempotency.

---

## 11. Testing strategy

**Test the seams; mock only the boundary.** The refactor makes almost everything reachable
without a mocking library — pure functions are tested directly; use cases run against a real
`EventLog` on `tmp_path` and a `FakeIssueGateway`; only `adapters/github.py` gets a transport
stub (`respx`/`responses`). `FakeIssueGateway` implements the port with an in-memory issue list
and a `search(label, marker, state)` the idempotency tests drive. Inject `clock()`/`id_factory()`
so events are byte-stable.

The two guarantees that **must** have a test:

1. **Wrap-up idempotency** (`test_loop.py`) — run `wrap_up` twice on a session; the fake's
   `search` returns the open issue on the second pass → **0 duplicate issues**. Variants: fake
   reports the issue `state:closed` → re-files (proves dedup keys off live state, not the cache);
   `--dry-run` → 0 created, report still lists the planned issue.
2. **`patterns.json` is fully rebuildable from `events.jsonl`** (`test_fold.py`) — `fold` over a
   log containing `override`/`tombstone`/`issue_filed`/`resolved` reconstructs `status`,
   `issue_url`, counts exactly; a second rebuild is identical (idempotent); a `tombstone` of a
   `tombstone` reinstates; a signal event on a `resolved` pattern yields `fixable` (regression).

Other P0/P1 tests: `classify` four corners (count 1↔2 × sev 2↔3); `suggest_keys` reject-unknown +
3-closest; `build_issue` marker + label mapping + secret-scrub refusal; `build_recap` renders a
fixed `SessionView` and **re-derives nothing** (feed deliberately "wrong" counts → rendered
verbatim, locking the rule out of the renderer); `github.py` contract (query built with the right
label+marker, parses `state:open`).

**TDD order — vertical slices, not horizontal.** Build the tracer bullet first
(`record_event` → append → `classify` → returned verdict), then grow one test → one behaviour:
store round-trip, fold corrections, recap, guardrail, wrap-up idempotency, GitHub contract last.
Don't write all eight test files up front.
