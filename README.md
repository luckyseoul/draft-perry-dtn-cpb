# Bundle Protocol Contact Probability Block

The Contact Probability Block (CPB) is a BPv7 extension block that carries
probability metadata for a bundle. The specification defines a default
probability, optional per-next-hop entries, a timestamp, a validity duration,
and a metric-type tag.

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

The `impl/` directory contains the standalone CDDL validation schema, Python
encoder/decoder, and deterministic format and policy tests. These checks do
not make comparative routing-performance claims.

```sh
python3 -m pip install -e './impl[test]'
python3 impl/test_cpb.py
python3 impl/test_config1_policies.py
python3 impl/test_sim_cpb_bridge.py
python3 impl/test_draft_consistency.py
make cddl
```

See [implementation details](impl/README.md).
