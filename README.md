# Bundle Protocol Contact Probability Block

The Contact Probability Block (CPB) is a BPv7 extension block for carrying a
bundle-conditioned estimate of forwarding success.  Each entry identifies a
decision node, a candidate next hop, and the probability of timely delivery
if that forwarding action is selected.

## Specification

The normative specification is
[`draft-perry-dtn-cpb.xml`](draft-perry-dtn-cpb.xml).  See the
[quick reference](docs/CPB-QUICK-REFERENCE.md) for the wire format and
processing rules.

## Build

Build formatted text and HTML:

```sh
make
```

This requires `xml2rfc` and the standard build dependencies.

## Reference Implementation

The `impl/` directory contains the CPB CDDL, Python encoder and decoder, and
conformance tests.

```sh
python3 -m pip install -e './impl[test]'
python3 -m pytest -q impl
make cddl
```

See [implementation details](impl/README.md).
