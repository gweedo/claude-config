"""Run the full experiment (grilling Q3 option B + Q4 + Q7) and the timemachine calibration.

    .venv/bin/python run_grid.py            # writes out/grid.json, out/calibration.json, out/tables.md

Not unit-tested on purpose (agreed in grilling Q10): it only wires tested pieces together.
"""

import itertools
import json
import math
import os
import statistics
import time

from dtbt import skill
from dtbt.generator import SCENARIOS, generate
from dtbt.pipeline import Settings
from dtbt.runner import run_experiment

DAYS = 250
SEED = 1
OR_MINUTES = (5, 15, 30)
STOPS = ("or-mid", "or-low", "atr:1.5")
TARGETS = ("1R", "1.5R", "2R")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def rs(results):
    return [r["r_multiple"] for r in results if r["status"] == "traded"]


def mean_se(x):
    if len(x) < 2:
        return (x[0] if x else None), None
    return statistics.fmean(x), statistics.stdev(x) / math.sqrt(len(x))


def welch_t(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    return (statistics.fmean(a) - statistics.fmean(b)) / math.sqrt(va + vb) if va + vb else None


def grid():
    rows = []
    charts = {s: generate(s, SEED, DAYS) for s in sorted(SCENARIOS)}
    for (orm, stop, tgt), scen in itertools.product(itertools.product(OR_MINUTES, STOPS, TARGETS), sorted(SCENARIOS)):
        st = Settings(or_minutes=orm, stop=stop, target=tgt)
        res = run_experiment(scen, st, DAYS, SEED, charts=charts[scen])
        o, c = rs(res["orb"]["results"]), rs(res["control"]["results"])
        om, ose = mean_se(o)
        rows.append({"or_minutes": orm, "stop": stop, "target": tgt, "scenario": scen,
                     "orb": res["orb"]["summary"], "control": res["control"]["summary"],
                     "orb_avg_r": om, "orb_se": ose, "orb_t": (om / ose) if ose else None,
                     "t_vs_control": welch_t(o, c)})
    return rows


def calibration(n_target=50):
    """Timemachine's predicted P(target first) vs what actually happened, on bootstrap ORB trades
    (README settings). History = the 59 synthetic sessions before each trade, as the skill uses."""
    tm = skill.timemachine()
    charts = generate("bootstrap", SEED, DAYS)
    res = run_experiment("bootstrap", Settings(), DAYS, SEED, charts=charts)["orb"]["results"]
    out = []
    for i, r in enumerate(res):
        if i < 59 or r["status"] != "traded":
            continue
        sessions = [(str(j), charts[j]["bars"]) for j in range(i - 59, i)]
        pool = tm.build_pool(sessions)
        k = next(j for j, b in enumerate(charts[i]["bars"]) if b["t"] == r["fill"]["entry_ts"]) - 1
        mc = tm.simulate(pool, r["plan"]["entry"], r["plan"]["stop"], r["plan"]["target"], k, 76,
                         replays=2000, seed=19)
        out.append({"day": i, "p_target": mc["p_target"], "p_stop": mc["p_stop"],
                    "p_neither": mc["p_neither"],
                    "actual": r["reason"], "r": r["r_multiple"]})
        if len(out) >= n_target:
            break
    return out


def fmt(x, nd=3):
    return "—" if x is None else ("%.*f" % (nd, x))


def tables(rows, cal):
    L = []
    by_scen = {}
    for r in rows:
        by_scen.setdefault(r["scenario"], []).append(r)
    L.append("## README settings (15-min range, stop at range middle, target 1R)\n")
    L.append("| scenario | ORB trades | win % | avg R | t | total P&L | max DD | control avg R | t vs control |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for s, rr in sorted(by_scen.items()):
        r = next(x for x in rr if x["or_minutes"] == 15 and x["stop"] == "or-mid" and x["target"] == "1R")
        o, c = r["orb"], r["control"]
        L.append("| %s | %d | %s | %s | %s | $%s | $%s | %s | %s |" % (
            s, o["trades"], fmt(o["win_rate"] and o["win_rate"] * 100, 1), fmt(r["orb_avg_r"]), fmt(r["orb_t"], 2),
            fmt(o["total_pnl"], 0), fmt(o["max_drawdown"], 0), fmt(c["avg_r"]), fmt(r["t_vs_control"], 2)))
    L.append("\n## All 27 variants, averaged over the 8 scenarios\n")
    L.append("| range | stop | target | ORB avg R (mean of scenarios) | scenarios with avg R > 0 | best scenario t | worst scenario t | bootstrap avg R | bootstrap t vs control |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    variants = {}
    for r in rows:
        variants.setdefault((r["or_minutes"], r["stop"], r["target"]), []).append(r)
    for (orm, stop, tgt), rr in sorted(variants.items()):
        ars = [x["orb_avg_r"] for x in rr if x["orb_avg_r"] is not None]
        ts = [x["orb_t"] for x in rr if x["orb_t"] is not None]
        b = next(x for x in rr if x["scenario"] == "bootstrap")
        L.append("| %d min | %s | %s | %s | %d/8 | %s | %s | %s | %s |" % (
            orm, stop, tgt, fmt(statistics.fmean(ars)), sum(1 for a in ars if a > 0),
            fmt(max(ts), 2), fmt(min(ts), 2), fmt(b["orb_avg_r"]), fmt(b["t_vs_control"], 2)))
    if cal:
        L.append("\n## Timemachine calibration (%d bootstrap ORB trades)\n" % len(cal))
        buckets = [(0, .2), (.2, .3), (.3, .4), (.4, 1.01)]
        L.append("| predicted P(target first) | trades | predicted avg | actual target-first rate |")
        L.append("|---|---|---|---|")
        for lo, hi in buckets:
            b = [c for c in cal if lo <= c["p_target"] < hi]
            if b:
                L.append("| %.0f–%.0f%% | %d | %.1f%% | %.1f%% |" % (
                    lo * 100, min(hi, 1) * 100, len(b), 100 * statistics.fmean(c["p_target"] for c in b),
                    100 * sum(1 for c in b if c["actual"] == "target") / len(b)))
        L.append("| **all** | %d | %.1f%% | %.1f%% |" % (
            len(cal), 100 * statistics.fmean(c["p_target"] for c in cal),
            100 * sum(1 for c in cal if c["actual"] == "target") / len(cal)))
    return "\n".join(L) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    rows = grid()
    t1 = time.time()
    cal = calibration()
    t2 = time.time()
    with open(os.path.join(OUT, "grid.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    with open(os.path.join(OUT, "calibration.json"), "w") as fh:
        json.dump(cal, fh, indent=1)
    md = tables(rows, cal)
    with open(os.path.join(OUT, "tables.md"), "w") as fh:
        fh.write(md)
    print(md)
    print("grid %.0fs, calibration %.0fs, %d rows" % (t1 - t0, t2 - t1, len(rows)))


if __name__ == "__main__":
    main()
