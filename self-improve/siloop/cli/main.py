"""`loop` CLI — a thin argparse adapter over the core use cases (PROTOCOL §8).

Commands: log, list, promote, retract, resolve, wrap-up, rebuild.
Storage location: $SILOOP_HOME (default: current directory).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from ..core import patterns as pattern_match
from ..core.fold import fold
from ..core.loop import (
    EventDraft,
    UnknownPattern,
    promote,
    record_event,
    rebuild,
    resolve,
    retract,
    wrap_up,
)
from ..core.models import FixType, SignalType, Status
from ..core.ports import IssueRef
from ..core.store import EventLog


def _store(home: str) -> EventLog:
    return EventLog(os.path.join(home, "events.jsonl"), os.path.join(home, "patterns.json"))


class _NullGateway:
    """Offline stand-in for --dry-run without a token: assumes no issue exists yet."""

    def ensure_labels(self, repo, labels): pass
    def open_issue_for(self, repo, pattern_key): return None
    def file_issue(self, repo, payload): return IssueRef(url="(dry-run)", number=0, state="open")
    def comment(self, ref, body): pass


def _gateway(dry_run: bool):
    if dry_run:
        return _NullGateway()
    from ..adapters.github import GithubGateway  # imported lazily so core stays offline
    return GithubGateway()


def _cmd_log(args, home) -> int:
    store = _store(home)
    draft = EventDraft(
        session_id=args.session,
        pattern_key=args.pattern,
        type=SignalType(args.type),
        title=args.title,
        summary=args.summary,
        root_cause=args.root_cause,
        severity=args.severity,
        fix_type=FixType(args.fix_type),
        proposed_fix=args.fix,
        affected_paths=args.paths or [],
    )
    try:
        result = record_event(store, draft, allow_new=args.new_pattern)
    except UnknownPattern as exc:
        print("unknown pattern_key {!r}. closest existing keys:".format(exc.key))
        for k in exc.suggestions:
            print("  - {}".format(k))
        print("pass --new-pattern to confirm a genuinely new one.")
        return 2
    flag = " [NEW PATTERN]" if result.is_new_pattern else ""
    print("logged {} -> verdict={} | pattern status={}{}".format(
        result.event.pattern_key, result.verdict.value, result.status.value, flag))
    return 0


def _cmd_list(args, home) -> int:
    store = _store(home)
    rollup = fold(store.read())
    rows = sorted(rollup.values(), key=lambda p: (-p.count, p.pattern_key))
    for p in rows:
        if args.status and p.status.value != args.status:
            continue
        if args.pattern and p.pattern_key != args.pattern:
            continue
        if args.unissued and not (p.status == Status.FIXABLE and p.issue_url is None):
            continue
        url = " -> {}".format(p.issue_url) if p.issue_url else ""
        print("{:<32} {:<8} {}x  sev{}{}".format(
            p.pattern_key, p.status.value, p.count, p.max_severity, url))
    return 0


def _cmd_promote(args, home) -> int:
    promote(_store(home), args.event_id, args.reason)
    print("promoted (override appended).")
    return 0


def _cmd_retract(args, home) -> int:
    try:
        retract(_store(home), args.event_id, args.reason, force=args.force)
    except ValueError as exc:
        print(str(exc)); return 2
    print("retracted (tombstone appended).")
    return 0


def _cmd_resolve(args, home) -> int:
    resolve(_store(home), args.pattern_key, args.reason)
    print("resolved {}.".format(args.pattern_key))
    return 0


def _cmd_wrapup(args, home) -> int:
    store = _store(home)
    gateway = _gateway(args.dry_run)
    report = wrap_up(store, gateway, session_id=args.session,
                     repo=args.issue_repo or args.repo,
                     recap_dir=os.path.join(home, "sessions"), dry_run=args.dry_run)
    if report.github_error:
        print(report.github_error); return 1
    print("recap: {}".format(report.recap_path))
    for key, url in report.created:
        print("  issue: {} -> {}".format(key, url))
    for key, url in report.commented:
        print("  comment (recurred): {} -> {}".format(key, url))
    for key in report.regressions:
        print("  REGRESSION re-opened: {}".format(key))
    return 0


def _cmd_rebuild(args, home) -> int:
    rebuild(_store(home))
    print("patterns.json rebuilt from events.jsonl.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="loop", description="self-improvement loop")
    p.add_argument("--home", default=os.environ.get("SILOOP_HOME", "."),
                   help="storage dir (default $SILOOP_HOME or cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log", help="append an approved event")
    lg.add_argument("--type", required=True, choices=[t.value for t in SignalType])
    lg.add_argument("--pattern", required=True)
    lg.add_argument("--title", required=True)
    lg.add_argument("--summary", default="")
    lg.add_argument("--root-cause", dest="root_cause", default="")
    lg.add_argument("--severity", type=int, choices=[1, 2, 3], required=True)
    lg.add_argument("--fix-type", dest="fix_type", required=True,
                    choices=[f.value for f in FixType])
    lg.add_argument("--fix", dest="fix", default="")
    lg.add_argument("--paths", nargs="*", default=[])
    lg.add_argument("--session", required=True)
    lg.add_argument("--new-pattern", dest="new_pattern", action="store_true")
    lg.set_defaults(func=_cmd_log)

    ls = sub.add_parser("list", help="review patterns")
    ls.add_argument("--status", choices=[s.value for s in Status])
    ls.add_argument("--session")
    ls.add_argument("--pattern")
    ls.add_argument("--unissued", action="store_true")
    ls.set_defaults(func=_cmd_list)

    pr = sub.add_parser("promote")
    pr.add_argument("event_id"); pr.add_argument("--reason", required=True)
    pr.set_defaults(func=_cmd_promote)

    rt = sub.add_parser("retract")
    rt.add_argument("event_id"); rt.add_argument("--reason", required=True)
    rt.add_argument("--force", action="store_true")
    rt.set_defaults(func=_cmd_retract)

    rs = sub.add_parser("resolve")
    rs.add_argument("pattern_key"); rs.add_argument("--reason", required=True)
    rs.set_defaults(func=_cmd_resolve)

    wu = sub.add_parser("wrap-up")
    wu.add_argument("--session", required=True)
    wu.add_argument("--repo", required=True)
    wu.add_argument("--issue-repo", dest="issue_repo")
    wu.add_argument("--dry-run", dest="dry_run", action="store_true")
    wu.set_defaults(func=_cmd_wrapup)

    rb = sub.add_parser("rebuild")
    rb.set_defaults(func=_cmd_rebuild)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args, args.home)


if __name__ == "__main__":
    sys.exit(main())
