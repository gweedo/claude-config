---
name: cicd-designer
description: >
  Design and document a CI/CD pipeline and deployment strategy stage by stage. Use when the user wants
  to design the pipeline (GitHub Actions, branching, tests, image tagging, secrets, migrations) or
  choose a release/rollback strategy (rolling, blue-green, canary). Decides one stage at a time, then
  captures the result in an ADR and expands the tech spec.
metadata:
  version: "0.1.0"
---

# CI/CD Designer

Design a delivery pipeline by deciding each stage deliberately, then record the result. CI/CD is a cross-cutting concern with many independent choices; resolve them one at a time so each is a conscious decision, not a default.

## Method

Run the stage-by-stage deep-dive (see `../design-workflow/references/decision-facilitation.md`):
for each stage, explain what it controls, lay out the realistic options with trade-offs tied to the project's constraints (team size, traffic, cost, risk tolerance), recommend one, and let the user decide. Log each decision. When all stages are decided, write one ADR (`adr-writer`) and expand the tech spec's CI/CD section (`tech-spec-writer`).

## The stages (decide each)

1. **Branching & deploy triggers** — GitHub Flow vs Git Flow vs direct-to-main; what triggers staging vs production; manual-approval vs tag vs auto-promote.
2. **Tests & coverage gate** — which tests run on PR vs post-deploy (tiering of slow integration/E2E); the coverage threshold and where it blocks.
3. **Security & supply chain** — dependency audit, secret scanning, SAST, container image scan; blocking policy (e.g. high/critical only); SBOM/provenance (usually deferred).
4. **Image build & tagging** — multi-stage builds; immutable SHA vs semver vs moving tags; deploy by digest; registry retention.
5. **Environments, auth & secrets** — separate environments; CI→cloud auth (OIDC federated identity vs stored secret); runtime secrets (managed-identity/vault references vs deploy-time injection); environment protection rules.
6. **Database migrations** — where they run (dedicated job before traffic vs on startup); safety pattern (expand/contract + roll-forward vs down-migrations).
7. **Deployment / release strategy** — rolling vs blue-green vs canary; map to the platform's traffic-shifting capability.
8. **Post-deploy verification & rollback** — what gates the production cutover (health, smoke, E2E); rollback trigger (manual alert-driven vs automated thresholds).

Full option menus, trade-offs, and default recommendations are in `references/cicd-stages.md`.

## Output

- One **ADR** (e.g. "CI/CD pipeline & deployment strategy") with a per-stage summary table plus deeper options analysis on the consequential stages (branching, deployment strategy, migrations, CI auth).
- An **expanded tech-spec CI/CD section** describing the concrete pipeline, plus a Mermaid pipeline diagram (see `../design-workflow/references/mermaid-snippets.md`).
- A starting workflow file from `templates/github-actions-deploy.yml.template`.

## Notes

- Tailor to the platform: the *concepts* (tiered tests, immutable tags, blue-green, expand/contract) are portable; the *mechanics* differ (e.g. Container Apps revision weights, Kubernetes Deployments, ECS services).
- Prefer the choices that make rollback trivial and keep secrets out of CI — they matter most for small teams.
