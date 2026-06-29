# Hook is a PreToolUse Bash hook, gating at commit on changed manifests

The scanner hook is a **Claude Code PreToolUse hook on the Bash matcher**,
mirroring the repo's existing `hooks/block-dangerous-git.{sh,ps1}` (OS-dispatched
via `uname`, wired to `$HOME/.claude`). It intercepts when **the agent** runs git,
so it covers every repo the agent operates in with no per-repo install.

A real per-repo git hook was rejected: it must be installed into each project and
is blind to the agent.

It fires on `git commit` but **only scans when a dependency manifest/lockfile is
among the staged files** (otherwise passes instantly — the fast path), runs the
Oracle CLI on those files, and **blocks (exit 2) on blocking findings**, passing on
advisory-only. Gating at commit means vulnerable deps never land.
