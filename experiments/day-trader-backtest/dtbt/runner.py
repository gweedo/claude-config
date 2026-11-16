"""S5: run one scenario with the ORB rule and with the random-entry control (grilling Q7).

Each day is a fresh $5,000 account with an empty broker log (one trade a day, grilling Q6).
The control picks a random 5-minute bar inside the skill's entry window (bar end 09:45-15:30,
after the opening range) and enters at its close. Target, sizing, risk check and fills are
exactly the ORB arm's; the stop keeps the same DISTANCE (see control_settings).
"""

import math
import random
from dataclasses import replace

from dtbt.generator import generate
from dtbt.metrics import summarize
from dtbt.pipeline import Account, run_day

FIRST_END_SLOT = 2      # bar 2 ends 09:45
LAST_END_SLOT = 71      # bar 71 ends 15:30


def control_slot(rng, or_minutes):
    return rng.randint(max(or_minutes // 5, FIRST_END_SLOT), LAST_END_SLOT)


def control_settings(chart, settings, entry_price):
    """An opening-range stop only makes sense above the range, where a breakout enters.
    The control keeps the same stop DISTANCE instead: half the range under the entry for
    or-mid, the whole range for or-low. ATR and pct stops are already entry-relative."""
    rule = settings.stop.lower().replace("_", "-")
    if rule not in ("or-mid", "mid", "or-low", "low"):
        return settings
    n_or = settings.or_minutes // 5
    hi = max(b["h"] for b in chart["bars"][:n_or])
    lo = min(b["l"] for b in chart["bars"][:n_or])
    dist = (hi - lo) / 2.0 if rule in ("or-mid", "mid") else (hi - lo)
    stop = math.floor((entry_price - dist) * 100) / 100.0
    return replace(settings, stop="price:%.2f" % max(stop, 0.01))


def run_experiment(scenario, settings, days, seed, charts=None):
    charts = charts if charts is not None else generate(scenario, seed, days)
    orb, ctl = [], []
    for i, chart in enumerate(charts):
        orb.append(run_day(chart, settings, Account(cash=settings.budget)))
        rng = random.Random("control:%s:%s:%s" % (scenario, seed, i))
        slot = control_slot(rng, settings.or_minutes)
        price = chart["bars"][slot]["c"]
        ctl.append(run_day(chart, control_settings(chart, settings, price), Account(cash=settings.budget),
                           entry_override=(slot, price)))
    return {"orb": {"summary": summarize(orb), "results": orb},
            "control": {"summary": summarize(ctl), "results": ctl}}
