# Retro — day-trader-skill session (2026-11-15)

Matt Pocock's `retro` skill: improvements to the agent's **environment**, most severe first.

1. **Automated checks — no test guardrail in this repo.** `.github/workflows/` runs only
   `claude-review` and `claude`; nothing runs `pytest` for `experiments/day-trader-backtest`
   (40 tests) or `self-improve/`. A broken harness would merge silently. Fix: one CI job
   running each Python project's tests (`./fetch_skill.sh` first for this one).

2. **Information access — no market data host.** The real question ("can it profit?") needs
   contiguous historical bars; Yahoo was refused by the egress proxy, so the session could
   only test synthetic data. Fix: an environment that allows one data host (e.g.
   `data.alpaca.markets`) plus a key via the credential form, or a committed/cached dataset.

3. **Navigation — Matt Pocock's skills weren't loadable.** They're in the `skills-install`
   registry, but `skills/` is gitignored and nothing installs them in cloud sessions, so the
   agent had to clone `mattpocock/skills` and follow `SKILL.md` files by hand instead of
   invoking them. Fix: run `skills-install` from the environment's setup script.

4. **Tool economy — `/security-review` can't review a third-party repo.** It shells out to
   `git diff origin/HEAD...` in the working repo and errored on the scratch clone; the review
   was redone by hand. Fix: a small "audit an external repo" skill (clone pinned → read →
   SkillSpector static → manual pass on side-effect paths), reusing the memory note's method.

5. **Coding standards (judgement) — TDD slices that pass on first run.** Two S3 tests passed
   immediately because the pipeline code was written ahead of them; they were validated by
   inspecting the skill's real messages, but strict red-before-green was broken. Reviewer
   rule: a new test that never failed must be shown to fail against a deliberate mutation.

6. **Navigation — `CONTEXT-MAP.md` doesn't list `experiments/`.** Add one row pointing at
   `experiments/day-trader-backtest/README.md` so future sessions find the harness and results.
