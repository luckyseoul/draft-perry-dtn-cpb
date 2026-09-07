# Bundle Protocol Contact Probability Block

The Contact Probability Block (CPB) is a BPv7 extension block that carries
probability metadata for a bundle. The specification defines a default
probability, optional per-next-hop entries, a timestamp, a validity duration,
and a metric-type tag.

## Specification

Read the [formatted draft](draft-perry-dtn-cpb.html); its normative source is
[`draft-perry-dtn-cpb.xml`](draft-perry-dtn-cpb.xml). See the
[quick reference](docs/CPB-QUICK-REFERENCE.md) for the wire format and
processing rules.

## Build

Build formatted text, HTML, and PDF:

```sh
make
```

This requires `xml2rfc` and the standard build dependencies.

## Experimental Scope

This is an unsubmitted GitHub presubmission with intended status Experimental.
The draft contains a plan for future routing, robustness, and interoperability
experiments. It reports no experimental results or demonstrated performance
improvement. Reference-code development checks do not execute that plan.

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

`make test` runs the same implementation checks using the Python interpreter
from the caller's environment. To select a separate environment, use
`make test CPB_PYTHON=/absolute/path/to/python`. The implementation pins
`cbor2==5.9.0` because its deterministic encoder uses that version's Python
backend; the draft rendering tools use their own template environment.

The editor copy uses `-latest`. Numbered submission artifacts can be prepared
locally without uploading them. The publishing workflow uploads to Datatracker
when a `draft-*` tag is pushed or the workflow is dispatched; use those
actions only when the author is ready to submit.
