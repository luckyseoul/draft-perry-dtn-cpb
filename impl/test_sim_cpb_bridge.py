"""Bridge tests: Configuration 1 confidences through the CPB wire format.

Purpose of CPB (draft abstract): transport for per-contact probability
metadata that routing consumers can use. The Config 1 simulator uses
ground-truth confidences without encoding extension blocks. These tests
prove that those same confidences:

1. Encode and decode as metric-type 1 (cgr-confidence) CPB maps / BTSD, and
2. Preserve the rate-aware cost ranking used by the "cpb" policy after
   float16 round-trip (binary16 snap is expected and routing-grade).

This is the missing link between the wire format and the routing-value
experiment without claiming in-band ION CGR consumption.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Allow `python3 impl/test_sim_cpb_bridge.py` from repo root or impl/
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from cpb import (  # noqa: E402
    F_DEFAULT_PROB,
    F_METRIC_TYPE,
    F_PATH_ENTRIES,
    F_VERSION,
    METRIC_CGR_CONFIDENCE,
    decode_btsd,
    decode_cpb,
    encode_btsd,
    encode_cpb,
)
from config1_sim import (  # noqa: E402
    GROUNDS,
    ORBITERS,
    ROVER_ORBITER_CONFIDENCE,
    ROVERS,
    Route,
    cpb_route_cost,
    predicted_arrival,
)


def _path_entries_for_rover(rover: int) -> list[list]:
    """One path entry per orbiter: [next-hop node number, confidence]."""
    return [[o, ROVER_ORBITER_CONFIDENCE[rover][o]] for o in ORBITERS]


def _cpb_for_rover(rover: int) -> dict:
    paths = _path_entries_for_rover(rover)
    # Default = max first-hop confidence for this rover (common pattern)
    default = max(p for _, p in paths)
    return {
        F_DEFAULT_PROB: default,
        F_PATH_ENTRIES: paths,
        F_METRIC_TYPE: METRIC_CGR_CONFIDENCE,
        F_VERSION: 1,
    }


def test_config1_confidences_roundtrip_as_cpb():
    for rover in ROVERS:
        data = _cpb_for_rover(rover)
        wire = encode_cpb(data)
        back = decode_cpb(wire)
        assert back[F_METRIC_TYPE] == METRIC_CGR_CONFIDENCE
        assert back[F_VERSION] == 1
        # float16 snap: decoded probs close to originals
        orig = {nh: p for nh, p in data[F_PATH_ENTRIES]}
        for nh, p in back[F_PATH_ENTRIES]:
            assert abs(p - orig[nh]) < 0.002, (rover, nh, p, orig[nh])
        # BTSD form (what sits in the extension block)
        btsd = encode_btsd(data)
        back2 = decode_btsd(btsd)
        assert back2[F_METRIC_TYPE] == METRIC_CGR_CONFIDENCE
        assert len(back2[F_PATH_ENTRIES]) == len(ORBITERS)


def test_decoded_cpb_preserves_rate_aware_ranking():
    """After wire round-trip, cpb cost ranking over routes is unchanged."""
    t = 1000.0
    for rover in ROVERS:
        data = _cpb_for_rover(rover)
        back = decode_cpb(encode_cpb(data))
        conf_by_orb = {nh: p for nh, p in back[F_PATH_ENTRIES]}

        routes = [Route(rover, o, g) for o in ORBITERS for g in GROUNDS]

        def cost_with_conf(r: Route, conf_map: dict) -> float:
            # Path product: first hop from CPB (or ground truth), rest from sim topology
            p1 = conf_map[r.orbiter]
            # Use full Route.confidence for space-side hops (static 0.99*0.99)
            # but replace first hop with decoded CPB value:
            from config1_sim import ORBITER_RELAY_CONFIDENCE, GROUND_CONFIDENCE
            conf = p1 * ORBITER_RELAY_CONFIDENCE[r.orbiter] * GROUND_CONFIDENCE[r.ground]
            latency = predicted_arrival(t, r) - t
            return cpb_route_cost(latency, conf, r.bottleneck_rate())

        orig_map = {o: ROVER_ORBITER_CONFIDENCE[rover][o] for o in ORBITERS}
        # Sort routes by cost using original vs decoded confidences
        rank_orig = sorted(routes, key=lambda r: cost_with_conf(r, orig_map))
        rank_dec = sorted(routes, key=lambda r: cost_with_conf(r, conf_by_orb))
        # Best route (and full ordering) must match — float16 snap is small enough
        assert rank_orig[0] == rank_dec[0], (
            rover, rank_orig[0], rank_dec[0],
            cost_with_conf(rank_orig[0], orig_map),
            cost_with_conf(rank_dec[0], conf_by_orb),
        )
        assert [ (r.orbiter, r.ground) for r in rank_orig ] == [
            (r.orbiter, r.ground) for r in rank_dec
        ], rover


def test_cpb_metric_type_is_cgr_not_mixed():
    data = _cpb_for_rover(1)
    back = decode_cpb(encode_cpb(data))
    assert back[F_METRIC_TYPE] == METRIC_CGR_CONFIDENCE
    # Explicit: we do not mix metric families in the bridge
    assert METRIC_CGR_CONFIDENCE == 1


if __name__ == "__main__":
    test_config1_confidences_roundtrip_as_cpb()
    test_decoded_cpb_preserves_rate_aware_ranking()
    test_cpb_metric_type_is_cgr_not_mixed()
    print("All sim↔CPB bridge tests passed.")
