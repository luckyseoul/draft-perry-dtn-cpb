# CPB quick reference

The normative source is
[`draft-perry-dtn-cpb.xml`](../draft-perry-dtn-cpb.xml). This file is an
implementation aid.

## Meaning

For every entry:

```text
P(bundle delivered before expiry | decision node selects candidate next hop)
```

The probability includes the attempted next-hop transfer and downstream
delivery. It is not a raw contact probability, rank, cost, utility, or estimator
confidence.

## Data model

| Key | Field | Requirement |
|---:|---|---|
| 0 | Entries | Required; 1–8 entries |
| 1 | Evaluation time | Required; DTN milliseconds |
| 2 | Validity duration | Required; positive milliseconds |
| 3 | Producer Node ID | Required; complete BP EID |
| >3 | Extensions | Ignored when unknown; cannot redefine base fields |

Each entry is:

```text
[decision-node EID, candidate-next-hop EID, probability]
```

EIDs use their BP CBOR representation, for example:

```text
[2, [200, 0]]        # ipn:200.0, default allocator
[2, [7, 200, 0]]     # ipn:7.200.0, explicit allocator
[1, "//relay.example/"]
```

IPN matching uses decoded allocator, node, and service values. Equivalent
two- and three-item SSP encodings compare equal.

## Encoding rules

- Deterministic CBOR and ascending map keys are mandatory.
- Probabilities are mandatory CBOR binary16 values in `[0, 1]`.
- Rounding is IEEE 754 round-to-nearest, ties-to-even.
- NaN, infinity, wider floats, integer probabilities, clamping, negative zero
  on the wire, and non-canonical CBOR are rejected.
- All CPB block processing flags are zero; CPB is not replicated into every
  fragment.
- At most four CPBs and 1024 aggregate CPB BTSD octets may be used per bundle.

## Selection

1. Validate the block and freshness window.
2. Authenticate and authorize the producer according to local policy.
3. Rank eligible CPBs by trust first, then evaluation time, then lowest block
   number.
4. Use one selected CPB; do not mix entries from producers.
5. Match only entries whose decision node is the local Node ID.

Absence of an entry is unknown, not probability zero.

## Security and fragmentation

- Unsigned CPB data must not override authenticated local routing information
  by default.
- A BIB-covered CPB cannot be modified; append a new CPB instead.
- A source applying a BIB to CPB also sets the primary block's
  `must-not-fragment` flag.
- A consumer does not use CPB found in a fragment for routing.
- CRC and integrity-service removal follow RFC 9171 and RFC 9173.

## Reference code

```sh
python3 -m pip install -r impl/requirements.txt
python3 -m pytest -q impl/test_cpb.py
python3 examples/simple_usage.py
```

Block type 200 is only a private/experimental test value pending IANA
assignment.
