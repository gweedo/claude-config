# TDD / Testability Review — Self-Improvement Loop

Reviewed: `PROTOCOL.md`, `DESIGN.md` (post-refactor). Lens: testability and the
test strategy the design should commit to.

**Verdict:** the refactor moved the design from "hard to test" to "mostly a pure-function
test suite plus two fakes." The seams are right. The only structural gap is that
`pattern_key` similarity-matching and the *live-search dedup policy* have no named home in
the test list, and DESIGN §3 lists three test files that don't cover the highest-risk
behaviour (idempotency, rebuild folding, the GitHub adapter contract).

---

## 1. Seams: what is unit-testable now, and what is still hard

### Good seams (the wins from the refactor)

| Seam | Why it makes testing easy |
|---|---|
| `IssueGateway` port (injected into `wrap_up`) | Network is behind a Protocol. A `FakeIssueGateway` (in-memory list + `search`) lets you test dedup and idempotency with **zero** HTTP and zero mocking framework. This is the single most valuable seam in the design. |
| `EventLog` store (`append`/`rebuild` the only writers) | One narrow write surface. Point it at a temp dir / `tmp_path` and you get a real round-trip test of the source of truth without touching the user's real log. |
| Pure `classify(event, count)` | No I/O, total function of two inputs. Boundary tests are trivial and fast. |
| Pure `build_recap(view)` over a `SessionView` | Rendering is decoupled from rule evaluation — you can feed a hand-built `SessionView` and assert on markdown without running the classifier, the store, or counts. |
| Pure `build_issue(pattern)` | Payload construction is data-in/data-out; assert the marker comment and labels directly. |

The split "pure functions vs `core/loop` use cases vs adapters" means **almost everything
worth testing is reachable without mocks** (per `mocking.md`: mock only at boundaries —
here the only boundary is `IssueGateway`).

### Where testing is still hard (call these out in DESIGN)

1. **`adapters/github.py` has no seam below it.** It *implements* `IssueGateway` but talks
   to real GitHub. It is the one place a fake can't help. DESIGN currently lists **no test
   for it at all**. It needs a contract/integration test (recorded HTTP or a `respx`/
   `responses`-style transport stub) — otherwise the marker-comment + `state:open` search
   logic, which the entire dedup guarantee rests on, is completely unverified.

2. **The dedup *policy* lives in `core/loop.wrap_up`, not in `issues.py`.** Good for purity,
   but it means the policy is only testable *through* `wrap_up` with a fake gateway. That's
   fine and intended — but the design should say so explicitly so nobody is tempted to push
   the policy back into `issues.py` (which would make it require the network to test).

