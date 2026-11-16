"""Load day-trader-skill's tools as Python modules (same approach as its own tests/_load.py).

The skill lives in .vendor/day-trader-skill, pinned by fetch_skill.sh.
"""

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, ".vendor", "day-trader-skill")
FIXTURES = os.path.join(SKILL_DIR, "tests", "fixtures")

_cache = {}


def load(folder, name):
    key = (folder, name)
    if key not in _cache:
        path = os.path.join(SKILL_DIR, folder, name + ".py")
        if not os.path.isfile(path):
            raise RuntimeError("day-trader-skill not found at %s: run ./fetch_skill.sh" % SKILL_DIR)
        spec = importlib.util.spec_from_file_location("dt_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod
    return _cache[key]


def entry():
    return load("trader-entry", "entry")


def exit_():
    return load("trader-exit", "exit")


def budget():
    return load("trader-budget", "size")


def risk():
    return load("trader-risk", "check")


def timemachine():
    return load("trader-timemachine", "timemachine")
