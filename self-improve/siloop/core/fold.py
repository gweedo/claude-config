"""fold(events) -> {pattern_key: Pattern}.

The single producer of the `patterns.json` rollup (DESIGN §2). `patterns.json` is never
mutated incrementally; it is always `write_snapshot(fold(read()))`, which makes it a
provable cache of the append-only log. `fold` is pure and total.

Folding rules:
* **tombstone** removes its target signal from all counts; a tombstone whose target is
  another tombstone *reinstates* the originally-removed signal (last-writer-wins),
  so a wrong retraction is itself correctable (PROTOCOL §9 / grill-me #4).
* **override** pins a pattern's verdict to fixable.
* **issue_filed** / **resolved** derive `issued` / `resolved` and `issue_url`.
* a signal event with `ts` after the latest `resolved` event is a **regression**.
"""
from __future__ import annotations

from typing import Dict, List

from .classify import classify
from .models import (
    Event,
    IssueFiledEvent,
    OverrideEvent,
    Pattern,
    ResolvedEvent,
    SignalEvent,
    TombstoneEvent,
    Verdict,
)
from .status import next_status


def _tombstoned_signal_ids(events: List[Event]) -> set:
    """Resolve the tombstone chain to the set of signal ids that are currently retracted."""
    tombstones = {e.id: e for e in events if isinstance(e, TombstoneEvent)}
    signal_ids = {e.id for e in events if isinstance(e, SignalEvent)}
    retracted = set()
    for e in events:  # chronological (append order)
        if not isinstance(e, TombstoneEvent):
            continue
        target = e.target_event_id
        if target in signal_ids:
            retracted.add(target)            # retract a signal
        elif target in tombstones:
            # reinstate: cancel the targeted tombstone's effect
            inner = tombstones[target]
            if inner.target_event_id in signal_ids:
                retracted.discard(inner.target_event_id)
    return retracted


def fold(events: List[Event]) -> Dict[str, Pattern]:
    retracted = _tombstoned_signal_ids(events)

    signals_by_key = {}  # pattern_key -> List[SignalEvent]
    for e in events:
        if isinstance(e, SignalEvent) and e.id not in retracted:
            signals_by_key.setdefault(e.pattern_key, []).append(e)

    # override targets a signal event id; map to the pattern it belongs to
    overridden_keys = set()
    sig_id_to_key = {
        e.id: e.pattern_key
        for e in events
        if isinstance(e, SignalEvent) and e.id not in retracted
    }
    for e in events:
        if isinstance(e, OverrideEvent) and e.target_event_id in sig_id_to_key:
            overridden_keys.add(sig_id_to_key[e.target_event_id])

    filed_by_key = {}     # pattern_key -> latest IssueFiledEvent
    resolved_ts_by_key = {}  # pattern_key -> latest resolved ts
    for e in events:
        if isinstance(e, IssueFiledEvent):
            filed_by_key[e.pattern_key] = e   # last-writer-wins
        elif isinstance(e, ResolvedEvent):
            prev = resolved_ts_by_key.get(e.pattern_key)
            if prev is None or e.ts > prev:
                resolved_ts_by_key[e.pattern_key] = e.ts

    rollup = {}
    for key, evs in signals_by_key.items():
        evs_sorted = sorted(evs, key=lambda x: x.ts)
        count = len(evs_sorted)
        max_sev = max(e.severity for e in evs_sorted)
        verdict = classify(max_sev, count)
        if key in overridden_keys:
            verdict = Verdict.FIXABLE

        filed = filed_by_key.get(key)
        issued = filed is not None
        issue_url = filed.issue_url if filed else None

        resolved_ts = resolved_ts_by_key.get(key)
        resolved = resolved_ts is not None
        regressed = False
        if resolved_ts is not None:
            # a signal strictly after the resolution re-opens the pattern
            regressed = any(e.ts > resolved_ts for e in evs_sorted)
            if regressed:
                resolved = False

        status = next_status(verdict, issued, resolved, regressed)

        rollup[key] = Pattern(
            pattern_key=key,
            count=count,
            max_severity=max_sev,
            status=status,
            first_seen=evs_sorted[0].ts,
            last_seen=evs_sorted[-1].ts,
            event_ids=[e.id for e in evs_sorted],
            issue_url=issue_url,
            fix_type=evs_sorted[-1].fix_type,
        )
    return rollup
