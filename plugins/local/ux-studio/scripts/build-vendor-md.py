"""Render VENDOR.md from vendor.lock."""
import sys, pathlib

root = pathlib.Path(sys.argv[1])
rows = [l.split("\t") for l in (root / "vendor.lock").read_text().splitlines()
        if l and not l.startswith("#")]
out = [
    "# Vendored skills",
    "",
    "Pinned third-party content (ADR-0001). Generated from `vendor.lock` by",
    "`scripts/sync-vendor.sh`; never edit the vendored folders by hand.",
    "",
    "| Name | Upstream | Pinned commit | Upstream path | Vendored to | Excluded |",
    "| --- | --- | --- | --- | --- | --- |",
]
for name, repo, sha, src, dest, excl in rows:
    link = f"[`{sha[:12]}`](https://github.com/{repo}/tree/{sha})"
    out.append(f"| {name} | [{repo}](https://github.com/{repo}) | {link} | `{src}` | `{dest}` | {'—' if excl == '-' else f'`{excl}/`'} |")
out += [
    "",
    "## Notes",
    "",
    "- **Licences**: Impeccable and playwright-cli are Apache-2.0; Taste and",
    "  awesome-design-md are MIT. Each vendored folder carries its upstream LICENSE/NOTICE.",
    "- **Impeccable** runs `scripts/impeccable`, a launcher that downloads a",
    "  self-contained engine binary from the project's GitHub releases on first run and",
    "  verifies it against `scripts/engine-checksums.txt` (sha256) before executing.",
    "- **Taste `assets/`** (~38 MB of CSS, components, icons, photos) is git-ignored.",
    "  `scripts/fetch-taste-assets.sh` fetches it at the pinned commit on first use.",
    "- **awesome-design-md** is not a skill: only its README is vendored, to build",
    "  `skills/design-md-reference/INDEX.md`. Each DESIGN.md is fetched on demand.",
    "- **playwright-cli** needs the CLI itself: `npm install -g @playwright/cli@latest`",
    "  on first use, unless `npx --no-install playwright cli` already works.",
    "",
    "## Updating",
    "",
    "```bash",
    "scripts/sync-vendor.sh --update            # bump all pins to upstream HEAD",
    "scripts/sync-vendor.sh --update impeccable # bump one",
    "git diff --stat -- .                        # review before committing",
    "```",
]
(root / "VENDOR.md").write_text("\n".join(out) + "\n")
