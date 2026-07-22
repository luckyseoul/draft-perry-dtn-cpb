# CPB Reference Implementation

Reference implementation of the Contact Probability Block (CPB) defined in [draft-perry-dtn-cpb](../draft-perry-dtn-cpb.xml).

## Contents

| File | Purpose |
|------|---------|
| `cpb.py` | Encoder and decoder for the CPB block-type-specific data per §3.2 / §3.4. ~600 LOC. |
| `test_cpb.py` | Conformance suite (original cases + many negative tests + Hypothesis property-based testing). |
| `config1_sim.py` | Discrete-event simulator producing the §11.5 results (4-rover, 4-orbiter Mars relay topology). Strategies: `baseline`, `cpb` (UCoP), `cpb-risk` (confidence floor then earliest-arrival). Supports `--quick`, `--risk-floor`, `--age-conf`, `--csv`. |
| `requirements.txt` | Python dependencies. |

See `../examples/` for small, runnable demonstrations of using the packaged `cpb` module.

## Quick start

```sh
# Option A: traditional
pip install -r requirements.txt
python3 test_cpb.py

# Option B: install as a proper package (recommended)
pip install -e .
python3 -m pytest -q          # or just: python3 test_cpb.py

# Recommended default for serious baseline comparisons (3 seeds, full load):
python3 config1_sim.py --battery standard     # (this is now the default)

# Exact reproduction of draft §11.5 results:
python3 config1_sim.py --battery paper

# Fast smoke test:
python3 config1_sim.py --quick

# Other useful options:
python3 config1_sim.py --battery standard --strategy cpb --csv results.csv

# All three policies (default); optional risk floor / seasonal aging:
python3 config1_sim.py --quick --strategy all
python3 config1_sim.py --strategy cpb-risk --risk-floor 0.85 --age-conf
```

Expected `test_cpb.py` output: 23+ `PASS` lines (more with Hypothesis installed), zero failures.

Expected full `config1_sim.py` paper battery (`--battery paper --strategy both`): delivery rates 0.99620 (baseline) / 0.99976 (CPB-aware), reproducing §11.5 exactly. Full run ~45s. Default `--strategy all` also runs `cpb-risk`.

## New in this tree (timeline1 improvements)

- Robust `make` (even on Python 3.12+ / minimal environments)
- `pip install -e '.[test]'` packaging for the CPB encoder/decoder
- Much stronger test suite (negative cases + Hypothesis property-based tests)
- Simulator now has a convenient CLI (`--quick`, `--max-bundles`, etc.)
- GitHub Actions CI

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
- Listing 7 (per-path CPB wire encoding)
- The full hex encoding table in §3.4.3

## License

MIT. See [`../LICENSE`](../LICENSE).

## Status

Per [RFC 7942](https://datatracker.ietf.org/doc/html/rfc7942), this is a reference implementation by the draft's author. It is not an independent implementation; a second independent implementation is identified in §11.10 of the draft as a prerequisite for Standards Track maturation.
