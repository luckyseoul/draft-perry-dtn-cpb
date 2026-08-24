"""Byte-level conformance tests for the CPB reference implementation."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cbor2
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cpb


def sample_data() -> dict:
    return {
        cpb.F_ENTRIES: [
            [cpb.ipn_eid(200), cpb.ipn_eid(100), 0.75],
            [cpb.ipn_eid(200), cpb.dtn_eid("//relay.example/"), 0.5],
        ],
        cpb.F_EVALUATION_TIME: 16_203_904,
        cpb.F_VALIDITY_DURATION: 3_600_000,
        cpb.F_PRODUCER_NODE: cpb.ipn_eid(50),
    }


def test_binary16_reference_values():
    expected = {
        0.0: "F90000",
        0.25: "F93400",
        0.5: "F93800",
        0.75: "F93A00",
        0.95: "F93B9A",
        1.0: "F93C00",
    }
    for value, wire_hex in expected.items():
        assert cpb._encode_probability(value).hex().upper() == wire_hex


def test_exact_cpb_vector():
    # Filled from the independently readable diagnostic structure above and
    # pinned so encoder changes cannot silently alter the protocol bytes.
    expected_hex = (
        "A400828382028218C800820282186400F93A008382028218C800"
        "8201702F2F72656C61792E6578616D706C652FF93800011A00"
        "F74080021A0036EE8003820282183200"
    )
    encoded = cpb.encode_cpb(sample_data())
    assert encoded.hex().upper() == expected_hex
    assert cpb.decode_cpb(encoded) == cpb.decode_cpb(bytes.fromhex(expected_hex))
    assert cpb.encode_cpb(cpb.decode_cpb(encoded)) == encoded


def test_btsd_and_canonical_block_roundtrip():
    data = sample_data()
    assert cpb.decode_btsd(cpb.encode_btsd(data)) == cpb.decode_cpb(cpb.encode_cpb(data))
    block = cpb.encode_canonical_block(data)
    assert cpb.decode_canonical_block(block) == cpb.decode_cpb(cpb.encode_cpb(data))
    assert block[:5] == bytes.fromhex("8518C80200")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, -0.1, 1.1])
def test_encoder_rejects_invalid_probability(value):
    data = sample_data()
    data[cpb.F_ENTRIES][0][2] = value
    with pytest.raises(ValueError):
        cpb.encode_cpb(data)


def test_negative_zero_is_positive_zero():
    assert cpb._encode_probability(-0.0) == bytes.fromhex("F90000")


def test_binary16_rounding_and_strict_mode():
    assert cpb._encode_probability(0.123456789).startswith(b"\xf9")
    with pytest.raises(ValueError):
        cpb._encode_probability(0.123456789, strict=True)


def test_decoder_rejects_wider_float_even_when_value_is_valid():
    encoded = cpb.encode_cpb(sample_data())
    wider = encoded.replace(bytes.fromhex("F93A00"), bytes.fromhex("FA3F400000"), 1)
    with pytest.raises(ValueError, match="deterministically"):
        cpb.decode_cpb(wider)


def test_decoder_rejects_integer_probability():
    data = sample_data()
    raw = {
        0: [[cpb.ipn_eid(200), cpb.ipn_eid(100), 1]],
        1: data[1],
        2: data[2],
        3: data[3],
    }
    with pytest.raises(ValueError, match="float"):
        cpb.decode_cpb(cbor2.dumps(raw, canonical=True))


def test_all_four_fields_are_required():
    for field in cpb.REQUIRED_FIELDS:
        data = sample_data()
        del data[field]
        with pytest.raises(ValueError, match="missing required"):
            cpb.encode_cpb(data)


def test_entry_count_is_bounded():
    data = sample_data()
    data[cpb.F_ENTRIES] = []
    with pytest.raises(ValueError, match="1..8"):
        cpb.encode_cpb(data)
    data[cpb.F_ENTRIES] = [
        [cpb.ipn_eid(200), cpb.ipn_eid(node), 0.5] for node in range(9)
    ]
    with pytest.raises(ValueError, match="1..8"):
        cpb.encode_cpb(data)


def test_duplicate_actions_use_scheme_defined_ipn_identity():
    data = sample_data()
    # ipn:200.0 and ipn:0.200.0 are the same decoded EID under RFC 9758.
    data[cpb.F_ENTRIES] = [
        [[2, [200, 0]], [2, [100, 0]], 0.5],
        [[2, [0, 200, 0]], [2, [0, 100, 0]], 0.6],
    ]
    with pytest.raises(ValueError, match="duplicate"):
        cpb.encode_cpb(data)


@pytest.mark.parametrize(
    "field,value",
    [
        (cpb.F_EVALUATION_TIME, -1),
        (cpb.F_VALIDITY_DURATION, 0),
        (cpb.F_VALIDITY_DURATION, -1),
        (cpb.F_PRODUCER_NODE, "ipn:50.0"),
    ],
)
def test_invalid_required_fields(field, value):
    data = sample_data()
    data[field] = value
    with pytest.raises(ValueError):
        cpb.encode_cpb(data)


def test_null_endpoint_is_not_a_node_identifier():
    data = sample_data()
    data[cpb.F_PRODUCER_NODE] = [1, 0]
    with pytest.raises(ValueError, match="null endpoint"):
        cpb.encode_cpb(data)
    data = sample_data()
    data[cpb.F_ENTRIES][0][1] = [1, 0]
    with pytest.raises(ValueError, match="null endpoint"):
        cpb.encode_cpb(data)


def test_extension_fields_are_preserved_deterministically():
    data = sample_data()
    data[10] = b"opaque-extension"
    assert cpb.decode_cpb(cpb.encode_cpb(data))[10] == b"opaque-extension"


def test_trailing_bytes_are_rejected():
    with pytest.raises(ValueError, match="trailing"):
        cpb.decode_cpb(cpb.encode_cpb(sample_data()) + b"\x00")
    with pytest.raises(ValueError, match="trailing"):
        cpb.decode_btsd(cpb.encode_btsd(sample_data()) + b"\x00")


def test_bad_block_flags_are_rejected():
    block = bytearray(cpb.encode_canonical_block(sample_data()))
    block[4] = 0x01
    with pytest.raises(ValueError, match="flags"):
        cpb.decode_canonical_block(bytes(block))


def test_ipn_two_and_three_element_eids_match():
    assert cpb.eid_identity([2, [100, 7]]) == cpb.eid_identity([2, [0, 100, 7]])


def test_freshness_is_half_open_and_tolerance_is_explicit():
    data = sample_data()
    start = data[cpb.F_EVALUATION_TIME]
    end = start + data[cpb.F_VALIDITY_DURATION]
    assert cpb.is_fresh(data, start)
    assert cpb.is_fresh(data, end - 1)
    assert not cpb.is_fresh(data, end)
    assert cpb.is_fresh(data, end, tolerance_ms=1)


def test_entries_for_node_matches_normalized_eid():
    data = cpb.decode_cpb(cpb.encode_cpb(sample_data()))
    entries = cpb.entries_for_node(data, [2, [0, 200, 0]])
    assert len(entries) == 2


def _run_as_script() -> None:
    # Parametrized tests require pytest; invoke the complete suite in a subprocess
    # style through pytest's API when this file is run directly.
    raise SystemExit(pytest.main([str(Path(__file__).resolve()), "-q"]))


if __name__ == "__main__":
    _run_as_script()
