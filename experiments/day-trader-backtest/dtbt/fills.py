"""S2: simulate one long bracket trade bar by bar.

Rules (agreed in grilling Q5):
- Buy at the open of the entry bar plus slippage. If that open is already at/below
  the stop or at/above the target, the plan no longer makes sense: no fill.
- Checked in this order on every bar from the entry bar on:
  1. bar starts at/after flat-by      -> market sell at its open (minus slippage)
  2. bar opens at/below the stop      -> gap: market sell at the (worse) open
  3. bar's low touches the stop       -> stop: stop price minus slippage
     (so a bar touching both stop and target counts as the stop: conservative)
  4. bar's high touches the target    -> limit: target, or the open if it gapped over
- Data ends first -> market sell at the last close.
"""


def _r2(x):
    return round(x + 1e-9, 2)


def simulate_trade(bars, entry_index, stop, target, flat_by_ts, qty, slippage_pct=0.02):
    slip = slippage_pct / 100.0
    first = bars[entry_index]["o"]
    if first <= stop or first >= target:
        return {"reason": "no_fill", "entry_price": None, "exit_price": None, "pnl": 0.0,
                "entry_ts": bars[entry_index]["t"], "exit_ts": None}
    entry = _r2(first * (1 + slip))
    exit_price = reason = exit_ts = None
    for b in bars[entry_index:]:
        if b["t"] >= flat_by_ts:
            exit_price, reason = _r2(b["o"] * (1 - slip)), "flat"
        elif b["o"] <= stop:
            exit_price, reason = _r2(b["o"] * (1 - slip)), "stop_gap"
        elif b["l"] <= stop:
            exit_price, reason = _r2(stop * (1 - slip)), "stop"
        elif b["h"] >= target:
            exit_price, reason = max(target, b["o"]), "target"
        if reason:
            exit_ts = b["t"]
            break
    if reason is None:
        last = bars[-1]
        exit_price, reason, exit_ts = _r2(last["c"] * (1 - slip)), "end_of_data", last["t"]
    pnl = _r2((exit_price - entry) * qty)
    return {"reason": reason, "entry_price": entry, "exit_price": exit_price, "pnl": pnl,
            "entry_ts": bars[entry_index]["t"], "exit_ts": exit_ts}
