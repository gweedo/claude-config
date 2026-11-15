"""S1: the scenario generator. Bad fake data would silently make every result meaningless."""

import datetime

import pytest

from dtbt import skill
from dtbt.generator import generate, SCENARIOS

ALL = sorted(SCENARIOS)


def et(t):
    e = skill.entry()
    return e.to_eastern(e.utc_of(t))


def test_the_eight_agreed_scenarios_exist():
    assert ALL == sorted(["trend_up", "trend_down", "choppy", "gap_up", "gap_down",
                          "crash", "quiet", "bootstrap"])


@pytest.mark.parametrize("name", ALL)
def test_same_seed_gives_identical_days_and_another_seed_does_not(name):
    a = generate(name, seed=7, days=3)
    assert a == generate(name, seed=7, days=3)
    assert a != generate(name, seed=8, days=3)


@pytest.mark.parametrize("name", ALL)
def test_every_day_is_a_full_nyse_session_of_sane_5_minute_bars(name):
    entry = skill.entry()
    for chart in generate(name, seed=1, days=5):
        bars = chart["bars"]
        assert len(bars) == 78
        first, last = et(bars[0]["t"]), et(bars[-1]["t"])
        assert (first.hour, first.minute) == (9, 30)
        assert (last.hour, last.minute) == (15, 55)
        assert entry.trading_day(first.date())[0]
        assert all(b2["t"] - b1["t"] == 300 for b1, b2 in zip(bars, bars[1:]))
        for b in bars:
            assert b["l"] <= min(b["o"], b["c"]) <= max(b["o"], b["c"]) <= b["h"]
            assert b["l"] > 0 and b["v"] > 0
            assert all(round(b[k], 2) == b[k] for k in "ohlc")


def test_days_are_consecutive_trading_days_starting_2026_01_02():
    days = [et(c["bars"][0]["t"]).date() for c in generate("quiet", seed=1, days=4)]
    # 2026-01-02 is a Friday; Monday 2026-01-05 follows
    assert days == [datetime.date(2026, 1, 2), datetime.date(2026, 1, 5),
                    datetime.date(2026, 1, 6), datetime.date(2026, 1, 7)]


def test_gap_up_days_open_3_percent_over_the_previous_close():
    for c in generate("gap_up", seed=3, days=10):
        assert c["bars"][0]["o"] == pytest.approx(c["prev_close"] * 1.03, abs=0.011)


def test_gap_down_days_open_3_percent_under_the_previous_close():
    for c in generate("gap_down", seed=3, days=10):
        assert c["bars"][0]["o"] == pytest.approx(c["prev_close"] * 0.97, abs=0.011)


def day_return(c):
    return c["bars"][-1]["c"] / c["bars"][0]["o"] - 1


def day_range(c):
    return max(b["h"] for b in c["bars"]) / min(b["l"] for b in c["bars"]) - 1


def test_trend_days_move_in_their_direction_on_average():
    up = generate("trend_up", seed=5, days=60)
    down = generate("trend_down", seed=5, days=60)
    assert sum(map(day_return, up)) / 60 > 0.01
    assert sum(map(day_return, down)) / 60 < -0.01


def test_quiet_days_have_a_much_smaller_range_than_choppy_days():
    quiet = sum(map(day_range, generate("quiet", seed=5, days=30))) / 30
    choppy = sum(map(day_range, generate("choppy", seed=5, days=30))) / 30
    assert quiet < choppy / 2


def test_crash_days_contain_a_drop_of_at_least_5_percent_within_15_minutes():
    for c in generate("crash", seed=9, days=10):
        closes = [b["c"] for b in c["bars"]]
        worst = min(closes[i + 3] / closes[i] - 1 for i in range(len(closes) - 3))
        assert worst <= -0.05


def test_bootstrap_bars_are_real_tsla_moves_at_the_same_time_of_day():
    from dtbt.generator import _tsla_sessions
    real = _tsla_sessions()
    assert len(real) >= 50                       # the fixture's ~59 sessions
    for c in generate("bootstrap", seed=2, days=3):
        prev = c["prev_close"]
        for slot, b in enumerate(c["bars"]):
            move = b["c"] / prev
            # some real session's bar at this slot made the same close-to-close move
            # (to within the cent rounding of a ~$350 price)
            assert min(abs(s[slot][3] - move) for s in real) < 0.0001
            prev = b["c"]
