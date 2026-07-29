"""Unit tests for Configuration 1 routing cost formulas (draft §12)."""

from __future__ import annotations

import math

from config1_sim import (
    MAX_HOP_RETRIES,
    cpb_route_cost,
    cpb_choose,
    baseline_choose,
    next_window_open,
    attempt_hop,
    Route,
    ROVER_ORBITER_CONFIDENCE,
    ROVER_ORBITER_RATE,
    ORBITERS,
    ROVERS,
)


def test_cpb_route_cost_matches_draft_formula():
    # cost = latency / confidence
    latency, conf = 100.0, 0.5
    got = cpb_route_cost(latency, conf)
    expected = latency / conf
    assert math.isclose(got, expected), (got, expected)
    # rate argument ignored in published cost
    assert math.isclose(cpb_route_cost(latency, conf, 1e9), expected)


def test_cpb_route_cost_zero_conf_is_inf():
    assert cpb_route_cost(100.0, 0.0) == float("inf")


def test_choosers_return_routes():
    r = baseline_choose(1000.0, 1)
    assert isinstance(r, Route)
    r2 = cpb_choose(1000.0, 1)
    assert isinstance(r2, Route)


def test_cpb_prefers_higher_conf_when_latency_similar():
    lat = 200.0
    low = cpb_route_cost(lat, 0.5)
    high = cpb_route_cost(lat, 0.9)
    assert high < low


def test_rates_not_rank_aligned_with_confidence():
    """Rate diversity is separable from confidence (not the same latin order)."""
    for rover in ROVERS:
        conf_order = sorted(ORBITERS, key=lambda o: ROVER_ORBITER_CONFIDENCE[rover][o])
        rate_order = sorted(ORBITERS, key=lambda o: ROVER_ORBITER_RATE[rover][o])
        assert conf_order != rate_order, rover


def test_next_window_advances_after_close():
    period, window = 1200.0, 600.0
    # mid open window
    assert next_window_open(100.0, period, window) == 0.0
    # in closed half of cycle 0
    assert next_window_open(700.0, period, window) == 1200.0
    # open in cycle 1
    assert next_window_open(1300.0, period, window) == 1200.0


def test_crn_identical_across_strategies():
    """Same seed/contact/trial → same Bernoulli outcome regardless of call order."""
    a1, t1, _ = attempt_hop(0.0, 1200.0, 600.0, 0.9, seed=42, contact_id=10, trial=0)
    a2, t2, _ = attempt_hop(0.0, 1200.0, 600.0, 0.9, seed=42, contact_id=10, trial=0)
    assert a1 == a2 and math.isclose(t1, t2)
    assert MAX_HOP_RETRIES == 2


def test_crn_not_strategy_keyed():
    """Contact success function has no strategy parameter (anti-gaming)."""
    import inspect
    sig = inspect.signature(attempt_hop)
    assert "strategy" not in sig.parameters
    assert "label" not in sig.parameters


def test_cpb_cost_form_unchanged_under_retry_budget():
    """Published cpb arm still uses latency/confidence only (no rate fold-in)."""
    assert math.isclose(cpb_route_cost(400.0, 0.8), 400.0 / 0.8)
    assert math.isclose(cpb_route_cost(400.0, 0.8, bottleneck_rate=1e9), 400.0 / 0.8)


if __name__ == "__main__":
    test_cpb_route_cost_matches_draft_formula()
    test_cpb_route_cost_zero_conf_is_inf()
    test_choosers_return_routes()
    test_cpb_prefers_higher_conf_when_latency_similar()
    test_rates_not_rank_aligned_with_confidence()
    test_next_window_advances_after_close()
    test_crn_identical_across_strategies()
    print("All config1 policy tests passed.")
