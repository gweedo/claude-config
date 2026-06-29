# Subagent delegation with phase-gated, PR-reviewed orchestration

The Orchestrator delegates to the six role agents as **native Claude Code
subagents** (via the Agent tool), each running in its own isolated context. This
is the keystone: because subagents don't share context, the **Context graph is
their shared memory** — which is precisely why the durable Memory service
(ADR-0001/0002) has to exist. A single agent "wearing hats" was rejected for
exactly this reason: it would leave the Memory service without a purpose.

Control flow is **plan-gated with per-phase checkpoints**: the Orchestrator
proposes a plan the user approves, executes one Phase autonomously (fanning out to
role agents), flushes the phase's triples to memory, and pauses. Fully autonomous
and step-per-delegation flows were rejected as too loose / too noisy.

Each completed Phase lands as commits on a **GitHub PR**. Review is a **mode of
the Architect and Tester** (not a separate role): the Architect reviews
design/structure, the Tester reviews coverage/correctness, both comment on the PR
and write issues found into the graph. The **user holds final merge approval**.

## Consequences
- Phase boundaries are the canonical memory-write points.
- Role agents must reuse existing repo skills rather than re-derive workflow
  (Developer→`implement`/`tdd`, Tester→`tdd`/`diagnosing-bugs`,
  Architect→`codebase-design`/`project-design-kit`,
  Infrastructure→`devcontainer-tools`/`cicd-designer`, PM→`to-prd`/`to-issues`,
  Domain Expert→`domain-modeling` + `domain-expert.md`).
