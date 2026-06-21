"""classify boundary corners (DESIGN §11 T1): count 1<->2 x severity 2<->3."""
from siloop.core.classify import classify
from siloop.core.models import Verdict


def test_first_sighting_low_severity_is_casual():
    assert classify(severity=1, count=1) == Verdict.CASUAL
    assert classify(severity=2, count=1) == Verdict.CASUAL  # sev 2 is NOT auto-fixable


def test_severity_three_is_fixable_on_a_one_off():
    assert classify(severity=3, count=1) == Verdict.FIXABLE


def test_recurrence_promotes_at_count_two():
    assert classify(severity=1, count=2) == Verdict.FIXABLE


def test_both_conditions_true():
    assert classify(severity=3, count=2) == Verdict.FIXABLE
