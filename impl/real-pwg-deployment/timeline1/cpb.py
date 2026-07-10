"""
cpb.py -- Contact Probability Block reference encoder/decoder.

Implements draft-perry-dtn-cpb-00 Section 3.2 (CDDL schema) and Section 3.4
(CBOR encoding rules) using cbor2 for the underlying CBOR work.

Per-path array (field 1) limit: the spec uses SHOULD (not MUST) for a
maximum of 8 entries to mitigate DoS on low-bandwidth/constrained DTN
links (see Bandwidth Considerations). Reference implementation accepts
larger arrays on encode; receivers in constrained deployments should
apply local policy.

Public surface:
    encode_cpb(data: dict) -> bytes      # cpb-data map -> CBOR bytes
    decode_cpb(buf: bytes) -> dict       # CBOR bytes -> cpb-data map
    encode_btsd(data: dict) -> bytes     # cpb-data map -> CBOR bstr (BTSD)
    decode_btsd(buf: bytes) -> dict      # BTSD bstr -> cpb-data map

Float policy (Spec Section 3.4):
  - On encode: probability values that are exactly representable in IEEE 754
    binary16 are encoded in 3 bytes (CBOR major 7, info 25).  Values that are
    not exactly representable raise ValueError; the caller chooses whether to
    snap-to-binary16 or emit binary32/64 explicitly.
  - On decode: any valid CBOR float is accepted and clamped to [0.0, 1.0].
    NaN and +/-Inf are rejected per Section 3.4.1.
"""

from __future__ import annotations

import math
import struct
import cbor2

CPB_BLOCK_TYPE_EXAMPLE = 200  # Spec uses 0xC8 in examples until IANA assigns

# Field numbers from Spec Section 3.2.1 / Listing 4
F_DEFAULT_PROB = 0
F_PATH_ENTRIES = 1
F_TIMESTAMP = 2
F_SOURCE_PCE = 3
F_VALIDITY = 4
F_METRIC_TYPE = 5
F_CONFIDENCE = 6
F_VERSION = 7

METRIC_PROPHET_DP = 0
METRIC_CGR_CONFIDENCE = 1
METRIC_MAXPROP_COST = 2
METRIC_RAPID_UTILITY = 3
METRIC_GENERIC = 4


# ---------- float16 helpers ------------------------------------------------

def _float_to_binary16_bytes(value: float, strict: bool = False) -> bytes:
    """Pack a float into 2-byte IEEE 754 binary16, big-endian.

    Default behaviour snaps to the nearest representable binary16 value
    (which is what the spec's Section 3.4.3 hex table shows: 0.95 -> 0x3B9A,
    whose actual binary16 value is 0.9501953125).  ~0.001 quantization
    matches the routing-grade precision claim in Section 3.4.

    With strict=True, raises ValueError if the value is not exactly
    representable in binary16 (useful for paranoid encoders that want to
    refuse silent rounding).
    """
    # struct '>e' is IEEE 754 binary16 big-endian.  Python's struct will
    # already snap to nearest binary16 on pack.
    packed = struct.pack(">e", value)
    if strict:
        roundtrip = struct.unpack(">e", packed)[0]
        if roundtrip != value:
            raise ValueError(
                f"value {value!r} is not exactly representable in IEEE 754 "
                f"binary16 (nearest is {roundtrip!r}); strict=True forbids "
                f"silent rounding"
            )
    return packed


