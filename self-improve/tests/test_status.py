"""next_status transition table, incl. the forbidden moves (DESIGN §5/§7)."""
from siloop.core.models import Status, Verdict
from siloop.core.status import next_status


def test_bare_verdict_passthrough():
    assert next_status(Verdict.CASUAL, False, False, False) == Status.CASUAL
    assert next_status(Verdict.FIXABLE, False, False, False) == Status.FIXABLE


def test_issued_wins_over_a_recomputed_casual():
    # forbidden move: a dropped count must NOT knock an issued pattern back (re-filing a dup)
    assert next_status(Verdict.CASUAL, issued=True, resolved=False, regressed=False) == Status.ISSUED


def test_resolved_beats_issued():
    assert next_status(Verdict.FIXABLE, issued=True, resolved=True, regressed=False) == Status.RESOLVED


def test_regression_reopens_to_fixable():
    assert next_status(Verdict.CASUAL, issued=True, resolved=True, regressed=True) == Status.FIXABLE
