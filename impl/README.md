# CPB Reference Implementation

Reference implementation of the Contact Probability Block (CPB) defined in [draft-perry-dtn-cpb](../draft-perry-dtn-cpb.xml).

## Contents

| File | Purpose |
|------|---------|
| `cpb.py` | Encoder and decoder for the CPB block-type-specific data per §3.2 / §3.4. ~600 LOC. |
| `test_cpb.py` | 23-test conformance suite covering Sections 3.2 through 3.6 of the draft. |
| `config1_sim.py` | Discrete-event simulator producing the §11.5 results (4-rover, 4-orbiter Mars relay topology, 10 seeds × 80,507 bundles per arm). |
| `requirements.txt` | Python dependencies. |

## Quick start

```sh
pip install -r requirements.txt

# Verify the encoder/decoder against draft §3 byte-exact listings:
python3 test_cpb.py

# Reproduce the experiment results in draft §11.5:
python3 config1_sim.py
```

Expected `test_cpb.py` output: 23 `PASS` lines, zero failures, on Python 3.10+ with `cbor2` 5.9.0.

Expected `config1_sim.py` output: aggregate delivery rates of 0.99620 (baseline CGR) and 0.99976 (CPB-aware CGR-UCoP), reproducing the numbers cited in §11.5 of the draft to the digit. Walltime is approximately 45 seconds on commodity hardware.

## Coverage

The reference implementation exercises:

- Block structure (draft §3.2) including block processing flags (§3.2.1) and CRC handling (§3.2.2)
- CBOR encoding rules (§3.4): float16 deterministic encoding, invalid-float handling (§3.4.1), hex encoding examples (§3.4.3)
- Metric-type semantics (§3.5): cross-metric arithmetic prohibition is enforced in code
- Multiple-CPB precedence (§3.6) and per-path matching (§3.6.1)
- 8-entry per-path array DoS limit (§3.4)
- Backwards-compatible fallback when CPB block type is unknown (§3.3.2)

Byte-exact match is verified against:

- Listing 2 (concrete CPB with `prob=0.75`)
- Listing 7 (per-path CPB wire encoding)
- The full hex encoding table in §3.4.3

## License

BSD 2-Clause. See [`../LICENSE.md`](../LICENSE.md).

## Status

Per [RFC 7942](https://datatracker.ietf.org/doc/html/rfc7942), this is a reference implementation by the draft's author. It is not an independent implementation; a second independent implementation is identified in §11.10 of the draft as a prerequisite for Standards Track maturation.
