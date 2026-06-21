# Self-Improvement Loop — PROTOCOL

> **What this file is.** The agent-facing rulebook for the self-improvement loop.
> Any agent (Cowork, Claude Code, a custom FastAPI agent) reads this file at the
> start of a working session and follows it. The loop has **no daemon and no magic**:
> the "detector" is whatever agent is currently working, governed by these rules,
> plus an append-only log and a small CLI. That is what makes it portable and
> independent of any single tool.

---

## 1. Mental model

```
            during a working session                      at "wrap up"
  ┌─────────────────────────────────────┐      ┌────────────────────────────┐
  │  agent works on a task               │      │  loop wrap-up              │
  │      │                               │      │    • recompute classes     │
  │      ▼ spots one of the 4 signals    │      │    • write session recap   │
  │  flag it INLINE ──► user approves ───┼──►   │    • create GitHub issues  │
  │      │                               │      │      for fixable items     │
  │      ▼                               │      └────────────────────────────┘
  │  loop log  ──► events.jsonl          │
  │              patterns.json (counts)  │
  └─────────────────────────────────────┘
```

The agent does the **thinking** (detect, diagnose, propose). The repo + CLI do the
**remembering**. GitHub issues are the **handoff** to a future implementer (an agent
or you). The loop itself never edits your code or your skills.

---

## 2. What to detect — the four signals

Flag an event when one of these happens. Each event maps to a `type`.

| `type` | Trigger | Ski-assistant example |
|---|---|---|
| `code_failure` | Code didn't run, a test failed, an exception was raised, a script produced wrong output. | The AINEVA bulletin parser threw on a missing `danger_level` field. |
| `misunderstood_intent` | You had to re-explain what you actually wanted; the agent solved the wrong problem. | Asked for *aspect* filtering of slopes; agent filtered by *altitude*. |
| `wrong_approach` | Code worked but the design was wrong — DDD violation, leaked infra into domain, skipped the repository pattern, raw SQL string, etc. | `RouteService` queried the DB directly instead of going through `RouteRepository`. |
| `repeated_correction` | A small style/convention fix you keep making. | Missing type hints; secret hardcoded instead of env var; no error handling on an API call. |

**Do not flag:** transient environment hiccups (network blip, rate limit), your own
typos that you immediately fix, or anything you explicitly say to ignore. When in
doubt, ask before logging.

---

## 3. The inline flow (capture)

1. Agent detects a signal.
2. Agent flags it in one short line and proposes a diagnosis + fix, e.g.:
   > ⚠️ Looks like a `wrong_approach`: `RouteService` is calling the DB directly
   > (leaks infra into the application layer). Proposed fix: `instruction_update` —
   > add a "repositories only" rule. Log it? `[pattern: infra-leak-in-app]`
