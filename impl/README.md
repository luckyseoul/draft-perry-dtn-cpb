# CPB Reference Implementation

This directory contains the reference implementation of the Contact
Probability Block defined by
[`draft-perry-dtn-cpb-latest`](../draft-perry-dtn-cpb.xml).

## Installation

```sh
python3 -m pip install -e '.[test]'
```

## Tests

```sh
python3 -m pytest -q
```

The conformance suite covers:

- deterministic CBOR and IEEE 754 binary16 probability encoding;
- BP EID arrays, including RFC 9758 two- and three-item IPN SSPs;
- forwarding-entry and aggregate resource limits;
- required-field, EID, and duplicate-action validation;
- malformed and non-deterministic CBOR rejection;
- BTSD and canonical-block test vectors;
- freshness-window processing; and
- scheme-aware IPN EID matching.

The canonical-block helper emits CRC type zero for vectors intended to be
covered by an applicable integrity service. Production integrations select CRC
and BPSec processing according to RFC 9171 and RFC 9173.

## Files

| File | Purpose |
|---|---|
| `cpb.py` | CPB encoder, decoder, EID matching, and freshness helpers |
| `cpb.cddl` | Standalone CDDL schema |
| `test_cpb.py` | Byte-level positive and negative conformance tests |
| `test_draft_consistency.py` | Specification and implementation consistency tests |

The implementation is distributed under the repository's MIT license.
