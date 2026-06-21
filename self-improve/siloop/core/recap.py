"""build_recap(SessionView) -> markdown.

A pure renderer. It re-derives nothing — no counts, no thresholds, no classification.
`wrap_up` resolves everything into a `SessionView` first (DESIGN §5); recap only formats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import SignalType, Verdict

_SIGNAL_ICON = {
    SignalType.CODE_FAILURE: "[code_failure]",
    SignalType.MISUNDERSTOOD_INTENT: "[misunderstood_intent]",
    SignalType.WRONG_APPROACH: "[wrong_approach]",
    SignalType.REPEATED_CORRECTION: "[repeated_correction]",
}


@dataclass
class LoggedLine:
    signal_type: SignalType
    pattern_key: str
    severity: int
    verdict: Verdict
    count: int


@dataclass
class IssueLine:
    pattern_key: str
    label: str
    title: str
    url: str


@dataclass
class WatchLine:
    pattern_key: str
    count: int


@dataclass
class SessionView:
    session_id: str
    logged: List[LoggedLine] = field(default_factory=list)
    promoted: List[IssueLine] = field(default_factory=list)
    watching: List[WatchLine] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)


def build_recap(view: SessionView) -> str:
    lines = ["# Session {} - recap".format(view.session_id), ""]

    lines.append("## Logged this session ({})".format(len(view.logged)))
    for x in view.logged:
        badge = (
            "**fixable ({}x)**".format(x.count)
            if x.verdict == Verdict.FIXABLE
            else "casual ({}x)".format(x.count)
        )
        lines.append(
            "- {} `{}` - sev {} - {}".format(
                _SIGNAL_ICON.get(x.signal_type, str(x.signal_type)),
                x.pattern_key,
                x.severity,
                badge,
            )
        )
    lines.append("")

    if view.regressions:
        lines.append("## Regressions ({})".format(len(view.regressions)))
        for key in view.regressions:
            lines.append("- WARNING `{}` recurred after being resolved - re-opened".format(key))
        lines.append("")

    lines.append("## Promoted to issues ({})".format(len(view.promoted)))
    for x in view.promoted:
        lines.append("- {} [{}] {}".format(x.url, x.label, x.title))
    lines.append("")

    lines.append("## Still casual / watching ({})".format(len(view.watching)))
    if view.watching:
        lines.append(
            ", ".join("`{}` ({}x)".format(w.pattern_key, w.count) for w in view.watching)
        )
    lines.append("")

    return "\n".join(lines)
