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
    "| Name | Role | Upstream | Pinned commit | Upstream path | Vendored to | On-demand folder |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
for name, repo, sha, src, dest, on_demand, role in rows:
    link = f"[`{sha[:12]}`](https://github.com/{repo}/tree/{sha})"
    out.append(f"| {name} | {role} | [{repo}](https://github.com/{repo}) | {link} | `{src}` | `{dest}` | {'—' if on_demand == '-' else f'`{on_demand}/`'} |")
out += [
    "",
    "## Notes",
    "",
    "- **Licences**: Impeccable and playwright-cli are Apache-2.0; Taste and",
    "  awesome-design-md are MIT. Each vendored folder carries its upstream LICENSE/NOTICE.",
    "- **Impeccable** runs `scripts/impeccable`, a launcher that downloads a",
    "  self-contained engine binary from the project's GitHub releases on first run and",
    "  verifies it against `scripts/engine-checksums.txt` (sha256) before executing.",
    "- **On-demand folders** (Taste's `assets/`: ~38 MB of CSS, components, icons,",
    "  photos) are git-ignored, never downloaded or touched by sync, and fetched at the",
    "  pinned commit on first use by `scripts/fetch-on-demand.sh [name]`.",
    "- **awesome-design-md** is not a skill: only its README is vendored, to build",
    "  the index (its lock role is `design-md-index`). Each DESIGN.md is fetched on demand.",
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
