# Cap the UX loop at two passes; file Leftovers to the project's tracker

The UX loop stops after two Review passes so the Designer and Reviewer cannot
ping-pong indefinitely. Findings stay in chat while the loop runs. Leftovers are
filed, after asking the user, to the target project's issue tracker as configured by
its `docs/agents/issue-tracker.md` and `triage-labels.md` (the Matt Pocock skills
setup), so they enter the normal triage flow instead of a ux-studio-specific file.
Filing happens in the `ux-loop` skill, not the Reviewer, which stays read-only.
