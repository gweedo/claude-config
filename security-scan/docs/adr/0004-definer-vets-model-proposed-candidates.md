# Definer vets model-proposed candidates; deps.dev for freshness

The Definer does **not** do open-ended package search. The model/agent proposes
candidates for a need (it is already good at enumerating options); the Definer's
bounded job is to **vet and rank** them and advise a pick. It may also accept an
explicit candidate list from a caller. Building/maintaining a package-search-API
integration was rejected as scope we don't want.

Ranking data beyond CVEs (latest version, release recency, maintenance health)
comes from **deps.dev** — one multi-ecosystem API giving versions, release dates,
OpenSSF Scorecard, and advisories. This is the **freshness source** left open in
ADR-0002: Trivy supplies CVEs, deps.dev supplies freshness + maintenance.
