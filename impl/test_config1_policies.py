"""Unit tests for Configuration 1 routing cost formulas (draft §12)."""

from __future__ import annotations

import math

from config1_sim import (
    cpb_route_cost,
    cpb_choose,
    baseline_choose,
    Route,
)


def test_cpb_route_cost_matches_draft_formula():
    # cost = latency / (confidence × bottleneck_rate)
    latency, conf, rate = 100.0, 0.5, 2.0e6
    got = cpb_route_cost(latency, conf, rate)
    expected = latency / (conf * rate)
    assert math.isclose(got, expected), (got, expected)


def test_cpb_route_cost_zero_conf_is_inf():
    assert cpb_route_cost(100.0, 0.0, 1e6) == float("inf")
    assert cpb_route_cost(100.0, 0.5, 0.0) == float("inf")


def test_choosers_return_routes():
    r = baseline_choose(1000.0, 1)
    assert isinstance(r, Route)
    r2 = cpb_choose(1000.0, 1)
    assert isinstance(r2, Route)


def test_cpb_prefers_higher_rate_or_conf_when_latency_similar():
    # Pure formula: lower cost for higher conf×rate product
    lat = 200.0
    low = cpb_route_cost(lat, 0.5, 1e6)
    high = cpb_route_cost(lat, 0.9, 3e6)
    assert high < low


if __name__ == "__main__":
    test_cpb_route_cost_matches_draft_formula()
    test_cpb_route_cost_zero_conf_is_inf()
    test_choosers_return_routes()
    test_cpb_prefers_higher_rate_or_conf_when_latency_similar()
    print("All config1 policy tests passed.")
