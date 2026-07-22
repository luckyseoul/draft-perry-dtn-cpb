# Probabilistic Contact Metadata for DTN Bundle Routing

Working area for the individual Internet-Draft "Probabilistic Contact Metadata
for DTN Bundle Routing" (draft-perry-dtn-cpb). Defines the Contact Probability
Block (CPB), a BPv7 extension block carrying per-contact probability metadata
in-bundle to support confidence-weighted routing in delay-tolerant networks.

**Current line of development is `main`.** That branch holds the vetted draft,
CI, reference implementation, and the timeline1 PWG testbed snapshot.

## Building the draft

```sh
make
```

Builds `draft-perry-dtn-cpb.txt` and `draft-perry-dtn-cpb.html` from the XML
source using xml2rfc.

The build system is more robust than a stock IETF template setup:
- Automatically handles environments where `python3 -m venv` + `ensurepip` is broken (common on Python 3.12+, minimal Ubuntu, containers).
- See `scripts/ensure-template-venv.sh` and the early bootstrap logic in the top-level `Makefile`.

The `lib/` submodule (i-d-template) is cloned automatically on first `make`, or you can run `git submodule update --init`.

## Reference implementation

See [`impl/`](impl/) for the CPB encoder/decoder (Section 3), conformance tests, and the discrete-event simulator that produced the results in Section 11.5.

### Quick start (recommended)

```sh
cd impl

# Modern way: install as a proper package (includes cbor2)
pip install -e '.[test]'

# Run the full conformance suite (including property-based tests with Hypothesis)
python3 test_cpb.py

# Fast smoke test of the Mars relay simulation (baseline + cpb + cpb-risk)
python3 config1_sim.py --quick

# Full paper-reproducing run (10 seeds, ~80k bundles/arm)
python3 config1_sim.py --battery paper --strategy both
```

Alternative (traditional):

```sh
pip install -r requirements.txt
python3 test_cpb.py
python3 config1_sim.py --quick
```

Useful simulator options:

```sh
python3 config1_sim.py --help
python3 config1_sim.py --strategy cpb --csv results.csv
python3 config1_sim.py --strategy cpb-risk --risk-floor 0.85 --age-conf
```

Build robustness, packaging, CI, stronger tests, and the simulator CLI are
maintained on `main` so others can use, test, and build on the reference
implementation.

## License

Reference implementation in [`impl/`](impl/): [BSD-2-Clause](LICENSE).
Draft text: IETF Trust Legal Provisions (BCP 78).
