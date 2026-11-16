"""S5: one scenario end to end, ORB vs the random-entry control."""

from dtbt.pipeline import Settings
from dtbt.runner import run_experiment


def test_small_run_is_reproducible_and_the_control_uses_the_same_sizing():
    a = run_experiment("choppy", Settings(), days=5, seed=1)
    assert a == run_experiment("choppy", Settings(), days=5, seed=1)
    for arm in ("orb", "control"):
        assert a[arm]["summary"]["days"] == 5
        assert len(a[arm]["results"]) == 5
    control_trades = [r for r in a["control"]["results"] if r["status"] == "traded"]
    assert control_trades, "the control should trade on most days"
    for r in control_trades:
        assert r["risk_verdict"] == "PASS"
        assert 0 < r["max_loss"] <= 50.0          # same $50 max-loss sizing as the ORB arm


def test_control_entries_fall_inside_the_skills_entry_window():
    a = run_experiment("quiet", Settings(), days=5, seed=2)
    for r in a["control"]["results"]:
        if "trigger_time" in r:
            assert "09:45" <= r["trigger_time"] <= "15:30"
