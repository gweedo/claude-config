# Vendored skills

Pinned third-party content (ADR-0001). Generated from `vendor.lock` by
`scripts/sync-vendor.sh`; never edit the vendored folders by hand.

| Name | Role | Upstream | Pinned commit | Upstream path | Vendored to | On-demand folder |
| --- | --- | --- | --- | --- | --- | --- |
| impeccable | skill | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | [`2b86d9c07b97`](https://github.com/pbakaus/impeccable/tree/2b86d9c07b97d4bed7de23583e1bd1e58dd2baae) | `plugin/skills/impeccable` | `skills/impeccable` | — |
| design-taste-frontend | skill | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | [`f6b76575f949`](https://github.com/Leonxlnx/taste-skill/tree/f6b76575f949707b4e3c37cd86cb44b0b98643e8) | `skills/taste-skill` | `skills/design-taste-frontend` | `assets/` |
| playwright-cli | skill | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | [`b21724888b81`](https://github.com/microsoft/playwright-cli/tree/b21724888b8100b05ef8dee3a92f2bb03bf4dcde) | `skills/playwright-cli` | `skills/playwright-cli` | — |
| awesome-design-md | design-md-index | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | [`fcc702849322`](https://github.com/VoltAgent/awesome-design-md/tree/fcc70284932276d085f01ef9f83edde90b1258cb) | `README.md` | `skills/design-md-reference/upstream-README.md` | — |

## Notes

- **Licences**: Impeccable and playwright-cli are Apache-2.0; Taste and
  awesome-design-md are MIT. Each vendored folder carries its upstream LICENSE/NOTICE.
- **Impeccable** runs `scripts/impeccable`, a launcher that downloads a
  self-contained engine binary from the project's GitHub releases on first run and
  verifies it against `scripts/engine-checksums.txt` (sha256) before executing.
- **On-demand folders** (Taste's `assets/`: ~38 MB of CSS, components, icons,
  photos) are git-ignored, never downloaded or touched by sync, and fetched at the
  pinned commit on first use by `scripts/fetch-on-demand.sh [name]`.
- **awesome-design-md** is not a skill: only its README is vendored, to build
  the index (its lock role is `design-md-index`). Each DESIGN.md is fetched on demand.
- **playwright-cli** needs the CLI itself: `npm install -g @playwright/cli@latest`
  on first use, unless `npx --no-install playwright cli` already works.

## Updating

```bash
scripts/sync-vendor.sh --update            # bump all pins to upstream HEAD
scripts/sync-vendor.sh --update impeccable # bump one
git diff --stat -- .                        # review before committing
```
