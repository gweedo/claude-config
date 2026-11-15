# UX Studio

A UX/UI **Designer** agent and a separate, read-only **Reviewer** agent that share
vendored design skills, plus the capped **UX loop** (build → Review pass → fix). Vocabulary is in
[CONTEXT.md](CONTEXT.md), and decisions are in [docs/adr/](docs/adr/).

## Agents

| Agent | Model | Triggers | Does |
|-------|-------|----------|------|
| `ux-ui-designer` | inherit | Delegated automatically for "build / redesign / restyle / polish this UI", or called by `ux-loop` | Builds with Impeccable, applies the Taste gate on marketing sites, picks a reference design when there's no DESIGN.md, and ends with a Playwright **Smoke check** |
| `ux-reviewer` | opus | **Only** an explicit "review the UI", or `ux-loop` | Playwright at 390/768/1440, Impeccable `audit` + `critique`, and the Taste gate on marketing sites. Returns severity-ranked **Findings** and edits nothing |

## Skills

| Skill | Source | Role |
|-------|--------|------|
| `ux-loop` | ours | `/ux-studio:ux-loop <brief>`: Designer → Reviewer → Designer, at most 2 Review passes. Then it offers to file **Leftovers** to the project's tracker (`docs/agents/issue-tracker.md`) |
| `design-md-reference` | ours, over [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | Index of 84 real-site DESIGN.md files. Each one is fetched on demand at the pinned commit |
| `impeccable` | vendored, [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Primary workflow: shape, build, critique, audit, polish |
| `design-taste-frontend` | vendored, [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Taste gate, for marketing and company sites only |
| `playwright-cli` | vendored, [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | Browser driving for smoke checks and reviews |

Pins, licences and runtime notes are in [VENDOR.md](VENDOR.md).

## Usage

- *"Build a pricing page for this app"*: the Designer picks it up.
- *"Review the UI of /checkout"*: the Reviewer runs.
- `/ux-studio:ux-loop redesign the dashboard home`: the full loop.

## Runtime requirements

- **Node 22+** and Chromium/Chrome (cloud sessions have both).
- `playwright-cli` installs itself on first use (`npm install -g @playwright/cli@latest`).
- Impeccable's launcher downloads a checksum-verified engine binary from its GitHub
  releases on first run.
- Taste needs its `assets/`: run `scripts/fetch-taste-assets.sh` once (the Designer does
  this itself). Taste also registers a `Stop` hook (`scripts/gate.mjs`) while its skill
  is active, which checks the built page in a real browser.

## Maintaining

```bash
scripts/sync-vendor.sh                     # re-copy everything at the pinned commits
scripts/sync-vendor.sh --update            # bump pins to upstream HEAD
scripts/sync-vendor.sh --update impeccable # bump one
```

Vendored folders are never edited by hand. Review the diff, then commit.
