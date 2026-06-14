---
name: requirements-questionnaire
description: >
  Use this skill to produce a stakeholder questionnaire that gathers product, content, or business input
  from non-technical teammates. Trigger phrases: "prepare questions for the team", "make a questionnaire",
  "I need to ask the stakeholders", "gather requirements from the content team", "what should I ask the
  business side", "PRD input form". Produces a fill-in document in the stakeholders' language whose
  answers feed a PRD.
metadata:
  version: "0.1.0"
---

# Requirements Questionnaire

When product/content/business facts are owned by people other than the builder, do not guess them — produce a clear questionnaire they can fill in, then turn their answers into a PRD.

## When to use

During the design workflow, whenever decisions depend on information only stakeholders have: what the product is for, who the audience is, goals/success metrics, content/format, tone/brand, timeline, and any domain specifics.

## How to write it

- **Match the audience's language.** If the stakeholders are non-technical and work in a given language, write the questionnaire in that language and avoid jargon.
- **Save to** `docs/product/<stakeholder>-questionnaire.md`.
- **Group questions into sections** and leave space to answer under each. Tell them short/bulleted answers are fine and "not applicable" is a valid answer.
- **Cover the gaps the PRD needs**, typically: the product in one sentence; the problem/mission; what makes it distinctive; the audience (who, where, how they discover it); goals and the #1 success metric; scope/feature priorities; tone/brand; timeline and dependencies; and an open "anything we didn't ask" question.
- **Keep it answerable in one sitting.** Prefer 4–8 focused sections over an exhaustive list.

## After answers arrive

- Map answers into a PRD at `docs/product/PRD.md`.
- Log any decisions the answers settle via `decision-tracker`, and clear the corresponding open questions.
- Anything still unanswered stays an open question — flag it, don't invent it.

See `templates/QUESTIONNAIRE.template.md`.
