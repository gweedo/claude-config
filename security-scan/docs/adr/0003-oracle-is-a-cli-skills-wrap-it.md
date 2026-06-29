# The Oracle is a CLI; skills wrap it

The Oracle is realized as a **Python CLI tool**, not a skill. It shells out to the
Engine (Trivy) plus the freshness source and emits **structured JSON on stdout**
(one normalized record per finding) and a **meaningful exit code** (`0` = no
blocking findings, non-zero = blocking).

Rationale: skills return prose to the model, which is the wrong primitive for
something agents must branch on deterministically — and the hook/routine must run
with **no model in the loop**. A CLI with a JSON+exit-code contract serves every
consumer: humans, models, and git hooks alike, and keeps the hard logic in
testable code rather than prose.

Layering:
- **Oracle (CLI)** — deterministic core; JSON + exit code.
- **Scanner, Definer (skills)** — thin, model-facing wrappers that invoke the CLI
  and interpret its output for the agent.
- **Hook, routine** — call the CLI directly. **Command** — calls the Scanner skill
  (or the CLI for a raw report).

Finding record shape: `{artifact, ecosystem, installed_version, fixed_version|null,
latest_version, cve_id, severity, fixable, class: blocking|advisory}`.
