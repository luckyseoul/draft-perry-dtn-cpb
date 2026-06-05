# Probabilistic Contact Metadata for DTN Bundle Routing

Working area for the individual Internet-Draft "Probabilistic Contact Metadata
for DTN Bundle Routing" (draft-perry-dtn-cpb). Defines the Contact Probability
Block (CPB), a BPv7 extension block carrying per-contact probability metadata
in-bundle to support confidence-weighted routing in delay-tolerant networks.

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

# Fast smoke test of the Mars relay simulation
python3 config1_sim.py --quick

# Full paper-reproducing run (10 seeds, ~80k bundles/arm)
python3 config1_sim.py
```

Alternative (traditional):

```sh
pip install -r requirements.txt
python3 test_cpb.py
python3 config1_sim.py --quick
```

The simulator supports useful options:
```sh
python3 config1_sim.py --help
python3 config1_sim.py --strategy cpb --max-bundles 8000 --csv results.csv
```

All changes on the `timeline1` branch (build robustness, packaging, CI, stronger tests, simulator CLI) are intended to make the reference implementation easier for other people to use, test, and build upon.

## Reference implementation

See [`impl/`](impl/) for the CPB encoder/decoder, conformance tests, and the
simulator that produced the Section 11 results.

```sh
cd impl
pip install -r requirements.txt
python3 test_cpb.py
python3 config1_sim.py
```

## License

Reference implementation in [`impl/`](impl/): [MIT](LICENSE).
Draft text: IETF Trust Legal Provisions (BCP 78).
