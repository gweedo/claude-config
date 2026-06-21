# Self-Improvement Loop — pass-2 implementation

Implements the design in `DESIGN.md` / `PROTOCOL.md`. The pure core is the heart of
the system; everything else is a thin adapter around it.

## Layout

```
self-improve/
├── siloop/
│   ├── core/        # pure functions + use cases + store port
│   │   ├── models.py     # Event union (signal + override/tombstone/issue_filed/resolved), Pattern, enums
│   │   ├── classify.py   # classify(severity, count) -> Verdict   (DESIGN §5)
│   │   ├── status.py     # next_status(...) -> Status — the transition table (DESIGN §5/§7)
│   │   ├── fold.py       # fold(events) -> {pattern_key: Pattern}; the ONLY producer of patterns.json
│   │   ├── patterns.py   # suggest_keys / is_known — the PatternMatcher default (PROTOCOL §5)
│   │   ├── recap.py       # build_recap(SessionView) -> markdown (pure renderer, no rules)
│   │   ├── issues.py     # build_issue(...) -> IssuePayload + mechanical secret scrub (DESIGN §6)
│   │   ├── ports.py      # IssueGateway, PatternMatcher protocols
│   │   ├── store.py      # EventLog: read/append/write_snapshot — pure I/O (+ optional file lock)
│   │   └── loop.py       # record_event / wrap_up / rebuild — use cases both adapters call
│   ├── cli/main.py       # argparse adapter (thin) -> core.loop
│   └── adapters/github.py# IssueGateway impl via stdlib urllib + GITHUB_TOKEN
└── tests/                # DESIGN §11 suite; pure-core tests + wrap-up idempotency + lossless rebuild
```

## Deviations from DESIGN.md (small, intentional, reconcilable)

1. **Package wrapper `siloop/`.** DESIGN §3 draws `core/`, `cli/`, `adapters/` at the
   `self-improve/` root. Importing a top-level `core` would collide in a shared env, so
   they live under a `siloop` package. The subpackage names match the doc exactly.
2. **dataclasses, not pydantic (yet).** The pure core uses stdlib dataclasses + enums so
   it runs and tests with zero install on Python 3.8. pydantic models can wrap at the
   CLI/HTTP boundary in the FastAPI phase (DESIGN §8) without touching core.
3. **argparse CLI, not typer.** The CLI is a thin adapter; argparse keeps the tool
   zero-dependency. Swapping to typer later doesn't touch `core/`.

None of these affect the architecture the reviews hardened: pure core, single `fold`
producer, ports for network/matching, append-only log as source of truth.

## Status

Pure core + use cases + tests are implemented and green. The CLI and GitHub adapter are
runnable scaffolding; the GitHub adapter needs a live-token contract test (DESIGN §11 T8)
before production use.

## Run

```bash
cd self-improve
python -m pytest            # pure core + use-case tests (no install needed)
python -m siloop.cli.main --help
```
