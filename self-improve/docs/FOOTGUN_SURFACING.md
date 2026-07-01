# Footgun surfacing — decision + design

Companion to `../README.md`, `PROTOCOL.md`, `DESIGN.md`. Addresses
[gweedo/claude-config#32](https://github.com/gweedo/claude-config/issues/32): make catalogued
footguns surface automatically when code in their area is being written, instead of relying on
passive recall.

## The gap this closes

From `retrospective-skills-orchestrator-2026-06-25.md` (Theme E + institutional-memory section): a
known footgun (a DB engine created without the Entra-token connection listener — the exact root
cause of a prior incident) reappeared in a new code path. The project *had* the memory; it wasn't
consulted at write-time. Recording isn't the gap — consulting the catalog at the moment of writing
is.

## Decision (recorded before implementation, per acceptance criteria)

Studied with the maintainer on 2026-07-01:

1. **Trigger mechanism — both, layered:**
   - A `PreToolUse` hook (`hooks/footgun-nudge.sh` / `.ps1`, matcher `Edit|Write`) is the mechanism
     that actually ships now. It's deterministic, works in any session (orchestrated or not), and
     needs no agent judgment to decide whether to fire — it fires whenever the file being written
     matches a catalogued area.
   - Orchestrator context injection (agent-orchestra checking the catalog when dispatching to a
     role agent) is the second layer, **deferred**: `plugins/local/agent-orchestra/agents/` has no
     dispatch code yet (scaffolding only — see its `CONTEXT.md`). When the orchestrator's dispatch
     logic exists, it should read the same `footguns.json` and inject matching entries into the
     role agent's briefing, so a footgun surfaces even in a sub-agent's isolated context that never
     goes through the top-level hook. Tracked as a follow-up, not blocking this issue.

2. **Tagging scheme — path globs.** Each entry carries an `area_globs` list matched against the
   file path in `tool_input.file_path`. Chosen over symbol/identifier matching (would require
   scanning file contents, not just the path — slower, and not needed for a v1 hook) and over
   topic labels (needs semantic matching, i.e. an LLM in the loop, which a deterministic hook
   can't do). Globs are intentionally broad in the seed entry since this catalog is shared across
   projects; tighten `area_globs` to real paths the first time an entry proves out in a specific
   codebase.

3. **Catalog home — `self-improve/footguns.json`,** sibling to `patterns.json`, inside the
   canonical `self-improve` project (`~/.claude/self-improve/` in `gweedo/claude-config`). Kept
   separate from `patterns.json` rather than folding in: `patterns.json` is the append-only,
   `fold()`-derived record of *corrections that happened* (owned by `siloop/core/fold.py`, rebuilt
   from `events.jsonl`); `footguns.json` is a small, hand-curated, standing catalog of *rules to
   enforce going forward*. Different lifecycle (curated vs. derived), different consumer (a shell
   hook, not the Python `loop` CLI) — merging them would make the hook depend on the siloop
   package and its schema for no benefit.

4. **Composition with existing memory recall — no overlap by design.** The `~/.claude/memory/`
   system (user/feedback/project/reference types, loaded into conversation context) is broad,
   semantic, and cross-session — it's recalled by the agent reading its own context, not matched
   mechanically. `footguns.json` is narrow: only "never X; always Y" rules tied to a code area,
   matched deterministically by path glob at the moment of an `Edit`/`Write` call. If a footgun
   ever needs semantic (non-path-based) matching, that's a signal it belongs in memory instead of
   here — don't duplicate an entry in both places.

## How it works

`hooks/footgun-nudge.sh` (POSIX) / `.ps1` (Windows), wired into `settings.json`'s `PreToolUse` for
matcher `Edit|Write`:

1. Reads `tool_input.file_path` from the hook's stdin JSON.
2. Loads `~/.claude/self-improve/footguns.json`.
3. For each entry, glob-matches `area_globs` against the (slash-normalized) file path.
4. On the first match, emits `additionalContext` with the entry's `rule` and `why` — non-blocking,
   same pattern as `hooks/verify-outcome-nudge.sh`.

No match, no catalog file, or unparseable input all exit `0` silently — this must never block an
edit.

## Adding a footgun

Append an object to `footguns.json`'s `footguns` array:

```json
{
  "id": "kebab-case-id",
  "rule": "Never X; always Y.",
  "why": "What breaks if you don't, and where this was learned.",
  "area_globs": ["**/path/pattern.py"],
  "source": "where this was learned (retro doc, issue #)",
  "added": "YYYY-MM-DD"
}
```

Prefer specific globs over broad ones once an entry has proven itself in a real codebase — broad
globs cost more false-positive nudges, which is exactly the "noise" the issue asked to keep low.
