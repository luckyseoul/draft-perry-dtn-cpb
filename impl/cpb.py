"""
cpb.py -- Contact Probability Block reference encoder/decoder.

Implements the CPB working draft Section 3.2 (CDDL schema) and Section 3.4
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
  - On encode: numeric probabilities are rounded to binary16. The private
    float helper's strict=True option rejects rounding or subnormal flushing.
  - On decode: untagged CBOR floats of all three widths are accepted and
    rejected if outside [0.0, 1.0]. NaN and +/-Inf are rejected per Section 3.4.1.
  - Positive probabilities below 2**-14 are flushed to zero, independently
    of the received float width, following the draft's binary16 policy.

Known fields are checked against their CBOR wire types before cbor2 converts
them to Python values. Unknown fields retain cbor2's semantic decoding,
including tags and shared references; byte-preserving re-encoding of unknown
values is not promised. Cyclic Python values are not supported on encode.
"""

from __future__ import annotations

import math
import io
import re
import struct
import cbor2
from cbor2._encoder import CBOREncoder as _PythonCBOREncoder

CPB_BLOCK_TYPE_EXAMPLE = 200  # Spec uses 0xC8 in examples until IANA assigns

# Field numbers from Spec Section 3.2.1 / Figure 4
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
METRIC_MAXPROP_DELIVERY_LIKELIHOOD = 2
METRIC_MAXPROP_COST = 2  # alias
METRIC_RAPID_UTILITY = 3
METRIC_GENERIC = 4

UINT64_MAX = (1 << 64) - 1
IPN_LOCAL_NODE = (1 << 32) - 1
MIN_NORMAL_BINARY16 = 2.0 ** -14
_UINT_FIELDS = (F_TIMESTAMP, F_VALIDITY, F_METRIC_TYPE, F_VERSION)


def _require_uint(value, field):
    if (not isinstance(value, int) or isinstance(value, bool)
            or not 0 <= value <= UINT64_MAX):
        raise ValueError(f"{field} must be an unsigned 64-bit integer, got {value!r}")
    return value


def _require_timestamp(data):
    if F_VALIDITY in data and F_TIMESTAMP not in data:
        raise ValueError("field 4 (validity) requires field 2 (timestamp)")


def _validate_next_hop(next_hop):
    """Validate the wire identity; scheme-specific aliases need routing context.

    Integers carry packed IPN FQNNs. Text carries a non-IPN URI; validation of
    its scheme-specific part and normalization for matching remain with the
    routing layer. This codec rejects duplicate exact identities, preserving
    the original spelling of text EIDs.
    """
    if isinstance(next_hop, int):
        _require_uint(next_hop, "path-entry next-hop")
        if next_hop == IPN_LOCAL_NODE:
            raise ValueError("IPN LocalNode cannot be sent as a next-hop reference")
    elif isinstance(next_hop, str):
        scheme, colon, ssp = next_hop.partition(":")
        if (not colon or not ssp
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*", scheme) is None
                or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in next_hop)):
            raise ValueError("text next-hop must be a full non-IPN EID URI")
        if scheme.lower() == "ipn":
            raise ValueError("IPN next-hop must be encoded as a packed uint FQNN")
    else:
        raise ValueError("path-entry next-hop must be uint or non-IPN EID text")
    return next_hop


class _CoreDeterministicEncoder(_PythonCBOREncoder):
    """Use RFC 8949 bytewise map ordering with the pinned cbor2 5.9 backend.

    cbor2's canonical mode otherwise uses length-first ordering. Its Python
    backend exposes the sortable-key hook, which also applies recursively to
    maps in arrays, tags, and other extension values. The aliases below accept
    objects returned by either the C or Python decoder backend.
    """

    def __init__(self, fp):
        super().__init__(fp, canonical=True)
        self._encoders[cbor2.CBORTag] = _PythonCBOREncoder.encode_semantic
        self._encoders[cbor2.CBORSimpleValue] = _PythonCBOREncoder.encode_simple_value
        self._encoders[type(cbor2.undefined)] = _PythonCBOREncoder.encode_undefined

    def encode_sortable_key(self, value):
        _, encoded = super().encode_sortable_key(value)
        return 0, encoded


def _core_dumps(value):
    stream = io.BytesIO()
    _CoreDeterministicEncoder(stream).encode(value)
    return stream.getvalue()


def _container_head(major, length):
    encoded = cbor2.dumps(length)
    return bytes([(major << 5) | encoded[0]]) + encoded[1:]


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
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"probability must be numeric, got {type(value).__name__}")
    if value < 0.0 or value > 1.0:
        raise ValueError(f"probability {value} outside [0.0, 1.0]")
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("NaN and +/-Inf are not valid probabilities (Spec 3.4.1)")
    if 0.0 < value < MIN_NORMAL_BINARY16:
        if strict:
            raise ValueError("strict=True forbids flushing a subnormal probability")
        value = 0.0
    return b"\xf9" + _float_to_binary16_bytes(value, strict=strict)


