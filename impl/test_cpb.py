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
