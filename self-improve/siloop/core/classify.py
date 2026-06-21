"""The recurrence + severity rule (DESIGN §5, PROTOCOL §4).

    fixable  <=  count >= THRESHOLD   OR   severity == SEVERITY_CEILING
    casual   <=  otherwise

Both constants are tunable in one place. `classify` is a total function of two ints.
"""
from __future__ import annotations

from .models import Verdict

THRESHOLD = 2          # second sighting promotes casual -> fixable
SEVERITY_CEILING = 3   # a sev-3 one-off is fixable immediately


def classify(severity: int, count: int) -> Verdict:
    if severity >= SEVERITY_CEILING or count >= THRESHOLD:
        return Verdict.FIXABLE
    return Verdict.CASUAL
