"""
test_cpb.py -- round-trip and conformance tests for cpb.py.

Verifies:
  - Figure 2 (Section 3.2): full CPB with prob=0.75, 1 path entry, creation
    time and validity (milliseconds), producer node ID -- inner CBOR map
    matches expected wire bytes.
  - Figure 2 / Figure 7 hex and the Section 3.4.3 table.
  - Figure 7 (Section 3.6): wire encoding for the same -- byte-for-byte match.
  - Hex encoding table (Section 3.4.3): each (prob -> CBOR hex) row.
  - Section 3.4.1: NaN, +/-Inf rejection; out-of-range rejection on decode.
  - Round-trip: encode -> decode -> encode is byte-stable.
"""

import sys
import os
# Resolve cpb.py relative to this script's location, regardless of where
# test_cpb.py is invoked from. This allows the test suite to run from any
# directory once the GitHub repo is cloned.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math
import struct
import io
from pathlib import Path
import xml.etree.ElementTree as ET
import cbor2
import cpb


def _hex(b: bytes) -> str:
    return b.hex().upper()


def fail(msg, *, got=None, expected=None):
    print(f"FAIL: {msg}")
    if got is not None:
        print(f"  got:      {got}")
    if expected is not None:
        print(f"  expected: {expected}")
    sys.exit(1)


def ok(msg):
    print(f"PASS  {msg}")


def draft_hex(anchor):
    """Read the literal published bytes, excluding artwork comments."""
    draft = Path(__file__).resolve().parents[1] / "draft-perry-dtn-cpb.xml"
    source = ET.parse(draft).find(f".//figure[@anchor='{anchor}']/sourcecode")
    if source is None or source.text is None:
        fail(f"missing XML hex figure {anchor}")
    return bytes.fromhex("".join(line.partition(";")[0]
                                  for line in source.text.splitlines()))


# ---------------- hex encoding table (Section 3.4.3) ---------------------

print("== Section 3.4.3 hex table ==")
table = [
    (0.0,  "F90000"),
    (0.25, "F93400"),
    (0.5,  "F93800"),
    (0.75, "F93A00"),
    (0.95, "F93B9A"),
    (1.0,  "F93C00"),
]
for prob, expected in table:
    got = _hex(cpb._encode_prob_float16(prob))
    if got != expected:
        fail(f"prob={prob}", got=got, expected=expected)
    ok(f"prob={prob:<5} -> {got}")


# ---------------- Figure 2: minimal full CPB ----------------------------
# Expected inner BTSD content (the 40-byte CBOR map after the bstr header):
#   A5                          ; map(5)
#   00 F93A00                   ; 0: 0.75
#   01 81 82 82 02 82 1864 00 F93C00   ; 1: [[ipn:100.0, 1.0]]
#   02 1B 000000C406A0EE00      ; 2: creation time 841924800000 ms
#   03 82 02 82 18C8 00         ; 3: producer ipn:200.0
#   04 1A 0036EE80              ; 4: validity 3600000 ms
ORBITER = [2, [100, 0]]
RELAY = [2, [300, 0]]
ROVER = [2, [200, 0]]

print("\n== Figure 2 (Section 3.2): full CPB ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[ORBITER, 1.0]],
    cpb.F_TIMESTAMP: 841924800000,
    cpb.F_PRODUCER: ROVER,
    cpb.F_VALIDITY: 3600000,
}
figure2_wire = draft_hex("fig-listing-2")
stream = io.BytesIO(figure2_wire)
figure2_block = cbor2.CBORDecoder(stream).decode()
if stream.tell() != len(figure2_wire):
    fail("Figure 2 must contain exactly one complete CBOR item")
if (not isinstance(figure2_block, list) or len(figure2_block) != 5
        or figure2_block[:4] != [200, 2, 0, 0]
        or not isinstance(figure2_block[4], bytes)):
    fail("Figure 2 canonical-block structure", got=figure2_block)
expected_block = cbor2.dumps([200, 2, 0, 0, cpb.encode_cpb(data)], canonical=True)
if figure2_wire != expected_block:
    fail("Figure 2 complete block mismatch", got=_hex(figure2_wire),
         expected=_hex(expected_block))
ok(f"literal XML Figure 2 is one complete {len(figure2_wire)}-byte canonical block")
expected_inner = _hex(figure2_block[4])
got_inner = _hex(cpb.encode_cpb(data))
if got_inner != expected_inner:
    fail("Figure 2 inner CBOR mismatch", got=got_inner, expected=expected_inner)
ok(f"inner CBOR ({len(got_inner)//2} bytes) matches Figure 2")

decoded = cpb.decode_cpb(cpb.encode_cpb(data))
if decoded != data:
    fail("Figure 2 round-trip mismatch", got=decoded, expected=data)
ok("decode(encode(L2)) == L2")


# ---------------- Figure 7: per-path wire encoding ----------------------
# Expected: map(4) with default 0.75, path entries [ipn:300.0, 0.5] and
# [ipn:100.0, 1.0], producer ipn:200.0, metric type 1 (cgr-confidence).

