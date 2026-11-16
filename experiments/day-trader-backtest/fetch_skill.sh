#!/usr/bin/env bash
# Fetch day-trader-skill pinned to the reviewed commit (see memory/day-trader-skill-security-review.md).
set -euo pipefail
cd "$(dirname "$0")"
COMMIT=3d0f4ef
DEST=.vendor/day-trader-skill
if [ ! -d "$DEST/.git" ]; then
  git clone -q https://github.com/Jakeschincariol/day-trader-skill "$DEST"
fi
git -C "$DEST" checkout -q "$COMMIT"
echo "day-trader-skill at $(git -C "$DEST" rev-parse --short HEAD)"
