# Decision Facilitation — the stage-by-stage deep-dive

A reusable technique for resolving a multi-part area (a stack, an architecture, a CI/CD pipeline) into a set of conscious, recorded decisions.

## The loop (one decision at a time)

For each open decision:

1. **Name what it controls.** One or two sentences on what this choice affects downstream. This frames why it matters.
2. **Lay out the realistic options.** Usually 2–4. For each, give the trade-offs tied to *this* project's constraints — team size and skills, time-to-launch, cost, scale, risk tolerance, compliance. Avoid generic pros/cons; make them specific.
3. **Recommend one, with a reason.** State a default and why it fits the constraints. Be honest if an option is suboptimal.
4. **Ask with a structured choice.** Offer the options as a multiple-choice question; let the user pick or override. Put the recommended option first and label it.
5. **Record the decision immediately** (decision-tracker), then move to the next.

Keep to one decision thread per step — don't stack many unrelated questions at once.

## Ordering

- Resolve **upstream** decisions first (ones others depend on). Note dependencies explicitly.
- If a choice is blocked on information someone else owns, capture it as an open question and move on.

## Handling answers well

- **Honor the choice, but stay honest.** If the user picks the non-recommended option, accept it and adapt — but make sure they saw the trade-off.
- **Watch for contradictions.** If two answers conflict (e.g. "do X now" + "X is phase 2"), surface the contradiction and re-clarify with one focused question rather than guessing.
- **Pause to explain on request.** If the user asks how something works before deciding, explain it plainly, then re-ask the decision.

## Synthesis (after the deep-dive)

When the area is fully decided:
- Write **one ADR** capturing the set: a per-stage/-decision summary table, plus deeper options analysis on the few most consequential choices, then trade-offs, consequences, and action items.
- **Expand the tech spec** section for that area to describe the concrete result, with a diagram where it helps (see `mermaid-snippets.md`).
- Add a summary entry to the **decision log** referencing the ADR.
- **Review for consistency** — make sure the new decisions don't contradict earlier docs; fix stale references.
