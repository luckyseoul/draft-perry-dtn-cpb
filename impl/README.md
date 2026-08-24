# CPB Reference Implementation

Reference implementation of the Contact Probability Block (CPB) defined in
the [working draft](../draft-perry-dtn-cpb.xml).

## Contents

| File | Purpose |
|------|---------|
| `cpb.py` | Encoder and decoder for the CPB block-type-specific data per §3.2 / §3.4. |
| `test_cpb.py` | Conformance suite (encode/decode, hex tables, invalid floats, path-array SHOULD). |
| `test_config1_policies.py` | Deterministic unit tests for the local confidence-weighted cost helper. |
| `test_sim_cpb_bridge.py` | Bridge tests for mapping local confidence values to metric-type 1 CPB. |
| `test_draft_consistency.py` | Structural checks that draft/docs claims match shipped code. |
| `config1_sim.py` | Local deterministic policy-test harness used by the unit and bridge tests. |
| `requirements.txt` | Python dependencies. |

See `../examples/` for small, runnable demonstrations of using the packaged `cpb` module.

## Quick start

```sh
# Option A: traditional
pip install -r requirements.txt
python3 test_cpb.py
python3 test_config1_policies.py

# Option B: install as a proper package (recommended)
pip install -e '.[test]'
python3 test_cpb.py

python3 test_sim_cpb_bridge.py
python3 test_draft_consistency.py
```

Expected `test_cpb.py` output: 22 `PASS` lines, zero failures.

The local policy helper uses `cost = latency / confidence` for its
deterministic unit tests. It is not presented as a routing-performance
evaluation.

## Coverage

The reference encoder/decoder exercises:

- CBOR encoding of CPB block-type-specific data (§3.4): float16 deterministic encoding, invalid-float handling (§3.4.1), hex encoding examples (§3.4.3)
- BTSD wrapping of the CPB map as used in the extension block
- per-path array (field 1): more than 8 entries are accepted at the encoder (SHOULD, not MUST; local enforcement on constrained nodes)

Routing, multi-CPB precedence, per-path matching algorithms, and cross-metric arithmetic prohibition are specified in the draft prose and are not separate unit tests in this package.

Byte-exact match is verified against:

- Figure 2 (concrete CPB with `prob=0.75`)
- Figure 7 (per-path CPB wire encoding, §3.6)
- The full hex encoding table in §3.4.3

## License

MIT. See [`../LICENSE`](../LICENSE).

## Status

Reference implementation by the draft author.
