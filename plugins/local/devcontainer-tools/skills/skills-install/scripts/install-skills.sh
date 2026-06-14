#!/usr/bin/env bash
# Installs Claude Code skills into <project>/.claude/skills from
# ../references/skills-registry.json.
#
# Run this INSIDE the devcontainer. It assumes a Debian/Ubuntu base
# (apt-get + sudo to install jq) and the devcontainer's git/network —
# all skills and plugins are created inside the container, not on the host.
#
# Usage:
#   install-skills.sh                  Install all default skills
#   install-skills.sh --list-optional  Print "name<TAB>description" for optional skills
#   install-skills.sh <name> [<name>...]  Install specific skills by name

set -euo pipefail

# Guard: refuse to run outside a container. The devcontainer marks itself
# via /.dockerenv (or the REMOTE_CONTAINERS / CODESPACES env vars).
if [ ! -f /.dockerenv ] && [ -z "${REMOTE_CONTAINERS:-}" ] && [ -z "${CODESPACES:-}" ]; then
  echo "error: run this inside the devcontainer (apt-get/jq + container git are required)." >&2
  echo "       Reopen the project in the container, then re-run /skills-install." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="${SKILLS_REGISTRY:-$SCRIPT_DIR/../references/skills-registry.json}"
TARGET_DIR="${CLAUDE_SKILLS_DIR:-.claude/skills}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found, installing..." >&2
  sudo apt-get update -qq && sudo apt-get install -y -qq jq >/dev/null
fi

install_skill() {
  local name="$1"
  local type repo ref path dest command

  type="$(jq -r --arg n "$name" '.skills[] | select(.name == $n) | .type' "$REGISTRY")"
  if [ -z "$type" ]; then
    echo "==> $name: unknown skill, skipping" >&2
    return
  fi

  case "$type" in
    npx)
      command="$(jq -r --arg n "$name" '.skills[] | select(.name == $n) | .command' "$REGISTRY")"
      echo "==> $name: $command"
      eval "$command"
      ;;
    git)
      local source
      source="$(jq -r --arg n "$name" '.skills[] | select(.name == $n) | .source' "$REGISTRY")"
      repo="$(jq -r --arg s "$source" '.sources[$s].repo' "$REGISTRY")"
      ref="$(jq -r --arg s "$source" '.sources[$s].ref // "main"' "$REGISTRY")"
      path="$(jq -r --arg n "$name" '.skills[] | select(.name == $n) | .path // ""' "$REGISTRY")"
      dest="$(jq -r --arg n "$name" '.skills[] | select(.name == $n) | .dest // $n' "$REGISTRY")"

      echo "==> $name: cloning $repo ($ref)${path:+/$path} -> $TARGET_DIR/$dest"
      local tmp
      tmp="$(mktemp -d)"
      # Shallow-fetch by ref so a branch, tag, OR commit SHA all work
      # (git clone --branch only accepts branch/tag names).
      git -C "$tmp" init --quiet
      git -C "$tmp" remote add origin "$repo"
      git -C "$tmp" fetch --quiet --depth 1 origin "$ref"
      git -C "$tmp" checkout --quiet FETCH_HEAD

      local src="$tmp"
      [ -n "$path" ] && src="$tmp/$path"

      mkdir -p "$TARGET_DIR"
      rm -rf "$TARGET_DIR/$dest"
      cp -r "$src" "$TARGET_DIR/$dest"
      rm -rf "$TARGET_DIR/$dest/.git"
      rm -rf "$tmp"
      ;;
    *)
      echo "==> $name: unknown skill type '$type', skipping" >&2
      ;;
  esac
}

if [ "${1:-}" = "--list-optional" ]; then
  jq -r '.skills[] | select(.default == false) | "\(.name)\t\(.description // "")"' "$REGISTRY"
  exit 0
fi

mkdir -p "$TARGET_DIR"

if [ "$#" -eq 0 ]; then
  names="$(jq -r '.skills[] | select(.default == true) | .name' "$REGISTRY")"
else
  names="$*"
fi

if [ -z "$names" ]; then
  echo "Nothing to install."
  exit 0
fi

for name in $names; do
  install_skill "$name"
done

echo "Done. Skills installed under $TARGET_DIR/"
