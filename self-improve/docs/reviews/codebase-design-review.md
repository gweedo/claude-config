# Codebase-Design Review — Self-Improvement Loop

Applying the **deep-module** lens (depth-as-leverage, seam placement, the deletion test,
"interface is the test surface," information leakage) to `DESIGN.md` §2–§8 and
`PROTOCOL.md` §8.

Scope: design only. No source files edited. Snippets below are *proposed* shapes, not
existing code.

---

## 1. Module-by-module assessment (deep vs shallow)

The layout proposed in `DESIGN.md` §3 is:
`core/{models,store,classify,recap,issues}.py` + `cli/loop.py` + `adapters/github.py`.

| Module | Interface size | Hidden complexity | Verdict |
|---|---|---|---|
| `core/classify.py` | tiny (`classify(event, count) -> Classification`) | the recurrence+severity rule, the two tunable constants | **Genuinely deep** in *logic density*, but **too small to stand alone as a module** — see §2.1. It is a pure function, not a module-shaped seam. |
| `core/models.py` | the data vocabulary | enum/validation | Correctly shallow-by-design (it *is* the interface — a vocabulary module). Fine. |
| `core/store.py` | "read/append events.jsonl, read/write patterns.json" | JSONL append semantics, derived-rollup recompute, the source-of-truth invariant | **Mis-shaped.** Bundles two responsibilities behind one name → information leakage + temporal coupling. See §2.2. This is the biggest issue. |
| `core/recap.py` | `build_recap(...) -> str` | grouping events by session, recomputing class, markdown rendering | **Risk of shallow.** If it only formats markdown it's a pass-through; the *recompute-at-wrap-up* logic (`DESIGN.md` §5 bullet 2) must live with it or in classify, not be re-implemented inline. See §2.3. |
| `core/issues.py` | `build_issue(pattern) -> IssuePayload` | template fill, label mapping, "skip if open issue exists" | **Half-deep.** Building the payload is real. But the "skip if an open issue already exists" rule (`PROTOCOL.md` §7.3, `DESIGN.md` §6) needs *network knowledge* (is there an open issue?) — that decision is currently homeless between `issues.py` (pure) and `adapters/github.py` (effectful). See §2.4. |
| `cli/loop.py` | the 5 commands (§7) | argparse/typer wiring only | Correctly **thin adapter** — *if* the core functions are shaped so the CLI is just parse→call→print. Today `wrap-up` would have to orchestrate store+classify+recap+issues+github itself, which makes it a fat adapter. See §2.5. |
| `adapters/github.py` | "the only place that talks to GitHub" | REST calls, auth, "find open issue by label/key" | **Deep and correctly placed** — this is the one true network seam. Good. The only worry is that `cli` and the future `fastapi` both construct it directly rather than receiving it (testability). See §2.4. |

### The named-but-missing module

`DESIGN.md` §2 advertises four core functions: `record_event`, `classify`, `build_recap`,
`build_issue`. But §3's file layout has **no `record_event` home** — `store.py` does the
appending and `classify.py` does classification, so `record_event` (the deep "log one
approved event and tell me its classification" operation, which is exactly what the CLI
`loop log` and the FastAPI `POST /events` both call) has no module. That function is the
*highest-leverage* interface in the whole system (it's the one both adapters share, §8),
and right now it's smeared across `store` + `classify`. **This is the central deepening
opportunity.**

---

## 2. Prioritized improvements

### 2.1 — P0: Give `record_event` and `wrap_up` real homes (a `service`/use-case layer)

**Weak now:** §2 promises `record_event()` and `build_recap()` as the core interface, but
§3 has no file that owns them. The CLI (§7) and the FastAPI router (§8) would each have to
re-orchestrate `store → classify → patterns bump → return classification`. That
duplicated orchestration is precisely what breaks the "thin second adapter" promise —
two adapters means a *real* seam (skill: "two adapters means a real one"), so the thing
behind the seam must be the **whole use case**, not the leaf functions.

**Apply the deletion test:** delete `cli/loop.py`. If the log-an-event orchestration
vanishes with it, it was living in the adapter — wrong. It should survive in core.

**Change:** introduce `core/loop.py` (or `core/service.py`) holding the use-case functions
that both adapters call. Leaf modules (`classify`, `recap`, `issues`, `store`) become its
*internal* parts, not the adapter's API surface.

Before (`DESIGN.md` §8) — the router reaches at leaf functions, implying the CLI does too:

```python
@router.post("/events")
def log_event(payload: EventIn) -> EventOut:        # wraps core.record_event
@router.post("/sessions/{sid}/wrap-up")
def wrap_up(sid, repo): ...                          # wraps core.build_recap + issues
```

After — both adapters cross **one** seam each; orchestration lives in core:

```python
# core/loop.py  — the deep interface both adapters share
def record_event(store: Store, draft: EventDraft) -> LoggedEvent:
    """Append an approved event, bump its pattern, return it WITH its classification.
       Owns the 'classify at log time with post-increment count' rule (DESIGN §5)."""

def wrap_up(store: Store, issues_gw: IssueGateway, session_id: str,
            dry_run: bool = False) -> WrapUpReport:
    """Recompute classes for the session, render the recap, decide which fixable
       patterns need new issues, create them via issues_gw. Returns a report."""
```

```python
# adapters: now genuinely thin
@router.post("/events")
def log_event(p: EventIn) -> EventOut:
    return to_out(core.record_event(store, to_draft(p)))
```

`record_event` and `wrap_up` are deep: a one-call interface hiding the
append-classify-rollup / recompute-recap-issue chains. The CLI and FastAPI become the
parse/serialize shells they were always meant to be.

---

### 2.2 — P0: Split `store.py` — it leaks the derived/source-of-truth distinction

**Weak now:** `DESIGN.md` §3 describes `store.py` as
*"read/append events.jsonl, read/write patterns.json."* That is **two modules wearing one
name**, and it leaks the system's core invariant across its own seam:

- `events.jsonl` is the **append-only source of truth** (§4.1).
- `patterns.json` is **derived and rebuildable** (§4.2: *"can always be rebuilt"*).

Putting both behind one `store` invites a caller to `write patterns.json` directly and
quietly violate "JSONL is the single source of truth." That's **information leakage** (the
derivedness must be known by every caller) and a latent **temporal coupling** ("append the
event, then remember to bump the rollup, in that order" — exactly the temporal-decomposition
smell). If a caller appends but forgets to bump, the invariant silently breaks.