# ---------- encode ---------------------------------------------------------

def encode_cpb(data: dict) -> bytes:
    """Encode a cpb-data dict to CBOR bytes per Spec Section 3.2.

    The dict keys are the integer field numbers (0..7) plus optionally any
    uint > 7 for future-extension fields.

    Probability fields (0, 6, and the second element of each path-entry) are
    encoded as deterministic float16 per Spec Section 3.4.  All other fields
    use RFC 8949 Section 4.2.1 core deterministic ordering, including maps
    nested in extension values. Field 4 requires field 2.
    """
    # cbor2 doesn't have a knob to force float16 only for selected values, so
    # we hand-build the map header + entries and let cbor2 handle the
    # non-float pieces.
    if not isinstance(data, dict):
        raise TypeError("cpb-data must be a dict keyed by integer field number")

    for key in data:
        _require_uint(key, "cpb-data key")
    _require_timestamp(data)
    # UInt key order equals the bytewise order of the preferred CBOR encoding.
    keys = sorted(data.keys())
    pieces = [_container_head(5, len(keys))]

    for k in keys:
        pieces.append(cbor2.dumps(k, canonical=True))
        v = data[k]
        if k == F_DEFAULT_PROB or k == F_CONFIDENCE:
            pieces.append(_encode_prob_float16(v))
        elif k == F_PATH_ENTRIES:
            pieces.append(_encode_path_entries(v))
        elif k in _UINT_FIELDS:
            pieces.append(cbor2.dumps(_require_uint(v, f"field {k}"), canonical=True))
        elif k == F_SOURCE_PCE:
            if not isinstance(v, (bytes, bytearray)):
                raise ValueError("field 3 (source PCE) must be bstr (bytes)")
            pieces.append(cbor2.dumps(bytes(v), canonical=True))
        else:
            pieces.append(_core_dumps(v))
    return b"".join(pieces)


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
    pieces = [_container_head(4, len(entries))]
    seen = set()
    for entry in entries:
        if (not isinstance(entry, (list, tuple))) or len(entry) != 2:
            raise ValueError(
                f"path-entry must be a 2-element [next-hop, prob] pair, got {entry!r}"
            )
        next_hop, prob = entry
        _validate_next_hop(next_hop)
        if next_hop in seen:
            raise ValueError(f"duplicate path-entry next-hop {next_hop!r}")
        seen.add(next_hop)
        pieces.extend((b"\x82", cbor2.dumps(next_hop, canonical=True),
                       _encode_prob_float16(prob)))
    return b"".join(pieces)


def encode_btsd(data: dict) -> bytes:
    """Encode cpb-data as a CBOR byte string (the BTSD form per Spec 3.2)."""
    inner = encode_cpb(data)
    return cbor2.dumps(inner, canonical=True)  # cbor2 wraps as bstr


# ---------- decode ---------------------------------------------------------

