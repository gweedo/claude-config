# Security Scan

A reusable capability for checking that Docker images, executables/binaries, and
programming packages are current and free of dangerous CVEs — usable by other
skills and agents. Built as three layers: a shared oracle, a scanner, and a definer.

## Language

**Oracle**:
The deep, shared core, realized as a **Python CLI** (not a skill). Given a concrete
artifact spec (a `package@version`, an image tag, or lockfiles), returns CVE and
freshness facts as **JSON on stdout** with a **meaningful exit code** (`0` = no
blocking findings). Both the Scanner and the Definer call it; so do the hook and
routine.
_Avoid_: engine, checker, backend (the *engine* is the underlying tool the Oracle wraps, e.g. Trivy)

**Scanner**:
The verifier. Given something that **already exists** (a working tree's lockfiles,
an image, a binary), enumerates it and reports what is outdated or vulnerable.
Reactive. This is what the hook, routine, and command wrap.
_Avoid_: auditor, checker

**Definer**:
The selector's adviser. Given a **need** ("a Postgres driver for Python"), **vets
and ranks model-proposed candidates** (it does no open-ended search) and **advises**
a pick — with CVE/freshness as one weighted factor among maintenance, license, and
fit. It advises; it does not decide. Invoked at architecture-design time.
_Avoid_: selector, picker, chooser (it does not autonomously choose)

**Engine**:
The underlying CVE tool the Oracle wraps — chosen: **Trivy**, behind an
abstraction so it can be swapped. Provides CVE facts for packages, images,
Dockerfiles, and IaC.
_Avoid_: scanner (the Scanner is our layer, not the engine)

**Blocking finding**:
A finding severe enough to fail a gate (e.g. stop the hook). Default: severity ≥
HIGH **and** a fix is available. Configurable.
_Avoid_: critical, failure

**Advisory finding**:
A finding that is reported but never gates: a merely-outdated package, or a
HIGH/CRITICAL CVE with no available fix. The Definer's main currency.
_Avoid_: warning, info

**Freshness source**:
A second data source the Oracle layers on top of the Engine to answer "is there a
newer version / is it maintained?" (e.g. a package registry, deps.dev, or OSV).
Needed by the Definer; Trivy alone does not provide it.