**Change:** make the invariant *unbreakable by construction*. Two options, prefer (a):

(a) **One deep `EventLog` module; rollup is a private cache it owns.** Callers can only
append and query. There is no public "write patterns.json."

```python
# core/store.py
class EventLog:
    def append(self, event: Event) -> None:
        """Append to events.jsonl AND update the derived rollup atomically.
           Callers cannot do one without the other."""
    def count(self, pattern_key: str) -> int: ...
    def pattern(self, pattern_key: str) -> Pattern | None: ...
    def events_for_session(self, session_id: str) -> list[Event]: ...
    def rebuild(self) -> None:
        """Discard patterns.json, re-fold it from events.jsonl. The ONLY writer
           of patterns.json besides append()."""
```

The deletion test passes: delete `EventLog` and the "derived rollup stays consistent with
the log" guarantee disappears across every caller — so it's earning its keep.

(b) If you want patterns.json strictly as a cache, make `count()`/`pattern()` fold from
JSONL on read and treat patterns.json as an *optional* perf cache that `rebuild()` writes.
Then "derived" is true by construction — there is no way to desync because nothing trusts
the file as authoritative. Heavier on IO; defer unless the log gets large.

Either way, **remove "read/write patterns.json" from the public interface.** The only
public mutators become `append()` and `rebuild()`.

---

### 2.3 — P1: Pin the "recompute at wrap-up" rule in one place; keep `recap` a renderer

**Weak now:** `DESIGN.md` §5 says `classify` is called twice — at log time *and* again at
wrap-up "for every event in the session." If `recap.py` re-runs the classification loop to
render its `fixable (2×)` badges, the recurrence rule now has **two homes** (classify.py +
recap.py), and the `casual → fixable` promotion logic leaks into the renderer. That makes
`recap.py` accidentally deep in the wrong way (business logic hidden in a formatter) and
splits locality.

**Change:** Let `wrap_up` (§2.1) produce a fully-resolved, already-classified view object,
and let `recap.py` be a pure, dumb renderer of it. `recap` should not see counts or
thresholds at all.

Before (implied by §5 + §3): `build_recap` takes raw events and re-derives classes.

After:

```python
# core/loop.wrap_up builds this; classification already resolved here, once.
@dataclass
class SessionView:
    session_id: str
    logged:   list[ClassifiedEvent]   # each carries final classification + count
    promoted: list[PatternRollup]     # the ones that became issues
    watching: list[PatternRollup]     # still casual

# core/recap.py — provably shallow on purpose, and that's correct for a renderer
def build_recap(view: SessionView) -> str: ...   # markdown only, no rules
```

Now the recurrence rule lives **only** in `classify` (invoked by `wrap_up`), and `recap`'s
interface (a `SessionView` → string) is trivially testable without touching the store.

---

### 2.4 — P1: The "skip if an open issue exists" decision is homeless; inject the gateway

