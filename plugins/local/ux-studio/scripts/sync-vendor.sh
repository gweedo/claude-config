#!/usr/bin/env bash
# Re-vendor ux-studio's third-party skills from vendor.lock (ADR-0001).
#
#   scripts/sync-vendor.sh            re-copy every entry at its pinned SHA
#   scripts/sync-vendor.sh --update   bump every pin to upstream HEAD, then copy
#   scripts/sync-vendor.sh --update <name>...   bump only the named entries
#
# Vendored files are never edited by hand: change them only through this script,
# then review the diff. Also regenerates VENDOR.md and the design-md index.
set -euo pipefail

GIT_BASE="${UX_STUDIO_GIT_BASE:-https://github.com}"  # tests point this at local repos
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/vendor.lock"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

update=0; only=()
if [[ "${1:-}" == "--update" ]]; then update=1; shift; only=("$@"); fi

wants_update() {
  (( update )) || return 1
  (( ${#only[@]} == 0 )) && return 0
  local n; for n in "${only[@]}"; do [[ "$n" == "$1" ]] && return 0; done; return 1
}

for n in ${only[@]+"${only[@]}"}; do
  if ! awk -F'\t' -v n="$n" '$1 == n { found = 1 } END { exit !found }' "$LOCK"; then
    echo "sync-vendor: unknown entry '$n' (not in vendor.lock)" >&2; exit 2
  fi
done

new_lock="$WORK/vendor.lock"
grep '^#' "$LOCK" > "$new_lock"

while IFS=$'\t' read -r name repo sha src dest on_demand role; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  url="$GIT_BASE/$repo"
  if wants_update "$name"; then
    sha="$(git ls-remote "$url" HEAD | cut -f1)"
    echo "[$name] bumped to $sha"
  fi
  echo "[$name] $repo@${sha:0:12} $src -> $dest"

  clone="$WORK/$name"
  git clone -q --filter=blob:none --no-checkout "$url" "$clone"
  sparse=("/$src" "/LICENSE*" "/NOTICE*")
  [[ "$on_demand" != "-" ]] && sparse+=("!/$src/$on_demand/")  # fetched later by fetch-on-demand.sh
  git -C "$clone" sparse-checkout set --no-cone "${sparse[@]}"
  git -C "$clone" checkout -q "$sha"

  target="$ROOT/$dest"
  if [[ -d "$clone/$src" ]]; then
    # Replace everything except the on-demand folder, which is fetched separately.
    mkdir -p "$target"
    find "$target" -mindepth 1 -maxdepth 1 ! -name "$on_demand" -exec rm -rf {} +
    cp -a "$clone/$src/." "$target/"
    for f in "$clone"/LICENSE* "$clone"/NOTICE*; do [[ -e "$f" ]] && cp "$f" "$target/"; done
  else
    mkdir -p "$(dirname "$target")"; cp "$clone/$src" "$target"
    for f in "$clone"/LICENSE* "$clone"/NOTICE*; do [[ -e "$f" ]] && cp "$f" "$(dirname "$target")/UPSTREAM-$(basename "$f")"; done
  fi
  if [[ "$role" == "design-md-index" ]]; then
    git -C "$clone" ls-tree --name-only "$sha" design-md/ | sed 's#^design-md/##' > "$(dirname "$target")/upstream-slugs.txt"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$repo" "$sha" "$src" "$dest" "$on_demand" "$role" >> "$new_lock"
done < "$LOCK"

cp "$new_lock" "$LOCK"
python3 -I "$ROOT/scripts/build-design-md-index.py" "$ROOT"
python3 -I "$ROOT/scripts/build-vendor-md.py" "$ROOT"
echo "Done. Review with: git diff --stat -- $ROOT"
