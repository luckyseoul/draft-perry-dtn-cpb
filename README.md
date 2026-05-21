# Probabilistic Contact Metadata for DTN Bundle Routing

Working area for the individual Internet-Draft "Probabilistic Contact Metadata
for DTN Bundle Routing" (draft-perry-dtn-cpb). Defines the Contact Probability
Block (CPB), a BPv7 extension block carrying per-contact probability metadata
in-bundle to support confidence-weighted routing in delay-tolerant networks.

## Building

```sh
make
```

Builds `draft-perry-dtn-cpb.txt` and `draft-perry-dtn-cpb.html` from the XML
source using xml2rfc. Requires the `lib` submodule (cloned automatically on
first `make`, or via `git submodule update --init`).

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
