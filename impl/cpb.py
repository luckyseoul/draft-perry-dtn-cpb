"""Reference encoder and decoder for the Contact Probability Block (CPB).

The module implements the wire format in draft-perry-dtn-cpb-latest.  A CPB
contains one to eight bundle-conditioned forwarding entries.  Each entry is:

    [decision-node EID, candidate-next-hop EID, success probability]

Probabilities are always deterministic CBOR binary16 values.  The reference
decoder intentionally rejects wider floats, non-canonical CBOR, invalid EIDs,
out-of-range probabilities, missing fields, and duplicate forwarding actions.
"""

from __future__ import annotations

import math
import struct
from io import BytesIO
from typing import Any

import cbor2

CPB_BLOCK_TYPE_EXAMPLE = 200
CPB_BLOCK_FLAGS = 0x00
MAX_ENTRIES = 8
MAX_CPBS_PER_BUNDLE = 4
MAX_AGGREGATE_BTSD = 1024

F_ENTRIES = 0
F_EVALUATION_TIME = 1
F_VALIDITY_DURATION = 2
F_PRODUCER_NODE = 3
REQUIRED_FIELDS = frozenset(
    {F_ENTRIES, F_EVALUATION_TIME, F_VALIDITY_DURATION, F_PRODUCER_NODE}
)


