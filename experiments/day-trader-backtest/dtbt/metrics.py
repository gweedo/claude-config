"""S4: statistics over a list of run_day results."""

from collections import Counter


def summarize(results):
    trades = [r for r in results if r["status"] == "traded"]
    n = len(trades)
    equity = peak = dd = 0.0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {
        "days": len(results),
        "trades": n,
        "win_rate": round(sum(1 for t in trades if t["pnl"] > 0) / n, 4) if n else None,
        "avg_r": round(sum(t["r_multiple"] for t in trades) / n, 4) if n else None,
        "total_pnl": round(sum(t["pnl"] for t in trades), 2),
        "avg_pnl": round(sum(t["pnl"] for t in trades) / n, 2) if n else None,
        "max_drawdown": round(dd, 2),
        "exits": dict(Counter(t["reason"] for t in trades)),
        "skipped": dict(Counter(r["reason"].split(":")[0] for r in results if r["status"] != "traded")),
    }
