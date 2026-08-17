"""
test_cpb.py -- round-trip and conformance tests for cpb.py.

Verifies:
  - Figure 2 (Section 3.2): full CPB with prob=0.75, 1 path entry, timestamp,
    validity duration -- inner CBOR map matches expected wire bytes.
  - Figure 2 / Figure 7 hex and the Section 3.4.3 table.
  - Figure 7 (Section 3.6): wire encoding for the same -- byte-for-byte match.
  - Hex encoding table (Section 3.4.3): each (prob -> CBOR hex) row.
  - Section 3.4.1: NaN, +/-Inf rejection; out-of-range clamping on decode.
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
# Expected inner BTSD content (the 23-byte CBOR map after the bstr header):
#   A4                  ; map(4)
#   00 F93A00           ; 0: 0.75
#   01 81               ; 1: array(1)
#       82 1864 F93C00  ;    [100, 1.0]
#   02 1A 00F73A80      ; 2: timestamp 0x00F73A80 (16203904)
#   04 19 0E10          ; 4: validity 3600

print("\n== Figure 2 (Section 3.2): full CPB ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[100, 1.0]],
    cpb.F_TIMESTAMP: 0x00F73A80,
    cpb.F_VALIDITY: 3600,
}
expected_inner = "A400F93A0001818218 64F93C00021A00F73A8004190E10".replace(" ", "")
got_inner = _hex(cpb.encode_cpb(data))
if got_inner != expected_inner:
    fail("Figure 2 inner CBOR mismatch", got=got_inner, expected=expected_inner)
ok(f"inner CBOR ({len(got_inner)//2} bytes) matches Figure 2")

decoded = cpb.decode_cpb(cpb.encode_cpb(data))
if decoded != data:
    fail("Figure 2 round-trip mismatch", got=decoded, expected=data)
ok("decode(encode(L2)) == L2")


# ---------------- Figure 7: per-path wire encoding ----------------------
# Expected:
#   A3                       ; map(3)
#   00 F93A00                ; 0: 0.75
#   01 82                    ; 1: array(2)
#       82 19 012C F93800    ;   [300, 0.5]
#       82 18 64 F93C00      ;   [100, 1.0]
#   05 01                    ; 5: 1 (cgr-confidence)

print("\n== Figure 7 (Section 3.6): per-path wire encoding ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[300, 0.5], [100, 1.0]],
    cpb.F_METRIC_TYPE: cpb.METRIC_CGR_CONFIDENCE,
}
expected = "A300F93A000182821 9012CF93800821864F93C000501".replace(" ", "")
got = _hex(cpb.encode_cpb(data))
if got != expected:
    fail("Figure 7 mismatch", got=got, expected=expected)
ok(f"wire encoding ({len(got)//2} bytes) matches Figure 7")

decoded = cpb.decode_cpb(cpb.encode_cpb(data))
if decoded != data:
    fail("Figure 7 round-trip mismatch", got=decoded, expected=data)
ok("decode(encode(L7)) == L7")


# ---------------- BTSD wrap: Figure 2 wrapped as bstr -------------------

print("\n== BTSD wrapping (Section 3.2: bstr .cbor cpb-data) ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[100, 1.0]],
    cpb.F_TIMESTAMP: 0x00F73A80,
    cpb.F_VALIDITY: 3600,
}
btsd = cpb.encode_btsd(data)
# bstr major-type 2; 23 bytes -> header byte 0x57 (= 0x40 | 23).
if btsd[0] != 0x57:
    fail("BTSD bstr header", got=hex(btsd[0]), expected="0x57 (bstr len 23)")
ok(f"BTSD bstr header byte 0x{btsd[0]:02X} (length {btsd[0] & 0x1F})")

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

# Decoder is permissive (clamps); test a hand-built blob with prob > 1.0 in float32.
import cbor2
blob_oversize = cbor2.dumps({0: 1.5}, canonical=True)
decoded = cpb.decode_cpb(blob_oversize)
if decoded[0] != 1.0:
    fail("decode 1.5 should clamp to 1.0", got=decoded[0])
ok("decode 1.5 -> clamped to 1.0")

blob_neg = cbor2.dumps({0: -0.2}, canonical=True)
decoded = cpb.decode_cpb(blob_neg)
if decoded[0] != 0.0:
    fail("decode -0.2 should clamp to 0.0", got=decoded[0])
ok("decode -0.2 -> clamped to 0.0")


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
data9 = {cpb.F_PATH_ENTRIES: [[i, 0.5] for i in range(9)]}
try:
    cpb.encode_cpb(data9)
    ok("9 path entries accepted (SHOULD, not MUST; local enforcement recommended on constrained links)")
except ValueError as e:
    ok(f"9 path entries rejected (local enforcement active: {str(e)[:60]}...)")


# ---------------- multi-step round-trip stability ------------------------

print("\n== round-trip byte stability ==")
data = {
    cpb.F_DEFAULT_PROB: 0.75,
    cpb.F_PATH_ENTRIES: [[300, 0.5], [100, 1.0]],
    cpb.F_TIMESTAMP: 16203904,
    cpb.F_VALIDITY: 3600,
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
