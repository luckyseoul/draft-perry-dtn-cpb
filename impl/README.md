# CPB Reference Implementation

Reference implementation of the Contact Probability Block (CPB) defined in [draft-perry-dtn-cpb-00](../draft-perry-dtn-cpb.xml).

## Contents

| File | Purpose |
|------|---------|
| `cpb.py` | Encoder and decoder for the CPB block-type-specific data per §3.2 / §3.4. |
| `test_cpb.py` | Conformance suite (encode/decode, hex tables, invalid floats, path-array SHOULD). |
| `test_config1_policies.py` | Unit tests for the draft §12 confidence-weighted cost formula used by the simulator. |
| `test_sim_cpb_bridge.py` | Bridge: Config 1 confidences encode/decode as metric-type 1 CPB without changing confidence-weighted ranking. |
| `test_draft_consistency.py` | Structural checks that draft/docs claims match shipped code. |
| `config1_sim.py` | Discrete-event simulator for draft §12.5 (4-rover, 4-orbiter Mars relay). Strategies: `baseline`, `cpb` (confidence-weighted). CLI: `--quick`, `--battery`, `--strategy`, `--max-bundles`, `--age-conf`, `--csv`. |
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

# Recommended default for serious baseline comparisons (3 seeds, full load):
python3 config1_sim.py --battery standard     # (this is now the default)

# Paper battery (10 seeds) — rates reported in draft §12.5:
python3 config1_sim.py --battery paper --strategy both

# Fast smoke test:
python3 config1_sim.py --quick

# Other useful options:
python3 config1_sim.py --battery standard --strategy cpb --csv results.csv
python3 config1_sim.py --quick --strategy both --max-bundles 8000
```

Expected `test_cpb.py` output: 22 `PASS` lines, zero failures.

Routing policy labels (must match draft §12):

- **baseline** — earliest predicted arrival
- **CPB** — `cost = latency / confidence`

**Delivery primary.** Hop-retry count `R` is a lever (`--hop-retries` /
`--sweep-hop-retries 2,3,4`). Same CRN and `cost = latency / confidence`
for both arms. Paper battery (10 seeds):

| R | baseline | CPB | Δ delivery |
|---|----------|-----|------------|
| 2 | ≈0.9789 | ≈0.9901 | ≈+0.011 |
| 3 | ≈0.9965 | ≈0.9984 | ≈+0.0019 (draft default) |
| 4 | ≈0.9988 | ≈0.9991 | ≈+0.0003 |

Tighter R → larger CPB delivery edge (high-value / short-budget traffic).
Larger R → higher absolute delivery, smaller gap. p95 is not a free win.
Parallel sweep: `--workers` (defaults to nproc-2).

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

Reference implementation by the draft author (draft §11).
