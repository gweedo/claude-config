# Retrospective — Infra over-provisioning & cost tracking — 2026-06-25

## What happened

While reviewing the Azure bill, the **Azure Front Door Premium** tier stood out as a large
fixed cost. Investigation (see [ADR-0015](docs/architecture/adr/0015-front-door-standard-tier.md))
found it was provisioned on **Premium** (~$330/month base fee) solely to host the
Microsoft-managed WAF rule set — which was running in **Detection (log-only)** mode and
therefore not actively blocking anything. The only enforced edge control was a *custom*
rate-limit rule, which the **Standard** tier (~$35/month) supports.

Net: the project was paying **~$295/month per environment** (~$3,500/year, roughly doubled
across staging + production) for a defence-in-depth layer that (a) was never enforced and
(b) duplicated protections already present at the application layer.

## Root cause

This is not a bug — the Bicep did exactly what it said. The root cause is a **process gap**:

1. **The tier was chosen for a feature, not for the MVP's actual needs.** ADR-0013 §11
   specified the managed OWASP rule set as defence-in-depth. That requirement silently forced
   the Premium SKU, but the cost consequence of that one line was never surfaced or weighed
   against the MVP's threat model (a solo-maintained Italian content blog with public
   read-only content and a 3-editor admin UI).

2. **No cost was attached to architecture decisions.** None of the ADRs or the infra guide
   carried a "what does this cost per month" line. Decisions were made on capability and
   correctness; the recurring spend was discovered only after the bill arrived, not at
   decision time.

3. **MVP-appropriate sizing was not a review axis.** Several Azure choices are sensible for a
   production-grade, multi-team product but are heavier than an MVP for one developer needs.
   The default reached for the more capable option without asking "what's the smallest thing
   that meets v1's requirements, and what does it cost?"

## Fix (this instance)

- Front Door profile + WAF policy moved to `Standard_AzureFrontDoor`; managed rule set removed
  (a `managedRules` block is rejected on Standard). Custom rate-limit rule retained in
  Prevention mode. See ADR-0015, which amends ADR-0013 §11. `bicep build` validates clean.

## Lessons / process changes

- **Attach a monthly cost estimate to every infra-shaping ADR.** A one-line "Est. cost:
  ~$X/month per environment" forces the trade-off into the open at decision time, when it's
  cheap to change, instead of at billing time.
- **Add an explicit "is this MVP-appropriate?" check** to infra review. For a v1 run by one
  developer, prefer the cheapest SKU that meets the stated requirement; reach for the premium
  option only when a requirement genuinely demands it (and record that requirement).
- **Separate "active control" from "defence-in-depth" when sizing.** Paying a premium for a
  log-only layer that duplicates app-layer controls is the specific trap that was hit here.
- **Track spend continuously, not reactively.** Set up an Azure Cost Management budget +
  alert per environment so a large fixed cost is caught in week one, not at month-end.

## Candidates worth a cost review (not yet audited)

These are not confirmed problems — flagged for a follow-up cost pass with the same
"MVP-appropriate?" lens:

- **Container Apps** min-replica / scale-to-zero settings per environment (idle cost).
- **PostgreSQL Flexible Server** SKU/storage tier vs. expected v1 load.
- **Log Analytics / Application Insights** retention window and ingestion volume.
- **Staging** sizing — staging can usually run on smaller SKUs than production.

## Action items

1. [x] Downgrade Front Door to Standard (ADR-0015).
2. [ ] Add an "Est. monthly cost" line to the infra ADR template and backfill existing
   infra ADRs (0004 Container Apps, 0005 PostgreSQL, 0010 observability, 0013 §10–11).
3. [ ] Configure an Azure Cost Management budget + alert for each environment.
   (Now tracked as issue #76 under the cost-optimization initiative, #71.)
4. [x] Run a one-pass cost review of the candidates above with the MVP-appropriate lens.
   Done 2026-06-29 — see `retrospective-infra-cost-review-2026-06-29.md`; resulting work
   filed as issues #72–#76 under #71.
