#!/usr/bin/env bash
# Fetch design-taste-frontend's assets/ (~38 MB, git-ignored) at the SHA pinned in
# vendor.lock. Run once before the Taste skill builds a page (ADR-0001). Idempotent.
set -euo pipefail
GIT_BASE="${UX_STUDIO_GIT_BASE:-https://github.com}"  # tests point this at local repos
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
read -r _ repo sha src dest _ < <(grep -P '^design-taste-frontend\t' "$ROOT/vendor.lock")
target="$ROOT/$dest/assets"
stamp="$target/.vendored-sha"
if [[ -f "$stamp" && "$(cat "$stamp")" == "$sha" ]]; then echo "Taste assets already at ${sha:0:12}"; exit 0; fi
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
git clone -q --filter=blob:none --no-checkout "$GIT_BASE/$repo" "$work/r"
git -C "$work/r" sparse-checkout set --no-cone "/$src/assets"
git -C "$work/r" checkout -q "$sha"
rm -rf "$target"; mkdir -p "$target"
cp -a "$work/r/$src/assets/." "$target/"
echo "$sha" > "$stamp"
echo "Taste assets fetched to $target at ${sha:0:12}"
