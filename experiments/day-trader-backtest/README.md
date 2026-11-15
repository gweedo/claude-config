# day-trader-backtest

Offline experiment: does [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
(pinned to the reviewed commit `3d0f4ef`) make money, and does it behave safely?

- **Findings:** [RESULTS.md](RESULTS.md)
- **Security review of the skill:** [`memory/day-trader-skill-security-review.md`](../../memory/day-trader-skill-security-review.md)
- **Claude-driven run protocol and grading key:** [CLAUDE_RUN.md](CLAUDE_RUN.md)

Built with Matt Pocock's skills: `grilling` to settle the design (decisions below),
`tdd` to build the harness one test at a time at agreed seams, `retro` at the end.

## Run it

```bash
./fetch_skill.sh                                  # clones the skill at 3d0f4ef into .vendor/ (gitignored)
uv venv .venv && VIRTUAL_ENV=.venv uv pip install pytest
.venv/bin/pytest -q                               # 40 tests, < 1 s
.venv/bin/python run_grid.py                      # full grid + time machine calibration, ~2 min -> out/
.venv/bin/python build_claude_run.py              # sandbox for the Claude-driven run -> out/claude-run/
```

No network needed after the fetch: everything runs on synthetic sessions and the skill's
bundled fixtures. Nothing here can place an order.

## Design decisions (grilling rounds 1–2)

| # | decision |
|---|---|
| Q1 | Answer both "does it behave" and "how much would it make", labelling synthetic P&L as not evidence of a real edge |
| Q2 | In the loop: entry → exit → budget → risk; time machine on a ~50-trade sample; plus a 10-day Claude-driven run. Out: scanner (single symbol), broker (simulated fills), alerts, news/analyst/pelosi |
| Q3 | Opening-range breakout, long only, 27 variants: range 5/15/30 min × stop or-mid/or-low/1.5×ATR × target 1/1.5/2R |
| Q4 | 8 scenarios × 250 days, fixed seeds: trend up/down, choppy, gap up/down, crash, quiet, bootstrap of real TSLA bars |
| Q5 | Buy at next bar's open + 0.02 % slippage, no commission; stop fills at stop or a worse gap open; stop and target in one bar = stop |
| Q6 | $5,000 account, $50 max loss per trade, one trade a day, the skill's own risk limits |
| Q7 | Control: random entry time with the same target, sizing and risk checks, and the same stop *distance* |
| Q8 | Code here; the skill fetched pinned, not vendored |
| Q9 | Run the skill's Python offline, pinned to the reviewed commit |
| Q10 | Test seams: S1 generator, S2 fill simulator, S3 one day through the pipeline (anchored on the README's TSLA trade), S4 statistics, S5 end-to-end smoke |
| Q11 | Call the skill's functions directly; S3 proves parity with the CLI numbers |
| Q12 | Claude-driven run in a sandbox with a scripted user and traps |

## Layout

| path | what |
|---|---|
| `dtbt/skill.py` | loads the pinned skill's tools as modules |
| `dtbt/generator.py` | S1: synthetic sessions (scenario table in its docstring) |
| `dtbt/fills.py` | S2: bar-by-bar bracket fill simulator |
| `dtbt/pipeline.py` | S3: `run_day` — the skill's entry/exit/budget/risk + fills |
| `dtbt/metrics.py` | S4: win rate, avg R, P&L, drawdown |
| `dtbt/runner.py` | S5: ORB arm vs random-entry control |
| `run_grid.py` | the full experiment and the time machine calibration |
| `build_claude_run.py` | the Claude-driven run's sandbox |
