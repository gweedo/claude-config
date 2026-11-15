"""S3: one trading day through day-trader-skill's own tools.

entry.evaluate -> exit.compute -> budget.size_trade/bracket_order -> risk.check -> fills.simulate_trade

The skill's functions are called directly (grilling Q11). The README reel test proves the
wiring reproduces the CLI's numbers.
"""

import datetime
from dataclasses import dataclass, field

from dtbt import skill
from dtbt.fills import simulate_trade


@dataclass
class Settings:
    or_minutes: int = 15
    stop: str = "or-mid"          # or-mid | or-low | atr:K | pct:X
    target: str = "1R"            # 1R, 1.5R, 2R ...
    slippage_pct: float = 0.02
    budget: float = 5000.0
    max_loss_per_trade_usd: float = 50.0
    extra_cfg: dict = field(default_factory=dict)

    def cfg(self):
        c = {"budget": self.budget, "max_loss_per_trade_usd": self.max_loss_per_trade_usd}
        c.update(self.extra_cfg)
        return c


@dataclass
class Account:
    cash: float
    state: dict = field(default_factory=lambda: {"orders": []})   # trader/state/broker.json shape


def session_day(chart):
    e = skill.entry()
    return e.to_eastern(e.utc_of(chart["bars"][0]["t"])).date()


def _utc_at(day, hh, mm):
    return skill.entry().eastern_to_utc(datetime.datetime.combine(day, datetime.time(hh, mm)))


def no_trade(reason, **extra):
    out = {"status": "no_trade", "reason": reason, "pnl": 0.0}
    out.update(extra)
    return out


def run_day(chart, settings, account, entry_override=None):
    """One session. entry_override=(trigger_slot, entry_price) replaces trader-entry's
    signal (used by the random-entry control); everything downstream is identical."""
    E, X, B, R = skill.entry(), skill.exit_(), skill.budget(), skill.risk()
    cfg = settings.cfg()
    day = session_day(chart)
    bars = X.session_bars(chart, day, "5m", now_utc=_utc_at(day, 16, 0))
    n_or = settings.or_minutes // 5
    if len(bars) <= n_or:
        return no_trade("not enough bars")
    or_high = round(max(b["h"] for b in bars[:n_or]), 2)
    or_low = round(min(b["l"] for b in bars[:n_or]), 2)
    orr = {"high": or_high, "low": or_low}

    if entry_override is None:
        res = E.evaluate(chart, _utc_at(day, 16, 0), setup="orb", or_minutes=settings.or_minutes)
        if res["status"] != "triggered":
            return no_trade("entry: %s" % res["reason"], opening_range=orr)
        slot, entry_price = res["trigger"]["bar_index"], res["trigger"]["price"]
    else:
        slot, entry_price = entry_override
    trig_end = E.to_eastern(E.utc_of(bars[slot]["t"])) + datetime.timedelta(minutes=5)
    trigger_time = trig_end.strftime("%H:%M")

    stop_rule, stop_param = X.parse_stop(settings.stop)
    target_rule, target_param = X.parse_target(settings.target)
    atr = atr_n = None
    if stop_rule == "atr":
        atr, atr_n = X.atr_of(bars[:slot + 1])
    try:
        c = X.compute(entry_price, stop_rule, stop_param, target_rule, target_param,
                      or_high, or_low, atr, atr_n)
        flat_by, _ = X.resolve_flat_by(day, None, X.DEFAULTS, trig_end.time())
    except X.PlanError as exc:
        return no_trade("exit: %s" % exc, opening_range=orr, trigger_time=trigger_time)
    plan = {"symbol": chart["symbol"], "side": "buy", "date": day.isoformat(), "setup": "orb",
            "entry": float(c["entry"]), "stop": float(c["stop"]), "target": float(c["target"]),
            "entry_time": trigger_time, "flat_by": flat_by,
            "stop_label": c["stop_label"], "target_label": c["target_label"]}

    try:
        s = B.size_trade(plan, cfg, cash=account.cash, today=day.isoformat())
    except B.SizeError as exc:
        return no_trade("budget: %s" % exc, opening_range=orr, trigger_time=trigger_time, plan=plan)
    order = B.bracket_order(s)
    if order is None:
        return no_trade("budget: %s" % s["refusal"], opening_range=orr, trigger_time=trigger_time, plan=plan)

    verdict = R.check([order], cfg, portfolio={"cash": account.cash, "positions": []},
                      prices={plan["symbol"]: plan["entry"]}, state=account.state,
                      today=day.isoformat(), now=E.eastern_to_utc(trig_end))
    r0 = verdict["results"][0]
    common = dict(opening_range=orr, trigger_time=trigger_time, plan=plan, qty=s["qty"],
                  max_loss=s["max_loss"], risk_verdict=r0["verdict"])
    if r0["verdict"] != "PASS":
        return no_trade("risk: %s" % "; ".join(r0.get("reasons") or []), **common)

    entry_index = slot + 1
    if entry_index >= len(bars):
        return no_trade("no bar left to enter on", **common)
    fh, fm = map(int, flat_by.split(":"))
    flat_ts = E.ts_of(_utc_at(day, fh, fm))
    fill = simulate_trade(bars, entry_index, plan["stop"], plan["target"], flat_ts, s["qty"],
                          settings.slippage_pct)
    if fill["reason"] == "no_fill":
        return no_trade("fill: next bar opened past the stop or target", **common)
    risk_usd = s["qty"] * (fill["entry_price"] - plan["stop"])
    out = dict(status="traded", reason=fill["reason"], pnl=fill["pnl"], fill=fill,
               r_multiple=round(fill["pnl"] / risk_usd, 3) if risk_usd > 0 else 0.0, **common)
    return out
