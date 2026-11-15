## Agent skills

### Issue tracker

Issues are tracked in this repo's GitHub Issues (`gweedo/claude-config`) via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary — `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: `CONTEXT-MAP.md` at the root points to per-context `CONTEXT.md` files. See `docs/agents/domain.md`.

### Default workflow for new work (always)

For any new feature, agent, skill or non-trivial change, use Matt Pocock's skills in this order. Don't skip a step because the work "looks small"; say so explicitly if the user waives one.

1. **`/grill-with-docs`**: interview the design to a shared understanding; glossary (`CONTEXT.md`) and ADRs are written as decisions settle.
2. **`/to-spec`**: synthesize the agreed design into a spec issue on the tracker (agree test seams with the user first).
3. **`/to-tickets`**: break the spec into tracer-bullet tickets with blocking edges; get the breakdown approved before publishing.
4. **`/tdd`**: implement each ticket red → green at pre-agreed seams; any code with logic (scripts included) gets tests.

If these skills aren't installed in the session, read them from `https://github.com/mattpocock/skills` (`skills/engineering/`) and follow them by hand rather than skipping them.
