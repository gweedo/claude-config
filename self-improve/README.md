# self-improve

A portable, git-tracked memory that turns the mistakes an AI agent makes during real
work into well-formed GitHub issues — but only the **systematic** ones, and only with
your approval.

It lives inside the `claude-config` repo as one self-contained project. The agent you're
already working with is the sensor: it spots a mistake, flags it inline, you approve, and
a small CLI records it. Over time the loop learns which mistakes recur and promotes those
into issues a later pass implements. It never edits your code or skills directly — it's
advisory.

## The 30-second mental model

```
        during a working session                    at "wrap up"
  ┌───────────────────────────────────┐    ┌────────────────────────────┐
  │  agent works on a task            │    │  loop wrap-up              │
  │      ▼ spots one of 4 signals     │    │    • recompute statuses    │
  │  flag inline ──► you approve ─────┼──► │    • write session recap   │
  │      ▼                            │    │    • file GitHub issues    │
  │  loop log ──► events.jsonl        │    │      for fixable patterns  │
  │             patterns.json (cache) │    └────────────────────────────┘
  └───────────────────────────────────┘
```

Three ideas do all the work:

1. **The agent is the sensor.** No daemon, no magic. Whatever agent is working follows
   `docs/PROTOCOL.md` and flags one of four signals (code failure, misunderstood intent,
   wrong approach, repeated correction). That's what makes the loop tool-agnostic.
2. **Recurrence + severity is the brain.** A one-off stays `casual` and just accrues a
   count; the second sighting (or a severity-3) promotes it to `fixable`. The system
   *learns* what's systematic instead of guessing on day one.
3. **The append-only log is the single source of truth.** `patterns.json` is a provable
   cache — `fold(events)` is its only producer, so it can never desync. Delete it and
   `loop rebuild` reconstructs it exactly.

## Run it

```bash
cd self-improve
python -m pytest                 # 33 tests, no third-party install needed
python -m siloop.cli.main --help # the `loop` CLI

# a real session, end to end:
export GITHUB_TOKEN=$(gh auth token)
python -m siloop.cli.main log --type wrong_approach --pattern infra-leak-in-app ...
python -m siloop.cli.main wrap-up --session 2026-06-20-ski --repo gweedo/claude-config --dry-run
```

Full command reference: `docs/PROTOCOL.md` §8.

## Status

Design ✅ · implementation ✅ (pure core + CLI + GitHub adapter, 33 green tests) · the
next milestone is the **first real run** against an actual working session. Living detail
and roadmap: **`docs/STATUS.md`**.

## Which doc answers which question

| You want to… | Read |
|---|---|
| Understand what this is and how to run it | this README |
| Know the rules the **agent** follows during a session | `docs/PROTOCOL.md` |
| Understand the **architecture** and data model | `docs/DESIGN.md` |
| Look up a term (`verdict` vs `status`, `pattern_key`, `fold`…) | `docs/GLOSSARY.md` |
| See current state, gaps, and next steps | `docs/STATUS.md` |
| Know how the shipped code deviates from the design | `docs/IMPLEMENTATION_NOTES.md` |
| See the review process that hardened the design | `docs/reviews/` |

## Layout

```
self-improve/
├── README.md          # you are here
├── docs/              # PROTOCOL · DESIGN · GLOSSARY · STATUS · IMPLEMENTATION_NOTES · reviews/
├── siloop/            # the package: core/ (pure logic) · cli/ · adapters/
├── tests/             # the DESIGN §11 suite
└── pyproject.toml
```

`siloop/core/` is pure (no I/O); persistence, network, and pattern-matching sit behind
ports so the same use cases drive the CLI today and a FastAPI service later. That
separation is deliberate — see `docs/DESIGN.md` §2 for why.