**Weak now:** `PROTOCOL.md` §7.3 / `DESIGN.md` §6 require: create an issue *only if no open
issue for that `pattern_key` already exists*. That decision needs a network fact ("is there
an open issue?") yet `issues.py` is declared pure ("no network here," §3). So the dedup rule
falls into a gap — it'll likely get hacked into the CLI's `wrap-up` handler, fattening the
adapter again.

Also, §8's router and §7's CLI both construct GitHub access directly. Per the skill
("accept dependencies, don't create them"), constructing the gateway inside core/adapters
makes `wrap_up` untestable without real HTTP.

**Change:** Define an `IssueGateway` *interface* (seam) and have `wrap_up` receive it. The
dedup rule lives in `wrap_up` (it's a use-case policy), expressed against the interface.
`adapters/github.py` is the real adapter; tests pass a fake — *two* adapters, so the seam is
real and justified.

```python
# core/ports.py
class IssueGateway(Protocol):
    def find_open_issue(self, pattern_key: str) -> IssueRef | None: ...
    def create_issue(self, payload: IssuePayload) -> IssueRef: ...

# core/loop.wrap_up (excerpt) — policy lives here, against the interface
for p in fixable_patterns:
    if issues_gw.find_open_issue(p.pattern_key):   # the §7.3 skip rule, in ONE place
        continue
    if not dry_run:
        ref = issues_gw.create_issue(build_issue(p))
        store.attach_issue(p.pattern_key, ref.url)  # writes back issue_url (§4.1/§4.2)
```

`issues.py` stays pure (`build_issue` → payload). `github.py` stays the only network code.
The "should I create this?" policy is no longer homeless. And `wrap_up` is unit-testable
with an in-memory `IssueGateway` fake — interface is the test surface.

---

### 2.5 — P1: Make `loop wrap-up` a thin call, not an orchestrator

**Weak now:** With the current §3 split, `cli/loop.py`'s `wrap-up` command must itself:
load store → recompute → render recap → write the .md → dedup issues → call github →
write back `issue_url`. That is a **fat adapter** doing domain orchestration — the exact
thing the core/adapter seam (§2) is supposed to prevent, and it would have to be *re-written*
in the FastAPI handler (§8). DRY violation across the seam = the seam is in the wrong place.

**Change:** Once §2.1 + §2.4 land, both adapters collapse to:

```python
# cli/loop.py
def wrap_up_cmd(session: str, repo: str, dry_run: bool = False):
    report = core.wrap_up(store, GithubGateway(repo), session, dry_run)
    print(render_cli(report))      # adapter-only concern: how to print
```

The only adapter-specific logic left is argument parsing and output formatting. That is what
"thin second adapter" (§8) actually requires.

---

### 2.6 — P2: `loop promote` mutates an append-only log — define the mechanism

**Weak now:** `PROTOCOL.md` §8 / `DESIGN.md` §7 offer `loop promote <event_id>`, but §4.1
says the log is **append-only** and "corrections are new events, never edits." Promotion is a
*correction*, so it must be a new event — but the data model has no event shape for "promote"
(no `promote` type, no link field). Undefined mechanism = it'll get implemented as an
in-place edit of `patterns.json`, breaking the source-of-truth invariant from §2.2.

**Change:** Model promotion as an appended override event, folded in by `rebuild()`:

```jsonc
// a promotion is itself an event, preserving append-only + rebuildability
{ "id": "...", "type": "override", "pattern_key": "missing-type-hints",
  "override": { "classification": "fixable", "reason": "security relevant" },
  "target_event_id": "..." }
```

`EventLog.append` and `rebuild` then know that an `override` event pins a pattern's class.
The invariant holds; promotion survives a rebuild; nothing edits a file in place.

---

### 2.7 — P2: Confirm the `record_event` return is the shared contract (it already is — keep it)

**Good now, protect it:** `PROTOCOL.md` §3.4 ("prints the resulting classification") and §8's
`POST /events -> EventOut` already agree that logging *returns the classified event*. That is
the correct deep contract and the linchpin of the CLI↔FastAPI symmetry. Keep `record_event`
returning the `LoggedEvent` (with classification + post-increment count) rather than `None` +
a side-effect — "return results, don't produce side effects." Just make sure §2.1's
`record_event` is the single definition both adapters import.

---

## 3. Summary of the seam map (target shape)

```
                 ┌──────────────────── core ────────────────────────────────┐
  adapters       │  loop.py  ─ record_event(store, draft) -> LoggedEvent     │
  ┌──────────┐   │            wrap_up(store, issues_gw, sid) -> WrapUpReport  │   ports
  │ cli/loop │──►│     internal parts (not the adapter's surface):           │  ┌──────────────┐
  │ fastapi  │──►│       classify · recap(SessionView) · issues(build_issue) │  │ IssueGateway │◄─ adapters/github.py
  └──────────┘   │     EventLog (store): append + rebuild only public writers│  └──────────────┘
                 └───────────────────────────────────────────────────────────┘
                         events.jsonl (source of truth) ──► patterns.json (derived cache)
```

**Three real seams** (each with ≥2 adapters or a guarded invariant, so each is justified):
1. `core.loop` ⟷ delivery adapters (CLI now, FastAPI later) — the §8 growth seam.
2. `IssueGateway` ⟷ `adapters/github.py` + test fake — the one network seam.
3. `EventLog.append/rebuild` ⟷ the JSONL/derived-cache files — guards the source-of-truth invariant.

**Net:** the design's instincts are right (pure core, single network seam, derived rollup).
The fixes are about *where the seams sit*: pull the two use-case functions
(`record_event`, `wrap_up`) into a core module so the adapters stay thin (P0); split `store`
so the derived/source invariant can't be violated by a caller (P0); demote `recap` to a pure
renderer and inject the issue gateway so wrap-up is testable (P1).
