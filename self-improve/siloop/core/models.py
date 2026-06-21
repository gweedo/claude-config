"""Domain types: events, the pattern rollup, and the enums.

The log (`events.jsonl`) holds two families of records, discriminated by `kind`
(DESIGN §4.1):

* **signal** events — the four mistake categories (PROTOCOL §2), carrying the full
  payload and a per-event `verdict`.
* **correction / lifecycle** events — `override`, `tombstone`, `issue_filed`,
  `resolved`. They carry a `target` (an event id or a pattern key) and are folded into
  the rollup by `fold()`. They are how the append-only log records changes without ever
  editing a prior line.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Union


# --- enums -----------------------------------------------------------------

class SignalType(str, Enum):
    CODE_FAILURE = "code_failure"
    MISUNDERSTOOD_INTENT = "misunderstood_intent"
    WRONG_APPROACH = "wrong_approach"
    REPEATED_CORRECTION = "repeated_correction"


class Verdict(str, Enum):
    """A single event's casual/fixable call at log time (non-authoritative)."""
    CASUAL = "casual"
    FIXABLE = "fixable"


class Status(str, Enum):
    """A pattern's authoritative lifecycle state."""
    CASUAL = "casual"
    FIXABLE = "fixable"
    ISSUED = "issued"
    RESOLVED = "resolved"


class FixType(str, Enum):
    SCRIPT = "script"
    SKILL_EDIT = "skill_edit"
    NEW_SKILL = "new_skill"
    INSTRUCTION_UPDATE = "instruction_update"


FIX_LABELS = {
    FixType.SCRIPT: "fix:script",
    FixType.SKILL_EDIT: "fix:skill",
    FixType.NEW_SKILL: "fix:new-skill",
    FixType.INSTRUCTION_UPDATE: "fix:instructions",
}


# --- events ----------------------------------------------------------------

@dataclass
class SignalEvent:
    id: str
    ts: str                       # ISO-8601 UTC, sortable
    session_id: str
    pattern_key: str
    type: SignalType
    title: str
    summary: str
    root_cause: str
    severity: int                 # 1..3
    verdict: Verdict              # snapshot at log time; non-authoritative
    fix_type: FixType
    proposed_fix: str
    affected_paths: List[str] = field(default_factory=list)
    approved: bool = True
    kind: str = "signal"


@dataclass
class OverrideEvent:
    id: str
    ts: str
    target_event_id: str
    verdict: Verdict              # the pinned verdict (always FIXABLE in practice)
    reason: str
    kind: str = "override"


@dataclass
class TombstoneEvent:
    id: str
    ts: str
    target_event_id: str          # a signal id (retract) or a tombstone id (reinstate)
    reason: str
    kind: str = "tombstone"


@dataclass
class IssueFiledEvent:
    id: str
    ts: str
    pattern_key: str
    issue_url: str
    repo: str
    kind: str = "issue_filed"


@dataclass
class ResolvedEvent:
    id: str
    ts: str
    pattern_key: str
    reason: str
    kind: str = "resolved"


Event = Union[SignalEvent, OverrideEvent, TombstoneEvent, IssueFiledEvent, ResolvedEvent]

_KIND_TO_CLASS = {
    "signal": SignalEvent,
    "override": OverrideEvent,
    "tombstone": TombstoneEvent,
    "issue_filed": IssueFiledEvent,
    "resolved": ResolvedEvent,
}

# enum-typed fields per event class, for (de)serialization
_ENUM_FIELDS = {
    "signal": {"type": SignalType, "verdict": Verdict, "fix_type": FixType},
    "override": {"verdict": Verdict},
}


# --- pattern rollup --------------------------------------------------------

@dataclass
class Pattern:
    pattern_key: str
    count: int
    max_severity: int
    status: Status
    first_seen: str
    last_seen: str
    event_ids: List[str]
    issue_url: Optional[str] = None
    fix_type: Optional[FixType] = None


# --- (de)serialization -----------------------------------------------------

def event_to_dict(event: Event) -> dict:
    """Plain JSON-ready dict (enum values flattened to their string)."""
    d = asdict(event)
    for k, v in list(d.items()):
        if isinstance(v, Enum):
            d[k] = v.value
    return d


def event_from_dict(d: dict) -> Event:
    kind = d.get("kind", "signal")
    cls = _KIND_TO_CLASS.get(kind)
    if cls is None:
        raise ValueError("unknown event kind: {!r}".format(kind))
    data = dict(d)
    for fname, enum_cls in _ENUM_FIELDS.get(kind, {}).items():
        if fname in data and not isinstance(data[fname], Enum):
            data[fname] = enum_cls(data[fname])
    return cls(**data)


def pattern_to_dict(pattern: Pattern) -> dict:
    d = asdict(pattern)
    d["status"] = pattern.status.value
    if pattern.fix_type is not None:
        d["fix_type"] = pattern.fix_type.value
    return d
