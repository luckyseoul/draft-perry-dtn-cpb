"""Pin Configuration 1 paper-battery means at multiple hop-retry budgets.

Delivery is the primary metric. Hop-retry count R is a lever:
  tighter R → larger paired delivery gain for confidence-weighted cpb;
  larger R → higher absolute delivery for both arms, smaller gap.

Default CI is structural (ordering + documented pins). Full 10-seed battery
runs when RUN_PAPER_BATTERY=1 (default R=3) or RUN_PAPER_BATTERY_SWEEP=1
(R in {2,3,4}).
"""
from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config1_sim import MAX_HOP_RETRIES, SEEDS, simulate, report_run  # noqa: E402


# 10-seed paper battery, CRN, cost=latency/confidence, same seeds both arms.
# Values from real config1_sim runs (2026-07-29 methodology).
#
# R=3 — draft §12.5 / default MAX_HOP_RETRIES (ceiling regime, modest gain)
PUB_R3_BASE_DELIV = 0.9965
PUB_R3_CPB_DELIV = 0.9984
# R=2 — tighter contact budget; larger delivery gain, lower absolute delivery
PUB_R2_BASE_DELIV = 0.9789
PUB_R2_CPB_DELIV = 0.9901
# R=4 — more retries; absolute delivery up, gap compresses further
PUB_R4_BASE_DELIV = 0.9988
PUB_R4_CPB_DELIV = 0.9991
TOL = 0.0005


def _means_for_r(hop_retries: int) -> tuple[float, float]:
    base: list[float] = []
    cpb: list[float] = []
    for seed in SEEDS:
        for strat, bucket in (("baseline", base), ("cpb", cpb)):
            bundles = simulate(seed, strat, hop_retries=hop_retries)
            bucket.append(report_run(bundles, strat, seed)["delivery"])
    return statistics.mean(base), statistics.mean(cpb)


def test_structural_pins_and_default_r():
    assert MAX_HOP_RETRIES == 3
    assert PUB_R2_CPB_DELIV > PUB_R2_BASE_DELIV
    assert PUB_R3_CPB_DELIV > PUB_R3_BASE_DELIV
    # Tighter R: larger absolute miss rate, larger cpb advantage
    assert (PUB_R2_CPB_DELIV - PUB_R2_BASE_DELIV) > (PUB_R3_CPB_DELIV - PUB_R3_BASE_DELIV)
    # Looser R: higher absolute delivery on both arms
    assert PUB_R3_BASE_DELIV > PUB_R2_BASE_DELIV
    assert PUB_R3_CPB_DELIV > PUB_R2_CPB_DELIV


def test_paper_battery_default_r3_if_enabled():
    if os.environ.get("RUN_PAPER_BATTERY") != "1":
        return
    mb, mc = _means_for_r(3)
    assert abs(mb - PUB_R3_BASE_DELIV) < TOL, (mb, PUB_R3_BASE_DELIV)
    assert abs(mc - PUB_R3_CPB_DELIV) < TOL, (mc, PUB_R3_CPB_DELIV)
    assert mc > mb


def test_paper_battery_r2_if_enabled():
    if os.environ.get("RUN_PAPER_BATTERY") != "1" and os.environ.get(
            "RUN_PAPER_BATTERY_SWEEP") != "1":
        return
    mb, mc = _means_for_r(2)
    assert abs(mb - PUB_R2_BASE_DELIV) < TOL, (mb, PUB_R2_BASE_DELIV)
    assert abs(mc - PUB_R2_CPB_DELIV) < TOL, (mc, PUB_R2_CPB_DELIV)
    assert mc > mb
    # delivery gain at R=2 exceeds R=3 published gain
    assert (mc - mb) > (PUB_R3_CPB_DELIV - PUB_R3_BASE_DELIV)


def test_paper_battery_sweep_if_enabled():
    """R=2,3,4: delivery primary; gap shrinks as R grows; absolute delivery rises."""
    if os.environ.get("RUN_PAPER_BATTERY_SWEEP") != "1":
        return
    results = {}
    for r in (2, 3, 4):
        mb, mc = _means_for_r(r)
        results[r] = (mb, mc, mc - mb)
        assert mc > mb, r
    # absolute delivery non-decreasing in R for both arms (ceiling may flatline)
    assert results[3][0] >= results[2][0] - TOL
    assert results[3][1] >= results[2][1] - TOL
    assert results[4][0] >= results[3][0] - TOL
    assert results[4][1] >= results[3][1] - TOL
    # paired gain at R=2 strictly larger than at R=3 (delivery lever)
    assert results[2][2] > results[3][2]
    # R=4 pin (soft): means near documented targets
    assert abs(results[4][0] - PUB_R4_BASE_DELIV) < 0.002, results[4]
    assert abs(results[4][1] - PUB_R4_CPB_DELIV) < 0.002, results[4]


if __name__ == "__main__":
    os.environ.setdefault("RUN_PAPER_BATTERY", "1")
    test_structural_pins_and_default_r()
    test_paper_battery_default_r3_if_enabled()
    test_paper_battery_r2_if_enabled()
    print("Paper battery numbers OK.")