class _WireReader:
    """Check wire types without losing duplicate keys or interpreting tags.

    cbor2 decodes the complete map after this structural pass, preserving
    shared references between extension fields. Indefinite-length containers
    remain valid on receive, as permitted by the BPv7 CBOR rules.
    """

    def __init__(self, buf):
        if not isinstance(buf, (bytes, bytearray, memoryview)):
            raise TypeError("CBOR input must be bytes")
        self.buf = bytes(buf)
        self.pos = 0

    def _take(self, count):
        end = self.pos + count
        if end > len(self.buf):
            raise ValueError("truncated CBOR item")
        value = self.buf[self.pos:end]
        self.pos = end
        return value

    def _head(self):
        initial = self._take(1)[0]
        major, ai = initial >> 5, initial & 31
        if ai < 24:
            argument = ai
        elif ai < 28:
            argument = int.from_bytes(self._take(1 << (ai - 24)), "big")
        elif ai == 31:
            argument = None
        else:
            raise ValueError("reserved CBOR additional information")
        return major, ai, argument

    def _break(self):
        if self.pos < len(self.buf) and self.buf[self.pos] == 0xff:
            self.pos += 1
            return True
        return False

    def _members(self, major, label):
        actual, _, length = self._head()
        if actual != major:
            raise ValueError(f"{label} has the wrong CBOR wire type")
        if length is None:
            while not self._break():
                yield
        else:
            for _ in range(length):
                yield

    def _uint(self, label):
        major, _, value = self._head()
        if major != 0 or value is None:
            raise ValueError(f"{label} must be an untagged CBOR uint")
        return value

    def _float(self, label):
        major, ai, _ = self._head()
        if major != 7 or ai not in (25, 26, 27):
            raise ValueError(f"{label} must be an untagged CBOR float")

    def _typed_item(self, majors, label):
        if self.pos == len(self.buf) or self.buf[self.pos] >> 5 not in majors:
            raise ValueError(f"{label} has the wrong CBOR wire type")
        self._skip()

    def _skip(self, depth=0):
        if depth > 400:
            raise ValueError("CBOR nesting exceeds the decoder resource limit")
        major, ai, argument = self._head()
        if major in (0, 1):
            if argument is None:
                raise ValueError("indefinite-length CBOR integer")
        elif major in (2, 3):
            if argument is not None:
                self._take(argument)
            else:
                while not self._break():
                    chunk_major, _, length = self._head()
                    if chunk_major != major or length is None:
                        raise ValueError("invalid indefinite-length string chunk")
                    self._take(length)
        elif major in (4, 5):
            remaining = argument
            while remaining is None or remaining > 0:
                if remaining is None and self._break():
                    break
                self._skip(depth + 1)
                if major == 5:
                    self._skip(depth + 1)
                if remaining is not None:
                    remaining -= 1
        elif major == 6:
            if argument is None:
                raise ValueError("indefinite-length CBOR tag")
            self._skip(depth + 1)
        elif ai == 31 or (ai == 24 and argument < 32):
            raise ValueError("invalid CBOR simple value or unexpected break")

    def cpb(self):
        seen = set()
        for _ in self._members(5, "cpb-data"):
            key = self._uint("cpb-data key")
            if key in seen:
                raise ValueError(f"duplicate cpb-data key {key}")
            seen.add(key)
            if key in (F_DEFAULT_PROB, F_CONFIDENCE):
                self._float(f"field {key}")
            elif key == F_PATH_ENTRIES:
                for _ in self._members(4, "path-entries"):
                    count = 0
                    for _ in self._members(4, "path-entry"):
                        if count == 0:
                            self._typed_item((0, 3), "path-entry next-hop")
                        elif count == 1:
                            self._float("path-entry probability")
                        else:
                            raise ValueError("path-entry must have exactly two elements")
                        count += 1
                    if count != 2:
                        raise ValueError("path-entry must have exactly two elements")
            elif key in _UINT_FIELDS:
                self._uint(f"field {key}")
            elif key == F_SOURCE_PCE:
                self._typed_item((2,), "field 3 (source PCE)")
            else:
                self._skip()
        self.finish()

    def finish(self):
        if self.pos != len(self.buf):
            raise ValueError("trailing bytes after CBOR item")


def decode_cpb(buf: bytes) -> dict:
    """Decode CBOR bytes into a cpb-data dict, validating per Spec 3.4.1.

    Probability values outside [0.0, 1.0], NaN, and +/-Inf raise
    ValueError per Spec 3.4 / 3.4.1. Unknown extension fields (uint > 7) retain
    cbor2's semantic values. Rejects duplicate keys, wrong known-field wire
    types, incomplete items, and trailing bytes before semantic decoding.
    """
    _WireReader(buf).cpb()
    raw = cbor2.loads(buf)
    _require_timestamp(raw)

    out = {}
    for k, v in raw.items():
        if k == F_DEFAULT_PROB or k == F_CONFIDENCE:
            out[k] = _validate_prob(v, field=k)
        elif k == F_PATH_ENTRIES:
            out[k] = _validate_path_entries(v)
        else:
            out[k] = v
    return out


def _validate_prob(v, field):
    if not isinstance(v, float):
        raise ValueError(f"field {field} must decode to a float, got {type(v).__name__}")
    f = v
    if math.isnan(f):
        raise ValueError(f"field {field} is NaN; Spec 3.4.1 rejects as malformed")
    if math.isinf(f):
        raise ValueError(f"field {field} is +/-Inf; Spec 3.4.1 rejects as malformed")
    # Reject out-of-range finite values per Spec 3.4 / 3.4.1 (do not clamp).
    if f < 0.0 or f > 1.0:
        raise ValueError(
            f"field {field}={f} outside [0.0, 1.0]; Spec 3.4.1 rejects as malformed"
        )
    if 0.0 < f < MIN_NORMAL_BINARY16:
        return 0.0
    return f


def _validate_path_entries(entries):
    if not isinstance(entries, list):
        raise ValueError("path-entries must decode to a CBOR array")
    out = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError(f"path-entry must be a 2-element array, got {entry!r}")
        next_hop, prob = entry
        _validate_next_hop(next_hop)
        if next_hop in seen:
            raise ValueError(f"duplicate path-entry next-hop {next_hop!r}")
        seen.add(next_hop)
        out.append([next_hop, _validate_prob(prob, field="path-entry-prob")])
    return out


def decode_btsd(buf: bytes) -> dict:
    """Decode BTSD bstr (which itself contains CBOR cpb-data) into a dict."""
    reader = _WireReader(buf)
    reader._typed_item((2,), "BTSD")
    reader.finish()
    inner = cbor2.loads(buf)
    return decode_cpb(bytes(inner))
