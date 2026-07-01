# Retrospective — MVP-appropriate cost review of the live infra — 2026-06-29

This is the follow-up promised in
[`retrospective-infra-cost-overprovisioning-2026-06-25.md`](retrospective-infra-cost-overprovisioning-2026-06-25.md)
(action item #4: "run a one-pass cost review of the candidates with the MVP-appropriate
lens"). Where that retrospective was reactive — a large fixed cost discovered from the bill —
this one is the deliberate pass it called for.

## What we did

Read the actual SKUs out of `infra/` (not estimated from memory) and built a per-resource,
per-environment monthly cost picture for the live footprint across **staging** and
**production**. Sources: `infra/modules/*.bicep` and `infra/parameters/{staging,production}.bicepparam`.

## Findings — current cost picture

Italy North / global list prices, USD. Two environments stamped from the same Bicep, plus
**one shared ACR** (production reuses staging's registry — `deployAcr = false`).

| Resource | SKU / config (from Bicep) | Est. $/mo per env |
|---|---|---|
| Front Door | `Standard_AzureFrontDoor`, 1 profile/env | ~$35 (flat base fee) |
| Container Apps | 2 apps, 0.5 vCPU / 1 GiB, **minReplicas: 1** | ~$25–40 (always-on idle baseline) |
| PostgreSQL Flexible | `Standard_B1ms` Burstable, 32 GB, no HA, no geo-redundancy | ~$15–20 |
| Log Analytics + App Insights | `PerGB2018`, 30-day retention | ~$0–10 (first 5 GB/mo free) |
| Storage | `Standard_LRS` Hot, images only | ~$1–2 |
| Key Vault | Standard | <$1 |

Shared ACR Basic ≈ $5/mo total.

- **Production alone:** ~$80–105/mo
- **Both environments running 24/7 + shared ACR:** ~$165–215/mo

The two dominant, traffic-independent costs are **Front Door** (a flat ~$35 you pay even at
zero traffic) and the **Container Apps idle baseline** (you pay for `minReplicas: 1` even
when nothing is being served). Everything else is already minimal.

## What we confirmed is already well-sized

The earlier retrospective flagged four candidates "not yet audited". Verdicts:

- **PostgreSQL** — `Standard_B1ms` is the cheapest Burstable tier; HA and geo-redundant backup
  are off. Appropriate for v1. No change to the SKU.
- **Log Analytics / App Insights** — `PerGB2018` with 30-day retention sits inside the 5 GB/mo
  free grant at blog-scale volume. No change.
- **Storage** — `Standard_LRS` Hot, images only. Negligible. No change.
- **Container Apps sizing** — 0.5 vCPU / 1 GiB is right; the lever is `minReplicas`, not the
  per-replica size (see below).

So the over-provisioning was isolated to Front Door (already fixed in ADR-0015). The remaining
savings are about **staging not needing to look like production**, not about wrong SKUs.

## Decisions → issues filed

Tracked under **#71** (cost-optimization initiative). Each is an independently deployable
Bicep/CI change:

1. **#72 — Front Door optional per-env; off on staging** (~$35/mo). Staging is reachable on the
   Container App's `*.azurecontainerapps.io` FQDN with managed TLS; it does not need the custom
   domain, `.eu→.it` redirect, or edge WAF.
2. **#73 — Parameterize `minReplicas`; staging → 0** (~$25–40/mo). Production stays at 1 (no cold
   starts for visitors); a deploy-verify environment tolerates a cold start.
3. **#74 — Stop/pause staging PostgreSQL when idle** (~$13/mo compute; storage retained).
4. **#75 — Ephemeral/teardownable staging** (up to ~$80/mo). Aggressive; overlaps #73/#74 — pick
   one strategy. The shared ACR must be excluded from the teardown blast radius.
5. **#76 — Azure Cost Management budget + alert per resource group** (free). The control that
   would have caught the original overspend in week one.

**Realistic target:** #72 + #73 land both environments at roughly ~$120–140/mo. Adopting #75
(ephemeral staging) brings steady-state down to roughly production-only (~$80–105/mo).

## Lessons (reinforcing, not new)

- The earlier process lesson held: the only real overspend was the one without a cost line
  attached at decision time. The audited resources that *did* match their stated v1 requirement
  were all correctly sized.
- **"Staging mirrors production" is a cost decision, not a default.** The cheapest staging is one
  that is smaller than prod, scales to zero, or doesn't exist between deploys. Mirroring prod
  exactly doubled every fixed cost for no verification benefit.
- A budget+alert (#76) converts "audit the bill periodically" into "get told at 50%." That should
  exist before, not after, the next SKU decision.

## Action items

1. [x] Run the MVP-appropriate cost review of the flagged candidates (this document).
2. [ ] Land #72–#76 (tracked under #71).
3. [ ] After changes land, record the new steady-state cost in #71 and the infra guide.
4. [ ] Still open from the prior retrospective: add an "Est. monthly cost" line to the infra ADR
   template and backfill ADRs 0004/0005/0010/0013.
