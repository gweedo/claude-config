"""fold() folding rules + lossless rebuild (DESIGN §11 T2/T3, the SSoT guarantee)."""
from siloop.core.fold import fold
from siloop.core.models import (
    FixType,
    IssueFiledEvent,
    OverrideEvent,
    ResolvedEvent,
    SignalEvent,
    SignalType,
    Status,
    TombstoneEvent,
    Verdict,
)


def sig(id, ts, key, sev=2):
    return SignalEvent(
        id=id, ts=ts, session_id="s", pattern_key=key, type=SignalType.WRONG_APPROACH,
        title="t", summary="", root_cause="rc", severity=sev, verdict=Verdict.CASUAL,
        fix_type=FixType.INSTRUCTION_UPDATE, proposed_fix="pf",
    )


def test_count_and_verdict_from_signals():
    p = fold([sig("e1", "t1", "k", 2), sig("e2", "t2", "k", 2)])["k"]
    assert p.count == 2
    assert p.max_severity == 2
    assert p.status == Status.FIXABLE       # recurrence promoted
    assert p.event_ids == ["e1", "e2"]


def test_tombstone_drops_event_from_count():
    events = [sig("e1", "t1", "k"), sig("e2", "t2", "k"),
              TombstoneEvent(id="x1", ts="t3", target_event_id="e2", reason="oops")]
    p = fold(events)["k"]
    assert p.count == 1
    assert p.status == Status.CASUAL         # back below threshold


def test_tombstone_of_tombstone_reinstates():
    events = [sig("e1", "t1", "k"), sig("e2", "t2", "k"),
              TombstoneEvent(id="x1", ts="t3", target_event_id="e2", reason="oops"),
              TombstoneEvent(id="x2", ts="t4", target_event_id="x1", reason="undo")]
    assert fold(events)["k"].count == 2


def test_override_pins_fixable():
    events = [sig("e1", "t1", "k", sev=1),
              OverrideEvent(id="o1", ts="t2", target_event_id="e1",
                            verdict=Verdict.FIXABLE, reason="severe")]
    assert fold(events)["k"].status == Status.FIXABLE


def test_issue_filed_then_resolved():
    events = [sig("e1", "t1", "k"), sig("e2", "t2", "k"),
              IssueFiledEvent(id="i1", ts="t3", pattern_key="k",
                              issue_url="http://x/1", repo="o/r")]
    p = fold(events)["k"]
    assert p.status == Status.ISSUED
    assert p.issue_url == "http://x/1"

    events.append(ResolvedEvent(id="r1", ts="t4", pattern_key="k", reason="fixed"))
    assert fold(events)["k"].status == Status.RESOLVED


def test_regression_reopens_resolved_pattern():
    events = [sig("e1", "t1", "k"), sig("e2", "t2", "k"),
              IssueFiledEvent(id="i1", ts="t3", pattern_key="k", issue_url="u", repo="o/r"),
              ResolvedEvent(id="r1", ts="t4", pattern_key="k", reason="fixed"),
              sig("e3", "t5", "k")]              # recurs after resolution
    assert fold(events)["k"].status == Status.FIXABLE


def test_fold_is_idempotent_and_lossless():
    events = [sig("e1", "t1", "k"), sig("e2", "t2", "k"),
              IssueFiledEvent(id="i1", ts="t3", pattern_key="k", issue_url="u", repo="o/r")]
    once = fold(events)
    twice = fold(events)
    assert once == twice                         # pure, deterministic
    # status + issue_url are reconstructed from the log alone (no out-of-band carry)
    assert once["k"].status == Status.ISSUED and once["k"].issue_url == "u"
