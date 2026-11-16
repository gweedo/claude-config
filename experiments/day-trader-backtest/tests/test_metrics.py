"""S4: statistics. Worked examples by hand."""

from dtbt.metrics import summarize


def traded(pnl, r, reason="target"):
    return {"status": "traded", "pnl": pnl, "r_multiple": r, "reason": reason}


def skipped(reason):
    return {"status": "no_trade", "pnl": 0.0, "reason": reason}


def test_worked_example_of_five_trades_and_two_skipped_days():
    results = [traded(10, 1.0), skipped("entry: no close above"), traded(-5, -0.5, "stop"),
               traded(-5, -0.5, "stop"), skipped("risk: daily loss"), traded(20, 2.0),
               traded(-15, -1.5, "stop_gap")]
    s = summarize(results)
    # equity after each trade: 10, 5, 0, 20, 5 -> worst peak-to-trough is 20 -> 5 = 15
    assert s["days"] == 7
    assert s["trades"] == 5
    assert s["win_rate"] == 0.4
    assert s["avg_r"] == 0.1          # (1 - .5 - .5 + 2 - 1.5) / 5
    assert s["total_pnl"] == 5.0
    assert s["max_drawdown"] == 15.0
    assert s["exits"] == {"target": 2, "stop": 2, "stop_gap": 1}
    assert s["skipped"] == {"entry": 1, "risk": 1}


def test_no_trades_at_all():
    s = summarize([skipped("entry: x"), skipped("entry: y")])
    assert s["trades"] == 0
    assert s["win_rate"] is None
    assert s["avg_r"] is None
    assert s["total_pnl"] == 0.0
    assert s["max_drawdown"] == 0.0
    assert s["skipped"] == {"entry": 2}
