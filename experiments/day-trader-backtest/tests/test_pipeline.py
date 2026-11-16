"""S3: one trading day through the skill's own entry -> exit -> budget -> risk.

The source of truth for the reel test is the skill's README ("the trade in the reel"),
not this harness.
"""

import os

from dtbt import skill
from dtbt.pipeline import run_day, Settings, Account


def load_reel_chart():
    path = os.path.join(skill.FIXTURES, "trader-entry", "TSLA-2026-10-19-5m.json")
    with open(path, encoding="utf-8") as fh:
        return skill.entry().parse_chart(fh.read(), "TSLA")


def test_reproduces_the_readme_tsla_reel():
    out = run_day(load_reel_chart(), Settings(), Account(cash=5000.0))
    # README: range 354.47-362.18, first 5-minute close above it at 10:15 = 364.18,
    # stop at the range midpoint 358.32, target 1R 370.04, 8 shares, max loss $46.88.
    assert out["status"] == "traded"
    assert out["opening_range"] == {"high": 362.18, "low": 354.47}
    assert out["trigger_time"] == "10:15"
    assert out["plan"]["entry"] == 364.18
    assert out["plan"]["stop"] == 358.32
    assert out["plan"]["target"] == 370.04
    assert out["qty"] == 8
    assert out["max_loss"] == 46.88
    assert out["risk_verdict"] == "PASS"


def capped(chart, cap):
    """The reel day with every bar after the opening range held under `cap`."""
    first = chart["bars"][0]["t"]
    bars = []
    for b in chart["bars"]:
        if b["t"] >= first + 15 * 60:
            b = dict(b, h=min(b["h"], cap), c=min(b["c"], cap), o=min(b["o"], cap), l=min(b["l"], cap))
        bars.append(b)
    return dict(chart, bars=bars)


def test_no_close_above_the_range_means_no_trade():
    out = run_day(capped(load_reel_chart(), 360.00), Settings(), Account(cash=5000.0))
    assert out["status"] == "no_trade"
    assert out["reason"].startswith("entry:")
    assert out["pnl"] == 0.0


def test_daily_loss_limit_already_used_makes_risk_block_the_trade():
    # two entries placed earlier today, $60 max loss each = $120; this one adds $46.88 > $150 limit
    earlier = [{"status": "placed", "date": "2026-10-19", "kind": "entry", "symbol": s,
                "side": "buy", "max_loss": 60.0} for s in ("AAPL", "MSFT")]
    out = run_day(load_reel_chart(), Settings(), Account(cash=5000.0, state={"orders": earlier}))
    assert out["status"] == "no_trade"
    assert out["risk_verdict"] == "BLOCK"
    assert "daily" in out["reason"].lower()
