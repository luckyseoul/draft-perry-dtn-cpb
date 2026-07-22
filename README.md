# Probabilistic Contact Metadata for DTN Bundle Routing

Working area for the individual Internet-Draft "Probabilistic Contact Metadata
for DTN Bundle Routing" (draft-perry-dtn-cpb-00). Defines the Contact Probability
Block (CPB), a BPv7 extension block carrying per-contact probability metadata
in-bundle to support confidence-weighted routing in delay-tolerant networks.

**Current line of development is `main`.** That branch holds the vetted draft,
CI, reference implementation, and the timeline1 PWG testbed snapshot.

**Teaching aid:** a short visual intro is in
[`docs/CPB-TEACHING-GUIDE.md`](docs/CPB-TEACHING-GUIDE.md) (with diagrams under
`docs/images/`).

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

See [`impl/`](impl/) for the CPB encoder/decoder (Section 3), conformance tests, and the discrete-event simulator that produced the results in Section 12.5.

### Quick start (recommended)

```sh
cd impl

# Modern way: install as a proper package (includes cbor2)
pip install -e '.[test]'

# Run the full conformance suite (including property-based tests with Hypothesis)
python3 test_cpb.py

# Fast smoke test of the Mars relay simulation (baseline + cpb + cpb-risk)
python3 config1_sim.py --quick

# Full paper-reproducing run (10 seeds; draft §12.5 rates)
python3 config1_sim.py --battery paper --strategy all
# Mean delivery (paper battery): baseline 0.9962, cpb/cpb-risk 0.9998
```

Alternative (traditional):

```sh
pip install -r requirements.txt
python3 test_cpb.py
python3 config1_sim.py --quick
```

Useful simulator options (all implemented on the real CLI):

```sh
python3 config1_sim.py --help
python3 config1_sim.py --strategy cpb --csv results.csv
python3 config1_sim.py --strategy cpb-risk
python3 config1_sim.py --max-bundles 8000 --quick
python3 config1_sim.py --age-conf --strategy all
```

Routing policy labels match draft §12:

- **baseline** — earliest predicted arrival (confidence ignored)
- **cpb** — rate-aware: `cost = latency / (confidence × bottleneck_rate)`
- **cpb-risk** — risk-averse: `cost = latency + (1 − confidence)² × 5000`

Paper battery mean delivery (Configuration 1, 10 seeds): **baseline 0.9962**,
**cpb 0.9998**, **cpb-risk 0.9998** (same as draft §12.5).

Build robustness, packaging, CI, stronger tests, and the simulator CLI are
maintained on `main` so others can use, test, and build on the reference
implementation.

## License

Reference implementation in [`impl/`](impl/): [MIT](LICENSE).
Draft text: IETF Trust Legal Provisions (BCP 78).

Note: `CONTRIBUTING.md` is the stock IETF template language about
contributions to the IETF Standards Process (BCP 78/79 and the Trust Legal
Provisions). Code *in this repository* is licensed under the MIT License in
`LICENSE`; the Simplified BSD wording in CONTRIBUTING applies only insofar as
IETF contribution rules govern material submitted into the IETF process, and
does not relicense the MIT-licensed reference implementation.
