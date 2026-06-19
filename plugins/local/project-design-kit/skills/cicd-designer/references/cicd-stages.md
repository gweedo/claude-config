# CI/CD Stage Decision Menus

For each stage: the options, the trade-off axis, and a sensible default for a small team / MVP that should scale. Adapt to the project's platform and constraints.

## 1. Branching & deploy triggers
- **GitHub Flow** *(default)* — one deployable `main`, short-lived feature branches, PR checks. Low ceremony, always-deployable main; the PR is where gates enforce quality.
- **Git Flow** — `main`+`develop`+`release/*`+`hotfix/*`. For scheduled, multi-team, versioned releases. Heavy for a small team.
- **Direct-to-main** — fastest, but no PR gate (discards the checkpoint that makes test/scan gates enforceable).
- **Triggers (default):** PR → checks only; merge to main → deploy staging; production via **manual approval** (environment protection), restricted to main/tags. Alternatives: release-tag trigger; auto-promote after staging checks.

## 2. Tests & coverage gate
- **Tiered** *(default)* — fast tests (unit + application + frontend-unit) and integration on every PR with a coverage gate before build; slow **E2E** post-deploy on staging as the promotion gate. Balances feedback speed and safety.
- **Everything on every PR** — safest, slowest/flakiest PR feedback.
- **Minimal on PR** — only unit gates PRs; integration/E2E pre-deploy. Fast PRs, late breakage.
- **Coverage gate (default):** ~80% overall, with pure/core layers near 100%; hard-fail before image build.

## 3. Security & supply chain
- **Dependency audit** (language audit tools + a bot that opens bump PRs) — cheap, high value.
- **Secret scanning** (diff scan + push protection) — cheap, high value.
- **Container image scan** (e.g. Trivy / cloud-native scanner) — catches OS/lib CVEs in the image.
- **SAST** (e.g. CodeQL) — static analysis of your code; easy if platform-native.
- **Blocking policy (default):** block on **high/critical** only; lower severities report. Defer SBOM + build provenance/attestation.

## 4. Image build & tagging
- **Immutable SHA (+ semver on release)** *(default)* — every image tagged by commit; deploy by digest; perfect traceability and clean rollback. Add a human-readable semver on releases.
- **Semver only** — release-versioned; in-progress builds lack distinct images.
- **Moving tags (`latest`/env names)** — convenient but ambiguous; anti-pattern for prod.
- Always: **multi-stage Dockerfiles** + a **registry retention/cleanup** policy.

## 5. Environments, auth & secrets
- **Separate staging + production** *(default)* — stamped from the same IaC with different parameters.
- **CI→cloud auth:** **OIDC / federated identity** *(default)* — short-lived tokens, no stored cloud secret, scoped per repo/branch/environment — vs a long-lived stored service-principal/access-key secret.
- **Runtime secrets:** **vault references via workload identity** *(default)* — the app reads secrets directly from the secret manager using its cloud identity; values never touch CI — vs injecting values at deploy time.
- **Environment protections:** required reviewer on prod; restrict prod deploys to main/tags.

## 6. Database migrations
- **Dedicated job, before traffic shift** *(default)* — run migrations as an explicit, ordered, rehearsed-on-staging step before the new version takes traffic.
- **On startup** — simple, but replica races and crash-loops on failure.
- **Manual** — error-prone; breaks automation.
- **Safety pattern:** **expand/contract + roll-forward** *(default)* — additive, backward-compatible changes so the previous version still works; rollback = redeploy previous image, no DB downgrade — vs lossy down-migrations.

## 7. Deployment / release strategy
- **Blue-green** *(default for most)* — deploy new ("green") at 0% traffic, verify, flip 100%; instant rollback to the warm previous ("blue"). Cheap if the platform does traffic-weighted revisions.
- **Canary** — gradual-% real traffic with metric-based advance/rollback. Higher value under real load, but needs traffic volume + automated metric analysis; often **phase 2**.
- **Rolling** — simplest; new replaces old; no warm standby, so rollback is a cold redeploy.

## 8. Post-deploy verification & rollback
- **Gate the cutover** with: health/readiness probe (always) + **smoke tests** against the new version; run **full E2E on staging** rather than re-running on prod.
- **Rollback trigger:** **manual, alert-driven** *(default to start)* — instant revert to the warm previous version, driven by error-rate/latency/health alerts — vs **automated rollback** on tuned thresholds (adopt once metric baselines exist; keep manual as fallback).

## Pipeline hygiene (apply by default)
Dependency + layer caching; concurrency cancellation of superseded runs; failure/deploy notifications.
