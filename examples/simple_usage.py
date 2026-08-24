#!/usr/bin/env python3
"""Build, encode, decode, and filter a conforming CPB."""

from __future__ import annotations

import sys
from pathlib import Path

IMPL = Path(__file__).resolve().parents[1] / "impl"
if str(IMPL) not in sys.path:
    sys.path.insert(0, str(IMPL))

import cpb


def main() -> None:
    rover = cpb.ipn_eid(200)
    data = {
        cpb.F_ENTRIES: [
            [rover, cpb.ipn_eid(100), 0.82],
            [rover, cpb.dtn_eid("//relay.example/"), 0.67],
        ],
        cpb.F_EVALUATION_TIME: 16_203_904,
        cpb.F_VALIDITY_DURATION: 3_600_000,
        cpb.F_PRODUCER_NODE: cpb.ipn_eid(50),
    }

    cpb_data = cpb.encode_cpb(data)
    btsd = cpb.encode_btsd(data)
    canonical_block = cpb.encode_canonical_block(data)

    print(f"cpb-data ({len(cpb_data)} bytes): {cpb_data.hex().upper()}")
    print(f"BTSD ({len(btsd)} bytes): {btsd.hex().upper()}")
    print(f"CRC-type-zero test block ({len(canonical_block)} bytes):")
    print(canonical_block.hex().upper())

    decoded = cpb.decode_btsd(btsd)
    assert cpb.encode_cpb(decoded) == cpb_data
    assert cpb.decode_canonical_block(canonical_block) == decoded

    local_entries = cpb.entries_for_node(decoded, [2, [0, 200, 0]])
    print("\nEligible actions for ipn:200.0:")
    for _, next_hop, probability in local_entries:
        print(f"  next-hop={next_hop!r} probability={probability:.6f}")

    tricky = 0.123456789
    nearest = cpb._encode_probability(tricky)
    print(f"\n{tricky} -> deterministic binary16 {nearest.hex().upper()}")


if __name__ == "__main__":
    main()
