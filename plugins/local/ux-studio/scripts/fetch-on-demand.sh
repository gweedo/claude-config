#!/usr/bin/env bash
# Fetch on-demand folders (vendor.lock column `on_demand`) at their pinned commits.
# Sync never downloads or touches these folders; they are git-ignored (ADR-0001).
#
#   scripts/fetch-on-demand.sh          fetch every entry that has an on-demand folder
#   scripts/fetch-on-demand.sh <name>   fetch only that entry's folder
#
# Idempotent: a folder already at its pinned commit is skipped.
set -euo pipefail
GIT_BASE="${UX_STUDIO_GIT_BASE:-https://github.com}"  # tests point this at local repos
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$ROOT/vendor.lock"
want="${1:-}"

if [[ -n "$want" ]] && ! awk -F'\t' -v n="$want" '$1 == n { found = 1 } END { exit !found }' "$LOCK"; then
  echo "fetch-on-demand: unknown entry '$want' (not in vendor.lock)" >&2; exit 2
fi

fetch_one() {
  local name="$1" repo="$2" sha="$3" src="$4" dest="$5" folder="$6"
  local target="$ROOT/$dest/$folder" stamp="$ROOT/$dest/$folder/.vendored-sha"
  if [[ -f "$stamp" && "$(cat "$stamp")" == "$sha" ]]; then
    echo "[$name] $folder/ already at ${sha:0:12}"; return
  fi
  local work; work="$(mktemp -d)"
  git clone -q --filter=blob:none --no-checkout "$GIT_BASE/$repo" "$work/r"
  git -C "$work/r" sparse-checkout set --no-cone "/$src/$folder"
  git -C "$work/r" checkout -q "$sha"
  rm -rf "$target"; mkdir -p "$target"
  cp -a "$work/r/$src/$folder/." "$target/"
  echo "$sha" > "$stamp"
  rm -rf "$work"
  echo "[$name] $folder/ fetched at ${sha:0:12}"
}

while IFS=$'\t' read -r name repo sha src dest on_demand _role; do
  [[ -z "$name" || "$name" == \#* || "$on_demand" == "-" ]] && continue
  [[ -n "$want" && "$name" != "$want" ]] && continue
  fetch_one "$name" "$repo" "$sha" "$src" "$dest" "$on_demand"
done < "$LOCK"
