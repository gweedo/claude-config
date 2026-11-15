"""S1: fake trading days in the shape trader-entry's parse_chart returns.

Each day is a full NYSE session (78 five-minute bars, 9:30-15:55 bar starts) on a real 2026
trading date (early-close days skipped). Days are independent: each starts from its own
previous close around $350 (a TSLA-like price, so the skill's sizing limits bind as in its README).

Scenario parameters (agreed in grilling Q4):

| scenario   | open gap         | daily vol | intraday shape                          |
|------------|------------------|-----------|-----------------------------------------|
| trend_up   | N(0, 0.4%)       | 2.0%      | +1.5% drift over the session            |
| trend_down | N(0, 0.4%)       | 2.0%      | -1.5% drift over the session            |
| choppy     | N(0, 0.4%)       | 3.0%      | mean-reverts to the open (~70 min)      |
| gap_up     | exactly +3%      | 3.0%      | no drift                                |
| gap_down   | exactly -3%      | 3.0%      | no drift                                |
| crash      | N(0, 0.4%)       | 2.5%      | -6% over 3 bars starting 11:00-14:00    |
| quiet      | N(0, 0.2%)       | 0.6%      | no drift                                |
| bootstrap  | real TSLA gaps   | real      | each bar copied (relative to the prior  |
|            |                  |           | close) from a random real TSLA session  |
|            |                  |           | at the same time of day                 |
"""

import datetime
import gzip
import math
import os
import random

from dtbt import skill

BARS = 78
SUB = 5                      # one-minute steps inside each 5-minute bar
BASE_PRICE = 350.0
START = datetime.date(2026, 1, 2)

SCENARIOS = {
    "trend_up":   dict(gap_sd=0.004, vol=0.020, drift=+0.015),
    "trend_down": dict(gap_sd=0.004, vol=0.020, drift=-0.015),
    "choppy":     dict(gap_sd=0.004, vol=0.030, revert=0.01),
    "gap_up":     dict(gap=+0.03, vol=0.030),
    "gap_down":   dict(gap=-0.03, vol=0.030),
    "crash":      dict(gap_sd=0.004, vol=0.025, crash=-0.06),
    "quiet":      dict(gap_sd=0.002, vol=0.006),
    "bootstrap":  dict(),
}


def trading_days(n, start=START):
    e = skill.entry()
    out, d = [], start
    while len(out) < n:
        if e.trading_day(d)[0] and d.isoformat() not in e.NYSE_EARLY_CLOSE:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def _ushape(slot):
    x = (slot - (BARS - 1) / 2.0) / ((BARS - 1) / 2.0)
    return 0.7 + 0.9 * x * x          # busier at the open and the close


def _r2(x):
    return round(x + 1e-9, 2)


def _bar(t, o, h, l, c, v):
    o, h, l, c = _r2(o), _r2(h), _r2(l), _r2(c)
    return {"t": t, "o": o, "h": max(h, o, c), "l": min(l, o, c), "c": c, "v": max(1, int(v))}


def _slot_ts(day):
    e = skill.entry()
    t0 = e.ts_of(e.eastern_to_utc(datetime.datetime.combine(day, datetime.time(9, 30))))
    return [t0 + 300 * i for i in range(BARS)]


def _model_day(rng, p, day, prev_close):
    gap = p["gap"] if "gap" in p else rng.gauss(0, p["gap_sd"])
    open_ = _r2(prev_close * (1 + gap))
    sigma = p["vol"] / math.sqrt(BARS * SUB)
    drift = p.get("drift", 0.0) / (BARS * SUB)
    crash_at = rng.randint(18, 51) if "crash" in p else None     # bar 18 = 11:00, 51 = 13:45
    crash_step = math.log(1 + p["crash"]) / (3 * SUB) if crash_at is not None else 0.0
    logp, log_open = math.log(open_), math.log(open_)
    bars = []
    for slot, t in enumerate(_slot_ts(day)):
        o = math.exp(logp)
        hi = lo = o
        for _ in range(SUB):
            step = drift + sigma * _ushape(slot) * rng.gauss(0, 1)
            if "revert" in p:
                step -= p["revert"] * (logp - log_open)
            if crash_at is not None and crash_at <= slot < crash_at + 3:
                step += crash_step
            logp += step
            px = math.exp(logp)
            hi, lo = max(hi, px), min(lo, px)
        c = math.exp(logp)
        bars.append(_bar(t, o if slot else open_, hi, lo, c, 100_000 * _ushape(slot) * rng.lognormvariate(0, 0.3)))
    return bars


_TSLA = None


def _tsla_sessions():
    """The skill's bundled 59 sessions of real TSLA 5-minute bars, each bar as ratios to the prior close."""
    global _TSLA
    if _TSLA is None:
        e = skill.entry()
        path = os.path.join(skill.FIXTURES, "trader-timemachine", "TSLA-60d5m.json.gz")
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            chart = e.parse_chart(fh.read(), "TSLA")
        by_day = {}
        for b in chart["bars"]:
            if b["t"] % 300:
                continue
            local = e.to_eastern(e.utc_of(b["t"]))
            by_day.setdefault(local.date(), []).append(b)
        sessions, prev_close = [], None
        for d in sorted(by_day):
            bars = by_day[d]
            if len(bars) == BARS and prev_close:
                rel, pc = [], prev_close
                for b in bars:
                    rel.append((b["o"] / pc, b["h"] / pc, b["l"] / pc, b["c"] / pc, b["v"]))
                    pc = b["c"]
                sessions.append(rel)
            prev_close = bars[-1]["c"]
        _TSLA = sessions
    return _TSLA


def _bootstrap_day(rng, day, prev_close):
    sessions = _tsla_sessions()
    pc, bars = prev_close, []
    for slot, t in enumerate(_slot_ts(day)):
        o, h, l, c, v = rng.choice(sessions)[slot]
        bars.append(_bar(t, pc * o, pc * h, pc * l, pc * c, v))
        pc = bars[-1]["c"]
    return bars


def generate(scenario, seed, days, start=START):
    if scenario not in SCENARIOS:
        raise ValueError("unknown scenario %r (have: %s)" % (scenario, ", ".join(sorted(SCENARIOS))))
    rng = random.Random("%s:%s" % (scenario, seed))
    out = []
    for day in trading_days(days, start):
        prev_close = _r2(BASE_PRICE * math.exp(rng.gauss(0, 0.05)))
        if scenario == "bootstrap":
            bars = _bootstrap_day(rng, day, prev_close)
        else:
            bars = _model_day(rng, SCENARIOS[scenario], day, prev_close)
        out.append({"symbol": "SYN", "meta": {"scenario": scenario, "seed": seed}, "bars": bars,
                    "prev_close": prev_close, "data_time": None})
    return out
