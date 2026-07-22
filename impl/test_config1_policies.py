"""Unit tests for Configuration 1 routing cost functions (draft §12).

Drives the real shipped pure functions in config1_sim.py — not reimplemented.
"""
from __future__ import annotations

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config1_sim import (
    CPB_RISK_PENALTY,
    cpb_route_cost,
    cpb_risk_route_cost,
    cpb_choose,
    cpb_risk_choose,
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
    assert cpb_route_cost(10.0, 0.0, 1e6) == float("inf")
    assert cpb_route_cost(10.0, 0.5, 0.0) == float("inf")


def test_cpb_risk_route_cost_matches_draft_formula():
    # cost = latency + (1 − confidence)² × 5000
    latency, conf = 100.0, 0.8
    got = cpb_risk_route_cost(latency, conf)
    expected = latency + (1.0 - conf) ** 2 * CPB_RISK_PENALTY
    assert math.isclose(got, expected), (got, expected)
    assert math.isclose(cpb_risk_route_cost(50.0, 1.0), 50.0)
    # conf=0 → latency + 5000
    assert math.isclose(cpb_risk_route_cost(10.0, 0.0), 10.0 + CPB_RISK_PENALTY)


def test_choosers_return_routes():
    r = baseline_choose(1000.0, 1)
    assert isinstance(r, Route)
    r2 = cpb_choose(1000.0, 1)
    assert isinstance(r2, Route)
    r3 = cpb_risk_choose(1000.0, 1)
    assert isinstance(r3, Route)


def test_cpb_prefers_higher_rate_or_conf_when_latency_similar():
    # Pure formula: lower cost for higher conf×rate product
    lat = 200.0
    low = cpb_route_cost(lat, 0.5, 1e6)
    high = cpb_route_cost(lat, 0.9, 3e6)
    assert high < low


def test_cpb_risk_penalizes_low_confidence():
    lat = 200.0
    safe = cpb_risk_route_cost(lat, 0.95)
    risky = cpb_risk_route_cost(lat, 0.5)
    assert risky > safe


if __name__ == "__main__":
    test_cpb_route_cost_matches_draft_formula()
    test_cpb_route_cost_zero_conf_is_inf()
    test_cpb_risk_route_cost_matches_draft_formula()
    test_choosers_return_routes()
    test_cpb_prefers_higher_rate_or_conf_when_latency_similar()
    test_cpb_risk_penalizes_low_confidence()
    print("All config1 policy tests passed.")
