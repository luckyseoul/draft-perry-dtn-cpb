#!/usr/bin/env python3
"""
Simple usage example for the CPB reference implementation.

Demonstrates:
- Building a CPB data structure
- Encoding to wire bytes (cbor2)
- Wrapping as Block Type-Specific Data (BTSD) per the draft
- Decoding and round-tripping
- Using the strict vs. non-strict float16 modes

Run after `pip install -e '.[test]'` from the impl/ directory (or with the
package in your PYTHONPATH).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python3 examples/simple_usage.py` from the repo root without install.
_IMPL = Path(__file__).resolve().parents[1] / "impl"
if str(_IMPL) not in sys.path:
    sys.path.insert(0, str(_IMPL))

import cpb  # noqa: E402


def main() -> None:
    print("=== CPB simple usage example ===\n")

    # 1. Build a CPB (default probability + two path entries).
    # An actual consumer also needs the shared transmitter/contact-window
    # context for metric 1; this example demonstrates wire handling only.
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    data = {
        cpb.F_DEFAULT_PROB: 0.82,
        cpb.F_PATH_ENTRIES: [
            [300, 0.91],   # next-hop 300 (e.g. an orbiter) with high confidence
            [100, 0.67],   # default-allocator IPN FQNN 100
        ],
        cpb.F_TIMESTAMP: int((datetime.now(timezone.utc) - epoch).total_seconds()),
        cpb.F_VALIDITY: 3600,          # valid for one hour
        cpb.F_METRIC_TYPE: cpb.METRIC_CGR_CONFIDENCE,
        cpb.F_CONFIDENCE: 0.75,        # confidence in the probabilities themselves
    }

    print("Input CPB data (Python dict):")
    print(data)
    print()

    # 2. Encode to wire format (the "cpb-data" CBOR map)
    wire = cpb.encode_cpb(data)
    print(f"Encoded cpb-data ({len(wire)} bytes): {wire.hex().upper()}")
    print()

    # 3. Wrap as Block Type-Specific Data (BTSD) — what actually goes in the BPv7 block
    btsd = cpb.encode_btsd(data)
    print(f"BTSD wrapper ({len(btsd)} bytes, first byte 0x{btsd[0]:02x}): {btsd.hex().upper()}")
    print()

    # 4. Decode the BTSD back
    decoded = cpb.decode_btsd(btsd)
    print("Decoded from BTSD:")
    print(decoded)
    print()

    # 5. Verify round-trip stability
    wire2 = cpb.encode_cpb(decoded)
    assert wire == wire2, "Round-trip failed!"
    print("✓ encode → decode → encode is byte-stable\n")

    # 6. Strict vs. non-strict float16 behavior (via the internal helper for demo)
    tricky = 0.123456789  # not exactly representable in binary16

    print("Float16 behavior demo:")
    print(f"  Value: {tricky}")

    # Non-strict (default in the public API) — snaps to nearest binary16
    snapped = cpb._encode_prob_float16(tricky)
    print(f"  Non-strict (snaps): {snapped.hex().upper()}")

    # Strict — refuses values that aren't exactly representable
    try:
        cpb._encode_prob_float16(tricky, strict=True)
    except ValueError as e:
        print(f"  Strict mode: raises ValueError (as expected)")
        print(f"    → {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