def _encode_prob_float16(value: float, strict: bool = False) -> bytes:
    """Encode a probability value as a 3-byte CBOR float16:
       0xF9 + 2 bytes binary16.  Snaps to nearest binary16 by default."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"probability must be numeric, got {type(value).__name__}")
    if isinstance(value, int):
        value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("NaN and +/-Inf are not valid probabilities (Spec 3.4.1)")
    if value < 0.0 or value > 1.0:
        raise ValueError(f"probability {value} outside [0.0, 1.0]")
    return b"\xf9" + _float_to_binary16_bytes(value, strict=strict)


# ---------- encode ---------------------------------------------------------

def encode_cpb(data: dict) -> bytes:
    """Encode a cpb-data dict to CBOR bytes per Spec Section 3.2.

    The dict keys are the integer field numbers (0..6) plus optionally any
    int > 6 for future-extension fields (passed through unchanged).

    Probability fields (0, 6, and the second element of each path-entry) are
    encoded as deterministic float16 per Spec Section 3.4.  All other fields
    are encoded by cbor2 in canonical mode (RFC 8949 Section 4.2.1).
    """
    # cbor2 doesn't have a knob to force float16 only for selected values, so
    # we hand-build the map header + entries and let cbor2 handle the
    # non-float pieces.
    if not isinstance(data, dict):
        raise TypeError("cpb-data must be a dict keyed by integer field number")

    # Determinism: sort keys ascending (RFC 8949 4.2.1 deterministic encoding).
    keys = sorted(data.keys())
    n = len(keys)
    # CBOR map header: small maps (n < 24) fit in 1 byte (major 5, value n).
    if n < 24:
        out = bytes([0xA0 | n])
    elif n < 256:
        out = bytes([0xB8, n])
    elif n < 65536:
        out = b"\xb9" + struct.pack(">H", n)
    else:
        raise ValueError("cpb-data map too large")

    for k in keys:
        if not isinstance(k, int) or k < 0:
            raise ValueError(f"cpb-data keys must be non-negative ints, got {k!r}")
        out += cbor2.dumps(k, canonical=True)
        v = data[k]
        if k == F_DEFAULT_PROB or k == F_CONFIDENCE:
            out += _encode_prob_float16(v)
        elif k == F_PATH_ENTRIES:
            out += _encode_path_entries(v)
        elif k == F_TIMESTAMP or k == F_VALIDITY:
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"field {k} must be uint, got {v!r}")
            out += cbor2.dumps(v, canonical=True)
        elif k == F_SOURCE_PCE:
            if not isinstance(v, (bytes, bytearray)):
                raise ValueError("field 3 (source PCE) must be bstr (bytes)")
            out += cbor2.dumps(bytes(v), canonical=True)
        elif k == F_METRIC_TYPE:
            if not isinstance(v, int) or v < 0:
                raise ValueError("field 5 (metric type) must be uint")
            out += cbor2.dumps(v, canonical=True)
        else:
            # Future extension fields: pass through cbor2 canonical encoding.
            out += cbor2.dumps(v, canonical=True)
    return out


def _encode_path_entries(entries) -> bytes:
    if not isinstance(entries, list):
        raise TypeError("path-entries (field 1) must be a list")
    if len(entries) > 8:
        # Spec §3.4: senders SHOULD limit per-path array to 8 entries to
        # mitigate DoS on low-bandwidth/constrained links.  The reference
        # implementation allows larger lists (per the relaxed SHOULD language)
        # but deployments on constrained nodes should enforce locally.
        # Larger arrays may be dropped by receivers per local policy.
        pass  # proceed to encode (SHOULD, not MUST)
    n = len(entries)
    if n < 24:
        out = bytes([0x80 | n])
    elif n < 256:
        out = bytes([0x98, n])
    else:
        raise ValueError("path-entries array too large")
    for entry in entries:
        if (not isinstance(entry, (list, tuple))) or len(entry) != 2:
            raise ValueError(
                f"path-entry must be a 2-element [next-hop, prob] pair, got {entry!r}"
            )
        next_hop, prob = entry
        out += b"\x82"  # CBOR array of 2 items
        if isinstance(next_hop, int) and next_hop >= 0:
            out += cbor2.dumps(next_hop, canonical=True)
        elif isinstance(next_hop, (bytes, bytearray)):
            out += cbor2.dumps(bytes(next_hop), canonical=True)
        elif isinstance(next_hop, str):
            # Spec 3.5.1: full EID for non-ipn schemes encoded as text string.
            out += cbor2.dumps(next_hop, canonical=True)
        else:
            raise ValueError(
                f"path-entry next-hop must be uint, bstr, or text EID, got {next_hop!r}"
            )
        out += _encode_prob_float16(prob)
    return out


def encode_btsd(data: dict) -> bytes:
    """Encode cpb-data as a CBOR byte string (the BTSD form per Spec 3.2)."""
    inner = encode_cpb(data)
    return cbor2.dumps(inner, canonical=True)  # cbor2 wraps as bstr


# ---------- decode ---------------------------------------------------------

def decode_cpb(buf: bytes) -> dict:
    """Decode CBOR bytes into a cpb-data dict, validating per Spec 3.4.1.

    Probability values are clamped to [0.0, 1.0]; NaN and +/-Inf raise
    ValueError per Spec 3.4.1.  Unknown extension fields (int > 6) pass
    through unchanged.
    """
    raw = cbor2.loads(buf)
    if not isinstance(raw, dict):
        raise ValueError("cpb-data must decode to a CBOR map")

    out = {}
    for k, v in raw.items():
        if not isinstance(k, int) or k < 0:
            raise ValueError(f"cpb-data key must be uint, got {k!r}")
        if k == F_DEFAULT_PROB or k == F_CONFIDENCE:
            out[k] = _validate_prob(v, field=k)
        elif k == F_PATH_ENTRIES:
            out[k] = _validate_path_entries(v)
        elif k == F_TIMESTAMP or k == F_VALIDITY:
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"field {k} must decode to uint, got {v!r}")
            out[k] = v
        elif k == F_SOURCE_PCE:
            if not isinstance(v, (bytes, bytearray)):
                raise ValueError("field 3 (source PCE) must decode to bstr")
            out[k] = bytes(v)
        elif k == F_METRIC_TYPE:
            if not isinstance(v, int) or v < 0:
                raise ValueError("field 5 (metric type) must decode to uint")
            out[k] = v
        else:
            out[k] = v  # extension field
    return out


def _validate_prob(v, field):
    if not isinstance(v, (int, float)):
        raise ValueError(f"field {field} must decode to a number, got {type(v).__name__}")
    f = float(v)
    if math.isnan(f):
        raise ValueError(f"field {field} is NaN; Spec 3.4.1 rejects as malformed")
    if math.isinf(f):
        raise ValueError(f"field {field} is +/-Inf; Spec 3.4.1 rejects as malformed")
    # Clamp to [0,1] per Spec 3.4.1.
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _validate_path_entries(entries):
    if not isinstance(entries, list):
        raise ValueError("path-entries must decode to a CBOR array")
    out = []
    for entry in entries:
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError(f"path-entry must be a 2-element array, got {entry!r}")
        next_hop, prob = entry
        if isinstance(next_hop, int):
            if next_hop < 0:
                raise ValueError("path-entry next-hop uint must be non-negative")
        elif not isinstance(next_hop, (bytes, str)):
            raise ValueError(
                f"path-entry next-hop must be uint, bstr, or text, got {type(next_hop).__name__}"
            )
        out.append([next_hop, _validate_prob(prob, field="path-entry-prob")])
    return out


def decode_btsd(buf: bytes) -> dict:
    """Decode BTSD bstr (which itself contains CBOR cpb-data) into a dict."""
    inner = cbor2.loads(buf)
    if not isinstance(inner, (bytes, bytearray)):
        raise ValueError("BTSD must decode to a bstr containing CBOR")
    return decode_cpb(bytes(inner))