3. **`pattern_key` reject-unknown guardrail (PROTOCOL §5) has no home in the layer map.**
   "Normalized string distance, show 3 closest, `--new-pattern` to override" is real logic
   with real boundary behaviour (exact match, near-match rejected, `--new-pattern` accepted).
   DESIGN doesn't name the module (suggest `core/patterns.py` or a pure `suggest_keys(key,
   known)` in `classify.py`/its own file) and §3 has no test for it. As written it risks being
   implemented inside the CLI adapter, where it is hard to test. **Pull it into a pure
   function and test it directly.**

4. **Time / UUID / "now" are implicit.** `Event.ts`, `id` (uuid4), and `first_seen/last_seen`
   are non-deterministic. Nothing in the design says how they're injected. Per `mocking.md`,
   time and randomness are boundaries — `record_event` should take a `clock`/`id_factory`
   (or the store should), or recap/round-trip assertions become flaky string matches.
   **This is the one refactor-for-testability item that isn't yet in the design.**

5. **`loop resolve` / wrap-up reconciliation of `issued`→`resolved`** (status carried from
   *live issue state*, not re-derived by rebuild) couples two sources of truth. It's testable
   via the fake gateway, but it's subtle enough to deserve its own named test.

---

## 2. Highest-value tests (prioritized)

Ordered by risk × likelihood-of-regression. P0 = must exist before pass-2 code is trusted.

### P0 — core correctness & the two guarantees the docs promise

**T1. `classify` boundary cases** (pure, `test_classify.py`)
- count 1, sev 1 → `casual`
- count 1, sev 2 → `casual`  *(the 2-vs-3 severity boundary: sev 2 is NOT auto-fixable)*
- count 1, sev 3 → `fixable`  *(severity ceiling fires on a one-off)*
- count 2, sev 1 → `fixable`  *(recurrence promotes; the 1→2 boundary)*
- count 2, sev 3 → `fixable`  *(both conditions true — no double-counting weirdness)*
- Pin the tie-breaker intent: a sev-2 second sighting is fixable *by recurrence*, a sev-2
  first sighting is not. These four corners are the whole rule.

**T2. EventLog append + rebuild round-trip** (`test_store.py`, `tmp_path`)
- `append(e1); append(e2)`; new `EventLog` over the same path; `rebuild()` → `patterns.json`
  reflects count=2, correct `max_severity`, `first_seen`/`last_seen`, `event_ids` in order.
- Asserts the source-of-truth invariant: patterns.json is fully derivable from the JSONL.

**T3. rebuild folds `override` and `tombstone` correctly** (`test_store.py`) — *missing today*
- tombstone: log event → tombstone it → rebuild → pattern count drops it; if it was the only
  event, pattern count is 0 / pattern absent.
- override (promote): casual pattern (count 1, sev 1) → `override` event pinning `fixable`
  → rebuild → status is `fixable` and **survives** a second rebuild (the "survives rebuild"
  claim in DESIGN §4.1 / §7).
- order independence: a tombstone appended after later events still removes exactly the target.

**T4. `wrap_up` idempotency with a `FakeIssueGateway`** (`test_wrap_up.py`) — *missing today*
- Arrange a fixable pattern, no open issue. Run `wrap_up` → fake records 1 created issue,
  pattern → `issued` + `issue_url`.
- Run `wrap_up` **again** on the same session → fake's `search` returns the open issue →
  **0 new issues created.** This is the headline guarantee in PROTOCOL §7 and DESIGN §6.
- Variant: fake reports the issue `state:closed` (manually closed) → wrap-up **re-files**
  (proves dedup keys off live `state:open` search, not the stale `issue_url` cache).
- Variant: `--dry-run` → 0 issues created, report still lists the *planned* issue.

### P1 — rendering & the guardrail

**T5. `build_recap` from a fixed `SessionView`** (`test_recap.py`, pure)
- Feed a hand-built pre-classified `SessionView` (logged / promoted-to-issues / still-casual
  sections). Assert the markdown sections, the `(2×)` counts, the `→ issue #42` link.
- Negative assertion (locks the architecture): recap given a `SessionView` whose counts/
  classes are deliberately "wrong" still renders them verbatim — proving `recap.py`
  **re-derives nothing** (DESIGN §5). This test is what keeps the rule in one place.

**T6. `pattern_key` reject-unknown guardrail** (`test_patterns.py`, pure) — *missing today*
- exact existing key → accepted.
- unknown key with a near neighbour → rejected, returns the 3 closest by normalized distance.
- same unknown key + `--new-pattern`/`allow_new=True` → accepted.
- Test the pure `suggest_keys`/validation function, **not** through the CLI.

**T7. `build_issue` payload** (`test_issues.py`, pure)
- Asserts the hidden `<!-- self-improve:pattern={key} -->` marker (the dedup anchor),
  `self-improve` + correct `fix:*` label mapping per `fix_type`, and that provenance fields
  (event_ids, first/last seen) render. Cheap, and the marker is load-bearing for T4.

### P2 — adapter contract & end-to-end

**T8. `adapters/github.py` contract test** (`test_github.py`, recorded/stubbed HTTP) — *missing today*
- The dedup search query is built with the right label + marker and parses `state:open`
  correctly; create returns the issue URL. Use `respx`/`responses` so it stays offline in CI.
- This is the only test that needs a transport stub; everything above uses the fake.

**T9. `record_event` use-case happy path** (`test_loop.py`)
- `record_event(store, draft)` appends one event, bumps the count, returns the classification
  computed by `classify` (the same one §5 says is shown at log time). Injected clock/id so the
  written event is deterministic. Ties the store + classify seams together once.

---

## 3. Is DESIGN §3's test list sufficient? No.

