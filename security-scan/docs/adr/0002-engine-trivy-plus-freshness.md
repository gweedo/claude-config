# Engine: Trivy, wrapped, plus a freshness source

The Oracle wraps **Trivy** as its CVE engine, behind an abstraction so it can be
swapped (e.g. for Grype) without touching the Scanner or Definer.

Trivy was chosen over Grype+Syft and over native per-ecosystem tools
(`npm audit`, `pip-audit`, …) because **extensibility is a first-class
requirement**: Trivy already auto-detects a broad range of lockfiles plus images,
Dockerfiles, and IaC, so adding a new language is usually zero work. Native
per-ecosystem tooling was rejected precisely because every new language would be
another tool to wire and maintain.

Trivy answers "what CVEs does `pkg@version` have?" but not "is there a newer
version / is it maintained?" — which the Definer needs. So the Oracle wraps
**Trivy plus a separate freshness source** (registry / deps.dev / OSV), not Trivy
alone.
