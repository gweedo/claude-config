"""Use-case tests: record_event, wrap-up idempotency, GitHub-down safety, lossless
rebuild through the store (DESIGN §11 T4/T9 — the two headline guarantees)."""
import os

import pytest

from siloop.core.fold import fold
from siloop.core.loop import (
    EventDraft,
    UnknownPattern,
    record_event,
    rebuild,
    wrap_up,
)
from siloop.core.models import FixType, SignalType, Status
from siloop.core.store import EventLog

from .fakes import FakeIssueGateway, seq_clock, seq_ids


def _store(tmp_path):
    return EventLog(str(tmp_path / "events.jsonl"), str(tmp_path / "patterns.json"))


def _draft(key="infra-leak-in-app", sev=2, session="2026-06-21-ski"):
    return EventDraft(
        session_id=session, pattern_key=key, type=SignalType.WRONG_APPROACH,
        title="RouteService queries DB", summary="bypassed repo", root_cause="no rule",
        severity=sev, fix_type=FixType.INSTRUCTION_UPDATE, proposed_fix="add rule",
        affected_paths=["src/route_service.py"],
    )


def _log(store, draft, ids, clock, allow_new=True):
    return record_event(store, draft, allow_new=allow_new, clock=clock, id_factory=ids)


def test_record_event_returns_verdict_and_status(tmp_path):
    store = _store(tmp_path)
    ids, clock = seq_ids(), seq_clock()
    r1 = _log(store, _draft(), ids, clock)
    assert r1.verdict.value == "casual" and r1.is_new_pattern
    r2 = _log(store, _draft(), ids, clock)
    assert r2.verdict.value == "fixable"          # 2nd sighting promotes
    assert r2.status == Status.FIXABLE


def test_unknown_pattern_rejected_without_allow_new(tmp_path):
    store = _store(tmp_path)
    record_event(store, _draft("known-key"), allow_new=True,
                 clock=seq_clock(), id_factory=seq_ids())
    with pytest.raises(UnknownPattern):
        record_event(store, _draft("knwon-key"), allow_new=False,
                     clock=seq_clock(), id_factory=seq_ids("z"))


def test_wrap_up_is_idempotent(tmp_path):
    store = _store(tmp_path)
    ids, clock = seq_ids(), seq_clock()
    _log(store, _draft(), ids, clock)
    _log(store, _draft(), ids, clock)             # now fixable
    gw = FakeIssueGateway()

    r1 = wrap_up(store, gw, "2026-06-21-ski", repo="o/r",
                 recap_dir=str(tmp_path / "sessions"), clock=clock, id_factory=ids)
    assert len(r1.created) == 1 and len(gw.issues) == 1
    assert fold(store.read())["infra-leak-in-app"].status == Status.ISSUED
    assert os.path.exists(r1.recap_path)

    r2 = wrap_up(store, gw, "2026-06-21-ski", repo="o/r",
                 recap_dir=str(tmp_path / "sessions"), clock=clock, id_factory=ids)
    assert len(r2.created) == 0          # dedup: no duplicate
    assert len(gw.issues) == 1
    assert len(r2.commented) == 1        # recurrence commented instead


def test_wrap_up_aborts_when_github_unreachable(tmp_path):
    store = _store(tmp_path)
    ids, clock = seq_ids(), seq_clock()
    _log(store, _draft(), ids, clock)
    _log(store, _draft(), ids, clock)
    gw = FakeIssueGateway(raise_on_search=True)

    report = wrap_up(store, gw, "2026-06-21-ski", repo="o/r",
                     recap_dir=str(tmp_path / "sessions"), clock=clock, id_factory=ids)
    assert report.github_error is not None
    assert len(gw.issues) == 0           # never read a failed search as "safe to create"
    assert fold(store.read())["infra-leak-in-app"].status == Status.FIXABLE


def test_rebuild_is_lossless_from_log(tmp_path):
    store = _store(tmp_path)
    ids, clock = seq_ids(), seq_clock()
    _log(store, _draft(), ids, clock)
    _log(store, _draft(), ids, clock)
    wrap_up(store, FakeIssueGateway(), "2026-06-21-ski", repo="o/r",
            recap_dir=str(tmp_path / "sessions"), clock=clock, id_factory=ids)

    snapshot_before = store.read_snapshot()
    os.remove(store.patterns_path)        # nuke the cache
    rebuild(store)                        # reconstruct from events.jsonl alone
    snapshot_after = store.read_snapshot()
    assert snapshot_before == snapshot_after
    assert snapshot_after["infra-leak-in-app"]["status"] == "issued"
    assert snapshot_after["infra-leak-in-app"]["issue_url"]