DESIGN §3 lists exactly three: `test_classify.py`, `test_store.py`, `test_recap.py`.
They map to T1, T2, T5 — the *easy, pure* third of the plan. **The list omits every test that
covers a stated guarantee or the network seam:**

- **No idempotency test** (T4) — yet "wrap-up is idempotent" is asserted twice (PROTOCOL §7,
  DESIGN §6) and is the single most important behaviour. Untested headline guarantee.
- **No rebuild-folding test** (T3) — `override`/`tombstone` folding is the most intricate
  pure logic in the system and is asserted to "survive a rebuild." `test_store.py` as named
  could cover it, but §3 doesn't say it must.
- **No `issues.py` / `build_issue` test** (T7) — the marker comment underwrites dedup.
- **No `adapters/github.py` test** (T8) — the one networked module is entirely unverified.
- **No `pattern_key` guardrail test** (T6) — PROTOCOL §5 calls the count "the whole point of
  the loop"; the guardrail protecting it is untested.
- **No `record_event` / `wrap_up` use-case test** (T4/T9) — the orchestration layer the
  whole architecture exists to make testable has no listed test.

The current list tests the parts that were *already* easy and skips the parts the refactor
specifically made testable.

---

## 4. Recommended additions to DESIGN

### 4a. Replace §3's test stanza with the committed suite

```
    ├── tests/
    │   ├── test_classify.py     # boundary corners: count 1↔2, severity 2↔3 (T1)
    │   ├── test_store.py        # append+rebuild round-trip; override/tombstone folding (T2,T3)
    │   ├── test_patterns.py     # pattern_key reject-unknown + 3-closest suggestions (T6)
    │   ├── test_issues.py       # build_issue payload: marker comment + label mapping (T7)
    │   ├── test_recap.py        # render from a fixed SessionView; re-derives nothing (T5)
    │   ├── test_loop.py         # record_event + wrap_up use cases w/ FakeIssueGateway (T4,T9)
    │   └── test_github.py       # IssueGateway adapter contract, stubbed HTTP (T8)
    ├── tests/fakes.py           # FakeIssueGateway (in-memory create/search), fixed clock/id
```

### 4b. Add a "## 11. Testing strategy" section

Suggested content:

- **Test the seams, mock only the boundary.** Pure functions (`classify`, `build_recap`,
  `build_issue`, key-validation) are tested directly. Use cases (`record_event`, `wrap_up`)
  are tested against a real `EventLog` on `tmp_path` and a `FakeIssueGateway`. The *only*
  module that gets a transport stub is `adapters/github.py`.
- **`FakeIssueGateway`** implements the `IssueGateway` Protocol with an in-memory issue list
  and a `search(label, marker, state)` that the idempotency tests drive — no mocking library.
- **Determinism contract:** inject `clock()` and `id_factory()` into `record_event` (or the
  store) so events are reproducible; recap/round-trip tests assert on fixed values.
- **The two guarantees that MUST have a test:** (1) wrap-up idempotency — running twice
  creates no duplicate issue; (2) patterns.json is fully rebuildable from events.jsonl,
  including `override`/`tombstone` folding.
- **TDD order (vertical slices, not horizontal):** build the tracer bullet first —
  `record_event` → append → `classify` → returned classification (T9+T1) — then grow one
  test→one behaviour: store round-trip, tombstone, override, recap, guardrail, then wrap_up
  idempotency, then the github contract last. Do **not** write all seven test files up front
  (the skill's "horizontal slice" anti-pattern); each test should respond to what the prior
  implementation revealed.

### 4c. One refactor-for-testability change

Make non-determinism injectable. Right now `Event.ts`/`id`/`first_seen`/`last_seen` are
implicitly "now"/uuid4, which forces tests into brittle regex/`startswith` assertions or
freezegun-style patching. Add `clock: Callable[[], datetime]` and `id_factory: Callable[[],
str]` parameters (defaulting to the real ones) to `record_event` / the store constructor.
Cheap, and it turns the round-trip and recap tests from fuzzy to exact. This is the only
place the current design is still genuinely hard to test.

Everything else in the architecture is already shaped correctly for testing — the work is
in *naming the missing tests and the determinism seam*, not restructuring.