def ipn_eid(node: int, service: int = 0, allocator: int = 0) -> list[Any]:
    """Build an RFC 9758 ipn EID using its preferred representation."""
    for label, value in (
        ("allocator", allocator),
        ("node", node),
        ("service", service),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(f"{label} must be a non-negative integer")
    if allocator >= 2**32 or node >= 2**32:
        raise ValueError("allocator and node must each fit in 32 bits")
    if allocator == 0:
        return [2, [node, service]]
    return [2, [allocator, node, service]]


def dtn_eid(scheme_specific_part: str | int) -> list[Any]:
    """Build an RFC 9171 dtn EID; integer 0 denotes dtn:none."""
    if scheme_specific_part != 0 and not isinstance(scheme_specific_part, str):
        raise ValueError("dtn scheme-specific part must be text or integer 0")
    return [1, scheme_specific_part]


def _float_to_binary16_bytes(value: float, *, strict: bool = False) -> bytes:
    """Convert to IEEE 754 binary16 using round-to-nearest, ties-to-even."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("probability must be numeric and not bool")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"probability {value!r} is outside finite [0, 1]")
    if value == 0.0:
        value = 0.0  # canonicalize negative zero
    try:
        packed = struct.pack(">e", value)
    except (OverflowError, struct.error) as exc:
        raise ValueError(f"probability {value!r} cannot be binary16") from exc
    if strict and struct.unpack(">e", packed)[0] != value:
        nearest = struct.unpack(">e", packed)[0]
        raise ValueError(
            f"probability {value!r} is not exactly binary16; nearest is {nearest!r}"
        )
    return packed


def _encode_probability(value: float, *, strict: bool = False) -> bytes:
    return b"\xf9" + _float_to_binary16_bytes(value, strict=strict)


# Retain the former helper name for callers that used it in demonstrations.
_encode_prob_float16 = _encode_probability


def _validate_eid(value: Any, *, label: str = "EID") -> list[Any]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must be a two-item BP EID array")
    scheme, ssp = value
    if type(scheme) is not int or scheme < 0:
        raise ValueError(f"{label} URI scheme code must be uint")

    if scheme == 1:
        if ssp != 0 and not isinstance(ssp, str):
            raise ValueError(f"{label} dtn SSP must be text or integer 0")
    elif scheme == 2:
        if not isinstance(ssp, (list, tuple)) or len(ssp) not in (2, 3):
            raise ValueError(f"{label} ipn SSP must contain two or three uints")
        if any(type(item) is not int or item < 0 for item in ssp):
            raise ValueError(f"{label} ipn SSP items must be uints")
        if len(ssp) == 3 and (ssp[0] >= 2**32 or ssp[1] >= 2**32):
            raise ValueError(f"{label} ipn allocator and node must fit in 32 bits")

    # Lists are the public representation even if tuples were accepted.
    normalized_ssp = list(ssp) if isinstance(ssp, tuple) else ssp
    return [scheme, normalized_ssp]


def _validate_node_id(value: Any, *, label: str) -> list[Any]:
    eid = _validate_eid(value, label=label)
    if eid == [1, 0]:
        raise ValueError(f"{label} cannot be the null endpoint dtn:none")
    return eid


def eid_identity(eid: Any) -> tuple[Any, ...]:
    """Return a scheme-aware identity suitable for EID matching."""
    scheme, ssp = _validate_eid(eid)
    if scheme == 2:
        if len(ssp) == 2:
            fqnn, service = ssp
            return (2, fqnn >> 32, fqnn & 0xFFFFFFFF, service)
        allocator, node, service = ssp
        return (2, allocator, node, service)
    if scheme == 1:
        return (1, ssp)
    return (scheme, cbor2.dumps(ssp, canonical=True))


def _encode_entries(entries: Any) -> bytes:
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError(f"entries must be a list containing 1..{MAX_ENTRIES} items")
    out = bytes([0x80 | len(entries)])
    seen: set[tuple[tuple[Any, ...], tuple[Any, ...]]] = set()
    for entry in entries:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise ValueError("each entry must be [decision EID, next-hop EID, probability]")
        decision = _validate_node_id(entry[0], label="decision-node")
        next_hop = _validate_node_id(entry[1], label="candidate-next-hop")
        identity = (eid_identity(decision), eid_identity(next_hop))
        if identity in seen:
            raise ValueError("duplicate decision-node/candidate-next-hop pair")
        seen.add(identity)
        out += b"\x83"
        out += cbor2.dumps(decision, canonical=True)
        out += cbor2.dumps(next_hop, canonical=True)
        out += _encode_probability(entry[2])
    return out


def encode_cpb(data: dict[int, Any]) -> bytes:
    """Encode a cpb-data map using deterministic CBOR."""
    if not isinstance(data, dict):
        raise TypeError("cpb-data must be a dict keyed by unsigned integers")
    if any(type(key) is not int or key < 0 for key in data):
        raise ValueError("all cpb-data keys must be unsigned integers")
    missing = REQUIRED_FIELDS.difference(data)
    if missing:
        raise ValueError(f"missing required CPB fields: {sorted(missing)}")

    keys = sorted(data)
    if len(keys) >= 24:
        raise ValueError("reference encoder supports fewer than 24 map fields")
    out = bytes([0xA0 | len(keys)])
    for key in keys:
        out += cbor2.dumps(key, canonical=True)
        value = data[key]
        if key == F_ENTRIES:
            out += _encode_entries(value)
        elif key == F_EVALUATION_TIME:
            if type(value) is not int or value < 0:
                raise ValueError("evaluation-time must be uint")
            out += cbor2.dumps(value, canonical=True)
        elif key == F_VALIDITY_DURATION:
            if type(value) is not int or value <= 0:
                raise ValueError("validity-duration must be a positive uint")
            out += cbor2.dumps(value, canonical=True)
        elif key == F_PRODUCER_NODE:
            out += cbor2.dumps(
                _validate_node_id(value, label="producer-node"), canonical=True
            )
        else:
            out += cbor2.dumps(value, canonical=True)
    return out


def _loads_one(buf: bytes, label: str) -> Any:
    if not isinstance(buf, (bytes, bytearray)):
        raise TypeError(f"{label} input must be bytes")
    stream = BytesIO(bytes(buf))
    try:
        value = cbor2.CBORDecoder(stream).decode()
    except Exception as exc:
        raise ValueError(f"invalid {label} CBOR: {exc}") from exc
    if stream.read(1):
        raise ValueError(f"trailing bytes after {label}")
    return value


def _validate_probability(value: Any) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise ValueError("probability must decode as a finite CBOR float")
    if not 0.0 <= value <= 1.0:
        raise ValueError("probability is outside [0, 1]")
    if value == 0.0:
        return 0.0
    return value


def _validate_entries(entries: Any) -> list[list[Any]]:
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError(f"entries must contain 1..{MAX_ENTRIES} items")
    out: list[list[Any]] = []
    seen: set[tuple[tuple[Any, ...], tuple[Any, ...]]] = set()
    for entry in entries:
        if not isinstance(entry, list) or len(entry) != 3:
            raise ValueError("forwarding entry must be a three-item array")
        decision = _validate_node_id(entry[0], label="decision-node")
        next_hop = _validate_node_id(entry[1], label="candidate-next-hop")
        identity = (eid_identity(decision), eid_identity(next_hop))
        if identity in seen:
            raise ValueError("duplicate decision-node/candidate-next-hop pair")
        seen.add(identity)
        out.append([decision, next_hop, _validate_probability(entry[2])])
    return out


def decode_cpb(buf: bytes) -> dict[int, Any]:
    """Decode and strictly validate deterministic CPB CBOR."""
    original = bytes(buf)
    raw = _loads_one(original, "cpb-data")
    if not isinstance(raw, dict):
        raise ValueError("cpb-data must be a CBOR map")  # noqa: TRY004 - wire error
    if any(type(key) is not int or key < 0 for key in raw):
        raise ValueError("all cpb-data keys must be unsigned integers")
    missing = REQUIRED_FIELDS.difference(raw)
    if missing:
        raise ValueError(f"missing required CPB fields: {sorted(missing)}")

    out: dict[int, Any] = {}
    for key, value in raw.items():
        if key == F_ENTRIES:
            out[key] = _validate_entries(value)
        elif key == F_EVALUATION_TIME:
            if type(value) is not int or value < 0:
                raise ValueError("evaluation-time must decode as uint")
            out[key] = value
        elif key == F_VALIDITY_DURATION:
            if type(value) is not int or value <= 0:
                raise ValueError("validity-duration must decode as positive uint")
            out[key] = value
        elif key == F_PRODUCER_NODE:
            out[key] = _validate_node_id(value, label="producer-node")
        else:
            out[key] = value

    # This byte comparison enforces map ordering, preferred integer encoding,
    # binary16 probability width, positive zero, and deterministic extensions.
    if encode_cpb(out) != original:
        raise ValueError("cpb-data is not deterministically encoded")
    return out


def encode_btsd(data: dict[int, Any]) -> bytes:
    """Encode the complete BP block-type-specific data CBOR bstr."""
    return cbor2.dumps(encode_cpb(data), canonical=True)


def decode_btsd(buf: bytes) -> dict[int, Any]:
    """Decode a serialized BP block-type-specific data CBOR bstr."""
    value = _loads_one(buf, "BTSD")
    if not isinstance(value, (bytes, bytearray)):
        raise ValueError("BTSD must be a bstr containing cpb-data")  # noqa: TRY004
    return decode_cpb(bytes(value))


def encode_canonical_block(
    data: dict[int, Any],
    *,
    block_type: int = CPB_BLOCK_TYPE_EXAMPLE,
    block_number: int = 2,
) -> bytes:
    """Encode a CRC-type-zero canonical block for protected test vectors.

    A real bundle may use CRC type zero only when permitted by RFC 9171 and
    RFC 9173, normally because an applicable BIB integrity service is present.
    """
    if type(block_type) is not int or block_type < 0:
        raise ValueError("block type must be uint")
    if type(block_number) is not int or block_number <= 1:
        raise ValueError("extension block number must be greater than 1")
    return cbor2.dumps(
        [block_type, block_number, CPB_BLOCK_FLAGS, 0, encode_cpb(data)],
        canonical=True,
    )


def decode_canonical_block(
    buf: bytes, *, expected_block_type: int = CPB_BLOCK_TYPE_EXAMPLE
) -> dict[int, Any]:
    """Decode the CRC-type-zero canonical-block test-vector form."""
    block = _loads_one(buf, "canonical block")
    if not isinstance(block, list) or len(block) != 5:
        raise ValueError("CRC-type-zero canonical block must have five items")
    block_type, block_number, flags, crc_type, block_data = block
    if type(block_type) is not int or block_type != expected_block_type:
        raise ValueError(f"unexpected CPB block type {block_type!r}")
    if type(block_number) is not int or block_number <= 1:
        raise ValueError("extension block number must be greater than 1")
    if type(flags) is not int or flags != CPB_BLOCK_FLAGS:
        raise ValueError(f"CPB block flags must be 0x{CPB_BLOCK_FLAGS:02x}")
    if crc_type != 0:
        raise ValueError("reference canonical-block decoder accepts CRC type zero only")
    if not isinstance(block_data, (bytes, bytearray)):
        raise ValueError("canonical-block data must be a CBOR bstr")  # noqa: TRY004
    return decode_cpb(bytes(block_data))


def is_fresh(data: dict[int, Any], now_dtn_ms: int, *, tolerance_ms: int = 0) -> bool:
    """Return whether a validated CPB is inside its half-open validity window."""
    if type(now_dtn_ms) is not int or type(tolerance_ms) is not int or tolerance_ms < 0:
        raise ValueError("times must be integer milliseconds and tolerance non-negative")
    start = data[F_EVALUATION_TIME]
    end = start + data[F_VALIDITY_DURATION]
    return start - tolerance_ms <= now_dtn_ms < end + tolerance_ms


def entries_for_node(data: dict[int, Any], local_node: Any) -> list[list[Any]]:
    """Return entries whose decision-node matches the supplied Node ID."""
    local_identity = eid_identity(local_node)
    return [entry for entry in data[F_ENTRIES] if eid_identity(entry[0]) == local_identity]
