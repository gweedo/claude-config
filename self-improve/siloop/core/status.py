"""The pattern status transition table (DESIGN §5/§7).

`next_status` is the ONE place that knows the forbidden moves:

* a recomputed `fixable` must NOT knock an `issued` pattern back to `fixable` (which
  would re-file a duplicate issue) — so `issued` wins over a bare verdict;
* a signal event landing on a `resolved` pattern is a **regression** and re-opens it to
  `fixable` (the "no regression in a follow-up session" criterion, DESIGN §6).

The booleans are computed by `fold()` from the log; this function just encodes the
precedence so it can be unit-tested exhaustively.
"""
from __future__ import annotations

from .models import Status, Verdict


def next_status(verdict: Verdict, issued: bool, resolved: bool, regressed: bool) -> Status:
    if regressed:
        return Status.FIXABLE      # re-opened: a new signal hit a resolved pattern
    if resolved:
        return Status.RESOLVED
    if issued:
        return Status.ISSUED       # stays issued even if the bare verdict is casual
    return Status(verdict.value)   # casual | fixable