print("\n== Figure 7 (Section 3.6): per-path wire encoding ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[RELAY, 0.5], [ORBITER, 1.0]],
    cpb.F_PRODUCER: ROVER,
    cpb.F_METRIC_TYPE: cpb.METRIC_CGR_CONFIDENCE,
}
figure7_wire = draft_hex("fig-listing-7")
expected = _hex(figure7_wire)
got = _hex(cpb.encode_cpb(data))
if got != expected:
    fail("Figure 7 mismatch", got=got, expected=expected)
ok(f"wire encoding ({len(got)//2} bytes) matches Figure 7")

decoded = cpb.decode_cpb(figure7_wire)
if decoded != data:
    fail("Figure 7 round-trip mismatch", got=decoded, expected=data)
ok("decode(literal XML Figure 7) == L7 with complete input consumption")


# ---------------- BTSD wrap: Figure 2 wrapped as bstr -------------------

print("\n== BTSD wrapping (Section 3.2: bstr .cbor cpb-data) ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[ORBITER, 1.0]],
    cpb.F_TIMESTAMP: 841924800000,
    cpb.F_PRODUCER: ROVER,
    cpb.F_VALIDITY: 3600000,
}
btsd = cpb.encode_btsd(data)
# bstr major-type 2; 40 bytes -> header 0x58 0x28.
if btsd[:2] != b"\x58\x28":
    fail("BTSD bstr header", got=btsd[:2].hex(), expected="5828 (bstr len 40)")
ok("BTSD bstr header 0x58 0x28 (length 40)")

decoded = cpb.decode_btsd(btsd)
if decoded != data:
    fail("BTSD round-trip", got=decoded, expected=data)
ok("decode_btsd(encode_btsd(d)) == d")


# ---------------- Section 3.4.1 invalid float handling -------------------

print("\n== Section 3.4.1: invalid float handling ==")
try:
    cpb._encode_prob_float16(float("nan"))
    fail("NaN should have raised")
except ValueError:
    ok("encode NaN -> ValueError")
try:
    cpb._encode_prob_float16(float("inf"))
    fail("+Inf should have raised")
except ValueError:
    ok("encode +Inf -> ValueError")
try:
    cpb._encode_prob_float16(-0.1)
    fail("negative prob should have raised")
except ValueError:
    ok("encode -0.1 -> ValueError (encoder is strict)")
try:
    cpb._encode_prob_float16(1.5)
    fail("prob > 1.0 should have raised")
except ValueError:
    ok("encode 1.5 -> ValueError (encoder is strict)")

# Decoder rejects out-of-range finite values (no clamp-to-certainty).
blob_oversize = cbor2.dumps({0: 1.5, 3: ROVER}, canonical=True)
try:
    cpb.decode_cpb(blob_oversize)
    fail("decode 1.5 should have raised")
except ValueError:
    ok("decode 1.5 -> ValueError (rejected)")

blob_neg = cbor2.dumps({0: -0.2, 3: ROVER}, canonical=True)
try:
    cpb.decode_cpb(blob_neg)
    fail("decode -0.2 should have raised")
except ValueError:
    ok("decode -0.2 -> ValueError (rejected)")


# ---------------- non-binary16 probability rejection ----------------------

print("\n== Section 3.4: non-representable float16 (strict mode) ==")
try:
    cpb._encode_prob_float16(0.123456789, strict=True)
    fail("0.123456789 should not be exact in float16")
except ValueError as e:
    ok(f"strict encode 0.123456789 -> ValueError ({str(e)[:60]}...)")

# And confirm non-strict snaps cleanly
snapped = cpb._encode_prob_float16(0.123456789)
ok(f"non-strict encode 0.123456789 -> {_hex(snapped)} (snapped to nearest binary16)")


# ---------------- DoS limit on path-entries (Section 3.4) ----------------

print("\n== Section 3.4: per-path array limit (SHOULD 8 on constrained links) ==")
data9 = {cpb.F_PRODUCER: ROVER,
         cpb.F_PATH_ENTRIES: [[[2, [i + 1, 0]], 0.5] for i in range(9)]}
try:
    cpb.encode_cpb(data9)
    ok("9 path entries accepted (SHOULD, not MUST; local enforcement recommended on constrained links)")
except ValueError as e:
    ok(f"9 path entries rejected (local enforcement active: {str(e)[:60]}...)")


# ---------------- multi-step round-trip stability ------------------------

print("\n== round-trip byte stability ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[RELAY, 0.5], [ORBITER, 1.0]],
    cpb.F_TIMESTAMP: 841924800000,
    cpb.F_PRODUCER: ROVER,
    cpb.F_VALIDITY: 3600000,
    cpb.F_METRIC_TYPE: 1,
    cpb.F_CONFIDENCE: 0.5,
}
e1 = cpb.encode_cpb(data)
e2 = cpb.encode_cpb(cpb.decode_cpb(e1))
e3 = cpb.encode_cpb(cpb.decode_cpb(e2))
if not (e1 == e2 == e3):
    fail("encode is not byte-stable across decode/re-encode",
         got=f"{_hex(e1)} / {_hex(e2)} / {_hex(e3)}")
ok(f"encode -> decode -> encode is byte-stable across 3 cycles ({len(e1)} bytes)")


print("\nAll tests passed.")
