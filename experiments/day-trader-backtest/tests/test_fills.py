"""S2: the fill simulator. Expected values are worked by hand, not recomputed."""

from dtbt.fills import simulate_trade


def bar(t, o, h, l, c):
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1000}


FLAT = 10_000  # flat-by timestamp, later than every bar unless a test says otherwise


def test_target_hit_exits_at_target_after_paying_entry_slippage():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 100.20, 101.50, 100.10, 101.30)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    # buy at 100.00 * 1.0002 = 100.02; target is a limit, no slippage: 101.00
    assert out["reason"] == "target"
    assert out["entry_price"] == 100.02
    assert out["exit_price"] == 101.00
    assert out["pnl"] == 9.80


def test_stop_hit_exits_at_stop_minus_slippage():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 100.20, 100.30, 98.90, 99.10)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    # stop is a market order once touched: 99.00 * 0.9998 = 98.9802 -> 98.98
    # pnl = (98.98 - 100.02) * 10 = -10.40
    assert out["reason"] == "stop"
    assert out["exit_price"] == 98.98
    assert out["pnl"] == -10.40


def test_gap_through_stop_fills_at_the_worse_open():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 98.50, 98.70, 98.20, 98.60)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    # opens below the stop: fills at 98.50 * 0.9998 = 98.4803 -> 98.48
    # pnl = (98.48 - 100.02) * 10 = -15.40
    assert out["reason"] == "stop_gap"
    assert out["exit_price"] == 98.48
    assert out["pnl"] == -15.40


def test_stop_and_target_in_the_same_bar_counts_as_the_stop():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 100.20, 101.50, 98.90, 100.00)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    assert out["reason"] == "stop"
    assert out["pnl"] == -10.40


def test_still_open_at_flat_by_sells_at_that_bars_open():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 100.20, 100.60, 100.00, 100.50),
            bar(600, 100.50, 100.90, 99.50, 99.60)]   # would hit nothing anyway
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=600, qty=10, slippage_pct=0.02)
    # market sell at the 600 bar's open: 100.50 * 0.9998 = 100.4799 -> 100.48
    # pnl = (100.48 - 100.02) * 10 = 4.60
    assert out["reason"] == "flat"
    assert out["exit_price"] == 100.48
    assert out["pnl"] == 4.60


def test_gap_over_target_fills_the_limit_at_the_better_open():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 101.40, 101.60, 101.20, 101.50)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    # pnl = (101.40 - 100.02) * 10 = 13.80
    assert out["reason"] == "target"
    assert out["exit_price"] == 101.40
    assert out["pnl"] == 13.80


def test_entry_bar_opening_below_the_stop_means_no_trade():
    bars = [bar(0, 98.80, 99.20, 98.50, 99.00)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    assert out["reason"] == "no_fill"
    assert out["pnl"] == 0.0


def test_entry_bar_opening_above_the_target_means_no_trade():
    bars = [bar(0, 101.20, 101.50, 101.00, 101.30)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    assert out["reason"] == "no_fill"
    assert out["pnl"] == 0.0


def test_data_ending_before_flat_by_sells_at_the_last_close():
    bars = [bar(0, 100.00, 100.40, 99.80, 100.20),
            bar(300, 100.20, 100.60, 100.00, 100.50)]
    out = simulate_trade(bars, entry_index=0, stop=99.00, target=101.00,
                         flat_by_ts=FLAT, qty=10, slippage_pct=0.02)
    # 100.50 * 0.9998 = 100.4799 -> 100.48; pnl = 4.60
    assert out["reason"] == "end_of_data"
    assert out["exit_price"] == 100.48
    assert out["pnl"] == 4.60
