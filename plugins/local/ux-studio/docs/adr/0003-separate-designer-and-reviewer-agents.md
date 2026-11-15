# Separate Designer and Reviewer agents

Building and judging UI are split into two agents. A subagent cannot spawn another
subagent, so a single agent would always critique screens with its own reasoning in
view, and self-review bias ("looks great") is how UI work fails. The Reviewer sees
only the running page and the brief. The cost is that the calling session runs the
build → review → fix loop and the Reviewer re-reads the page from scratch. The
Designer keeps a Smoke check so obvious breakage never reaches review.