3. **User approves, edits, or drops it.** Nothing is logged without approval.
4. On approval the agent calls `loop log …` (see §8). The CLI appends to
   `events.jsonl`, recomputes `patterns.json` by folding the log, and prints the
   resulting `verdict` (and the pattern's current `status`).

Keep flags lightweight — one or two lines. Batch nothing here; the wrap-up does the
batching.

---

## 4. Verdict & status — casual vs fixable

This is the heart of the loop. The rule is **recurrence + severity**:

```
fixable  ⇐  recurrence_count >= 2   OR   severity == 3
casual   ⇐  otherwise (first sighting, low/medium severity)
```

Two words, kept distinct on purpose so they never blur:

- **`verdict`** — this rule's call for **one event**, `casual | fixable`, frozen at log time. A
  snapshot; never the current truth.
- **`status`** — a **pattern's** lifecycle, `casual → fixable → issued → resolved` (§7). This is
  the authoritative state, always recomputed from the full log.

So an event has a `verdict`; a pattern has a `status`. When you need "is this being acted on
right now?", read the pattern's `status`, never an old event's `verdict`.

- **severity** is a 1–3 judgment set when logging:
  - `1` cosmetic — naming, formatting. *E.g. missing type hints; inconsistent import order.*
  - `2` real but contained — a bug or design slip with a blast radius of one module. *E.g. the
    bulletin parser throws on a missing field; `RouteService` queries the DB directly.*
  - `3` serious — security, data loss, or safety-relevant output. *E.g. a hardcoded secret; a
    wrong avalanche risk shown to the user.* Severity-3 is **fixable immediately**, even as a
    one-off.
  - **Tie-breaker:** when torn between two levels, pick the **lower** and let recurrence
    promote it. This keeps sev-3's "act now even once" power rare and therefore trustworthy.
- **recurrence_count** is the number of times the same `pattern_key` has been logged
  (across all sessions). The second sighting promotes a `casual` pattern to `fixable`.

`casual` items are still **tracked** — they sit in the log accumulating a count. That
is how the system *learns* what is systematic instead of guessing on day one.

---

## 5. `pattern_key` conventions

The `pattern_key` is how recurrence is counted, so it must be **stable and reusable**.

- Short, kebab-case, describes the *pattern* not the instance.
- Good: `missing-type-hints`, `raw-sql-in-router`, `infra-leak-in-app`,
  `hardcoded-secret`, `misread-aineva-scope`, `no-error-handling-external-api`.
- Bad: `error-in-route-service-line-42` (instance, never recurs),
  `bug` (too broad to be useful).
- Before inventing a key, check `loop list` for an existing one that fits. Reuse beats
  inventing — a near-duplicate key splits the count and hides a real pattern.
- **Enforced, not just advised:** `loop log` **rejects an unknown `pattern_key`** and prints
  the 3 closest existing keys — matched on **tokenized kebab parts** (Jaccard over
  `{raw, sql, in, router}`) *and* edit distance, so reordered/synonym-free near-dups surface,
  not just typos. Pass `--new-pattern` to confirm a genuinely new one; every new key is **echoed
  into the recap's "new patterns this session" line** so creating one is visible and reviewable.
  The guardrail's v1 job is to make collisions *visible*, not to catch every semantic dup —
  pgvector similarity (DESIGN §9) is the later upgrade. The matcher lives behind a `PatternMatcher`
  port in core (not the CLI), so pgvector is a drop-in second adapter.

---

## 6. Fix-type routing

Every event carries a **proposed** `fix_type`. These are starting heuristics; the
agent can override with reasoning.

| Signal | Usual `fix_type` | Why |
|---|---|---|
| `code_failure` | `script` | Add/repair a script, add a regression test, add a CI check. |
| `repeated_correction` | `instruction_update` or `script` | Encode the rule in CLAUDE.md, or automate it as a lint rule. |
| `wrong_approach` | `instruction_update`, `skill_edit`, or `new_skill` | The right pattern needs to live somewhere durable. |
| `misunderstood_intent` | `instruction_update` or `skill_edit` | Usually a prompt/skill-description clarity gap. |

`fix_type` values and their GitHub label:

| `fix_type` | Label | Meaning |
|---|---|---|
| `script` | `fix:script` | Automatable; a script/test/CI rule resolves it. |
| `skill_edit` | `fix:skill` | An existing skill needs editing. |
| `new_skill` | `fix:new-skill` | A capability gap → scaffold a new skill. |
| `instruction_update` | `fix:instructions` | Update CLAUDE.md / project rules / a skill description. |

> Reminder: in Cowork the installed skills are a **read-only cache**. `skill_edit` and
> `new_skill` therefore target the **source** in `gweedo/claude-config`, never the
> live cache. The issue says *what* to change; a later pass makes the edit and you
> reinstall/sync.

---

## 7. Wrap-up

Triggered when you say "wrap up" (or `loop wrap-up`). The agent:

1. Recomputes every pattern's `status` by folding the whole log (`loop rebuild`).
2. Writes a human-readable recap to `sessions/<session_id>.md` (overwriting any prior render).
3. For each **fixable, un-issued** pattern, creates one GitHub issue from the template (see
   DESIGN.md) and **appends an `issue_filed` event** so `status: issued` + `issue_url` are
   re-derivable from the log, not held out-of-band. "Already issued" is decided by a **live
   GitHub search** (label `self-improve` + the hidden `pattern` marker, only `state:open`
   counts) — never the local cache, which a manually-closed issue would leave stale. A pattern
   already `issued` that **recurred** this session gets a comment on its open issue, not a
   duplicate. A `resolved` pattern that recurred is re-opened as a **regression** and flagged
   loudly in the recap.
4. Prints a short summary: what was logged, what stayed casual, what became issues
   (with links), and any regressions.

Wrap-up is **idempotent**: the dedup is search→create→append-event **per item under the store
lock**, so a rerun (or a mid-batch crash + rerun) creates no duplicate. If the live search
itself can't reach GitHub, wrap-up writes the recap but creates **zero** issues and exits
non-zero ("rerun later") — a failed search is never read as "safe to create." If wrap-up is
skipped, use `loop list --status fixable --unissued` as a standing catch.

`casual` items create **no** issue — they just keep accruing recurrence until they
cross the threshold in some future session.

Always show the planned issues and get a final nod before creating them (`--dry-run`
first if unsure).

---

## 8. CLI quick reference

```bash
# capture an approved event
loop log \
  --type wrong_approach \
  --pattern infra-leak-in-app \
  --title "RouteService queries DB directly" \
  --summary "Bypassed RouteRepository in the application layer" \
  --root-cause "No explicit 'repositories only' rule; agent defaulted to convenience" \
  --severity 2 \
  --fix-type instruction_update \
  --fix "Add a 'data access only via repositories' rule to CLAUDE.md" \
  --paths "src/application/route_service.py" \
  --session 2026-06-20-ski

# review what's open
loop list --status fixable
loop list --status fixable --unissued      # fixable but no open issue yet
loop list --session 2026-06-20-ski

# manually promote a casual item (severe one-off you want acted on now)
loop promote <event_id> --reason "security relevant"

# retract a mis-logged event (appends a tombstone; rebuild drops it from counts)
loop retract <event_id> --reason "logged in haste, wrong pattern_key"

# end of session
loop wrap-up --session 2026-06-20-ski --repo gweedo/claude-config --dry-run
loop wrap-up --session 2026-06-20-ski --repo gweedo/claude-config
# fix:script issues can land in the project repo instead of claude-config:
loop wrap-up --session 2026-06-20-ski --repo gweedo/claude-config --issue-repo gweedo/ski-assistant

# close the loop once a fix lands
loop resolve infra-leak-in-app --reason "repository-only rule added to CLAUDE.md"
```

---

## 9. Guardrails

- **Approval is mandatory.** Never log, create an issue, **promote, retract, or resolve**
  without an explicit OK. `promote`/`retract`/`resolve` override the algorithm's own judgment,
  so they carry the same bar as issue creation — the agent may *propose* them inline; the human
  runs them. `retract` refuses to demote a currently-`issued` pattern unless `--force` (the
  GitHub issue still exists), and never auto-closes that issue.
- **No secrets in the log.** Summaries and root causes must not contain tokens, keys,
  passwords, or personal data. If an event *is about* a leaked secret, describe the
  pattern (`hardcoded-secret`) — never paste the value. Defense-in-depth: `build_issue` runs a
  mechanical secret scrub and **refuses to file** on a denylist hit, so a slip never reaches a
  public GitHub issue — but the human rule comes first.
- **Don't over-flag.** A noisy log kills the signal. Prefer one good pattern over five
  instances of it.
- **The loop is advisory.** It produces issues, not code changes. It never edits your
  repo, code, or skills directly.
