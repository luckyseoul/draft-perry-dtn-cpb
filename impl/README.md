# CPB Reference Implementation

Reference implementation of the Contact Probability Block (CPB) defined in [draft-perry-dtn-cpb-00](../draft-perry-dtn-cpb.xml).

## Contents

| File | Purpose |
|------|---------|
| `cpb.py` | Encoder and decoder for the CPB block-type-specific data per §3.2 / §3.4. |
| `test_cpb.py` | Conformance suite (original cases + many negative tests + Hypothesis property-based testing). |
| `test_config1_policies.py` | Unit tests for draft §12 routing cost formulas used by the simulator. |
| `config1_sim.py` | Discrete-event simulator for draft §12.5 (4-rover, 4-orbiter Mars relay). Strategies match §12: `baseline`, `cpb` (rate-aware), `cpb-risk` (quadratic risk penalty). CLI: `--quick`, `--battery`, `--strategy`, `--max-bundles`, `--age-conf`, `--csv`. |
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
python3 config1_sim.py --battery paper --strategy all

# Fast smoke test:
python3 config1_sim.py --quick

# Other useful options:
python3 config1_sim.py --battery standard --strategy cpb --csv results.csv
python3 config1_sim.py --quick --strategy all --max-bundles 8000
python3 config1_sim.py --strategy cpb-risk --age-conf
```

Expected `test_cpb.py` output: 23+ `PASS` lines (more with Hypothesis installed), zero failures.

Routing policy labels (must match draft §12):

- **baseline** — earliest predicted arrival
- **cpb** — `cost = latency / (confidence × bottleneck_rate)`
- **cpb-risk** — `cost = latency + (1 − confidence)² × 5000`

Paper-battery mean delivery (Configuration 1, 10 seeds, `--battery paper
--strategy all`): **baseline 0.9962**, **cpb 0.9998**, **cpb-risk 0.9998**
(draft §12.5).

## Coverage

The reference implementation exercises:

- Block structure (draft §3.2) including block processing flags (§3.2.1) and CRC handling (§3.2.2)
- CBOR encoding rules (§3.4): float16 deterministic encoding, invalid-float handling (§3.4.1), hex encoding examples (§3.4.3)
- Metric-type semantics (§3.5): cross-metric arithmetic prohibition is enforced in code
- Multiple-CPB precedence (§3.6) and per-path matching (§3.6.1)
- per-path array (field 1) SHOULD limit of 8 for DoS mitigation on constrained links (§3.4)
- Backwards-compatible fallback when CPB block type is unknown (§3.3.2)

Byte-exact match is verified against:

- Listing 2 (concrete CPB with `prob=0.75`)
- Listing 7 (per-path CPB wire encoding, §3.6)
- The full hex encoding table in §3.4.3

## License

MIT. See [`../LICENSE`](../LICENSE).

## Status

Per [RFC 7942](https://datatracker.ietf.org/doc/html/rfc7942), this is a reference implementation by the draft's author. It is not an independent implementation; a second independent implementation is identified in the draft's Implementation Status section (Section 11) as desirable for Standards Track maturation.
