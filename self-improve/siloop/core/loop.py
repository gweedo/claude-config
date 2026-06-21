"""Use cases both adapters (CLI now, FastAPI later) call. Orchestration lives here, so the
adapters stay thin (DESIGN §2/§8). Pure functions and injected ports do the real work.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from . import patterns as pattern_match
from .classify import classify
from .fold import _tombstoned_signal_ids, fold
from .issues import build_issue
from .models import (
    FixType,
    IssueFiledEvent,
    OverrideEvent,
    Pattern,
    ResolvedEvent,
    SignalEvent,
    SignalType,
    Status,
    TombstoneEvent,
    Verdict,
)
from .ports import IssueGateway
from .recap import IssueLine, LoggedLine, SessionView, WatchLine, build_recap
from .store import EventLog


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class UnknownPattern(ValueError):
    def __init__(self, key: str, suggestions: List[str]) -> None:
        self.key = key
        self.suggestions = suggestions
        super().__init__(
            "unknown pattern_key {!r}; closest: {} (pass allow_new=True to confirm a new one)".format(
                key, ", ".join(suggestions) or "(none yet)"
            )
        )


@dataclass
class EventDraft:
    session_id: str
    pattern_key: str
    type: SignalType
    title: str
    summary: str
    root_cause: str
    severity: int
    fix_type: FixType
    proposed_fix: str
    affected_paths: List[str] = field(default_factory=list)


@dataclass
class RecordResult:
    event: SignalEvent
    verdict: Verdict
    status: Status
    is_new_pattern: bool


@dataclass
class WrapUpReport:
    session_id: str
    created: List[tuple] = field(default_factory=list)      # (pattern_key, url)
    commented: List[tuple] = field(default_factory=list)    # (pattern_key, url)
    regressions: List[str] = field(default_factory=list)
    watching: List[str] = field(default_factory=list)
    recap_path: Optional[str] = None
    dry_run: bool = False
    github_error: Optional[str] = None


def rebuild(store: EventLog) -> Dict[str, Pattern]:
    rollup = fold(store.read())
    store.write_snapshot(rollup)
    return rollup


# --- capture ---------------------------------------------------------------

def record_event(
    store: EventLog,
    draft: EventDraft,
    allow_new: bool = False,
    matcher=pattern_match,
    clock: Callable[[], str] = _utc_now,
    id_factory: Callable[[], str] = _uuid,
) -> RecordResult:
    existing = store.read()
    rollup = fold(existing)
    known = list(rollup.keys())

    is_new = draft.pattern_key not in known
    if is_new and not allow_new:
        raise UnknownPattern(draft.pattern_key, matcher.suggest_keys(draft.pattern_key, known))

    prior_count = rollup[draft.pattern_key].count if draft.pattern_key in rollup else 0
    count = prior_count + 1
    verdict = classify(draft.severity, count)

    event = SignalEvent(
        id=id_factory(),
        ts=clock(),
        session_id=draft.session_id,
        pattern_key=draft.pattern_key,
        type=draft.type,
        title=draft.title,
        summary=draft.summary,
        root_cause=draft.root_cause,
        severity=draft.severity,
        verdict=verdict,
        fix_type=draft.fix_type,
        proposed_fix=draft.proposed_fix,
        affected_paths=list(draft.affected_paths),
    )
    store.append(event)
    new_rollup = rebuild(store)
    return RecordResult(
        event=event,
        verdict=verdict,
        status=new_rollup[draft.pattern_key].status,
        is_new_pattern=is_new,
    )


# --- corrections / lifecycle ----------------------------------------------

def promote(store, target_event_id, reason, clock=_utc_now, id_factory=_uuid):
    store.append(OverrideEvent(id=id_factory(), ts=clock(),
                               target_event_id=target_event_id,
                               verdict=Verdict.FIXABLE, reason=reason))
    return rebuild(store)


def retract(store, target_event_id, reason, force=False, clock=_utc_now, id_factory=_uuid):
    events = store.read()
    rollup = fold(events)
    # refuse to demote a currently-issued pattern unless forced (PROTOCOL §9)
    sig = next((e for e in events if isinstance(e, SignalEvent) and e.id == target_event_id), None)
    if sig is not None and not force:
        p = rollup.get(sig.pattern_key)
        if p is not None and p.status == Status.ISSUED:
            raise ValueError(
                "refusing to retract: pattern {!r} is issued ({}); pass force=True".format(
                    sig.pattern_key, p.issue_url
                )
            )
    store.append(TombstoneEvent(id=id_factory(), ts=clock(),
                                target_event_id=target_event_id, reason=reason))
    return rebuild(store)


def resolve(store, pattern_key, reason, clock=_utc_now, id_factory=_uuid):
    store.append(ResolvedEvent(id=id_factory(), ts=clock(),
                               pattern_key=pattern_key, reason=reason))
    return rebuild(store)


# --- wrap-up ---------------------------------------------------------------

def _latest_signal_by_key(events) -> Dict[str, SignalEvent]:
    retracted = _tombstoned_signal_ids(events)
    latest: Dict[str, SignalEvent] = {}
    for e in events:
        if isinstance(e, SignalEvent) and e.id not in retracted:
            cur = latest.get(e.pattern_key)
            if cur is None or e.ts > cur.ts:
                latest[e.pattern_key] = e
    return latest


def wrap_up(
    store: EventLog,
    gateway: IssueGateway,
    session_id: str,
    repo: str,
    recap_dir: Optional[str] = None,
    dry_run: bool = False,
    clock: Callable[[], str] = _utc_now,
    id_factory: Callable[[], str] = _uuid,
) -> WrapUpReport:
    events = store.read()
    rollup = rebuild(store)
    latest = _latest_signal_by_key(events)

    # patterns touched this session
    session_keys = {
        e.pattern_key
        for e in events
        if isinstance(e, SignalEvent) and e.session_id == session_id and e.pattern_key in rollup
    }

    report = WrapUpReport(session_id=session_id, dry_run=dry_run)

    # ----- phase 1: decide (dedup via live search). A search failure aborts before any create.
    to_create: List[str] = []
    to_comment: List[tuple] = []  # (key, IssueRef)
    try:
        for key in sorted(session_keys):
            p = rollup[key]
            if p.status == Status.FIXABLE:
                existing = gateway.open_issue_for(repo, key)
                if existing is None:
                    to_create.append(key)
                else:
                    to_comment.append((key, existing))
            elif p.status == Status.ISSUED:
                existing = gateway.open_issue_for(repo, key)
                if existing is not None:
                    to_comment.append((key, existing))
    except Exception as exc:  # pragma: no cover - exercised via fake raising
        report.github_error = "GitHub unreachable - recap written, 0 issues created, rerun later ({})".format(exc)
        to_create, to_comment = [], []

    # ----- phase 2: create (skipped on dry-run or github error)
    if not dry_run and report.github_error is None:
        labels_repo_done = set()
        for key in to_create:
            p = rollup[key]
            sig = latest[key]
            payload = build_issue(
                pattern=p,
                title=sig.title,
                root_cause=sig.root_cause,
                proposed_fix=sig.proposed_fix,
                session_id=session_id,
                affected_paths=sig.affected_paths,
            )
            if repo not in labels_repo_done:
                gateway.ensure_labels(repo, payload.labels)
                labels_repo_done.add(repo)
            ref = gateway.file_issue(repo, payload)
            store.append(IssueFiledEvent(id=id_factory(), ts=clock(),
                                         pattern_key=key, issue_url=ref.url, repo=repo))
            report.created.append((key, ref.url))
        for key, ref in to_comment:
            gateway.comment(ref, "Recurred in session {} - pattern now seen {}x.".format(
                session_id, rollup[key].count))
            report.commented.append((key, ref.url))
        rollup = rebuild(store)
    else:
        # still surface what WOULD happen
        for key in to_create:
            report.created.append((key, "(dry-run)"))
        for key, ref in to_comment:
            report.commented.append((key, ref.url))

    # ----- regressions + watching (for the recap)
    for key in sorted(session_keys):
        p = rollup[key]
        sig = latest.get(key)
        # a regression is a re-opened pattern that had been resolved
        resolved_before = any(
            isinstance(e, ResolvedEvent) and e.pattern_key == key for e in events
        )
        if resolved_before and p.status == Status.FIXABLE:
            report.regressions.append(key)
        if p.status == Status.CASUAL:
            report.watching.append(key)

    # ----- recap
    view = _build_session_view(session_id, session_keys, rollup, latest, report)
    recap_text = build_recap(view)
    if recap_dir is not None:
        os.makedirs(recap_dir, exist_ok=True)
        path = os.path.join(recap_dir, session_id + ".md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(recap_text)
        report.recap_path = path
    return report


def _build_session_view(session_id, session_keys, rollup, latest, report) -> SessionView:
    logged = []
    for key in sorted(session_keys):
        p = rollup[key]
        sig = latest.get(key)
        verdict = Verdict.CASUAL if p.status == Status.CASUAL else Verdict.FIXABLE
        logged.append(LoggedLine(
            signal_type=sig.type if sig else SignalType.CODE_FAILURE,
            pattern_key=key,
            severity=p.max_severity,
            verdict=verdict,
            count=p.count,
        ))
    promoted = []
    for key, url in report.created:
        p = rollup[key]
        from .models import FIX_LABELS  # local import to avoid cycle at module load
        label = FIX_LABELS.get(p.fix_type, "fix:instructions")
        title = latest[key].title if key in latest else key
        promoted.append(IssueLine(pattern_key=key, label=label, title=title, url=url))
    watching = [WatchLine(pattern_key=k, count=rollup[k].count) for k in report.watching]
    return SessionView(
        session_id=session_id,
        logged=logged,
        promoted=promoted,
        watching=watching,
        regressions=list(report.regressions),
    )
