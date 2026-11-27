"""Wire-level CPB regressions, including all 65,536 binary16 bit patterns.

Run with ``python3 impl/test_cpb_validation.py`` from the repository root.
These vectors deliberately bypass encode_cpb when constructing malformed
inputs: a Python dict cannot represent duplicate CBOR map keys.

Field 3 (producer node ID) is mandatory, so most hand-built vectors are
passed through ``wp()``, which adds producer ipn:200.0 to a definite or
indefinite-length top-level map.
"""

import math
import struct
import unittest

import cbor2
import cpb

ROVER = [2, [200, 0]]
ORBITER = [2, [100, 0]]
PRODUCER_WIRE = b"\x03" + cbor2.dumps(ROVER)  # 03 82 02 82 18c8 00
NH100 = bytes.fromhex("82028218 6400".replace(" ", ""))  # ipn:100.0


def wp(wire):
    """Add the producer field to a top-level map built by hand."""
    if wire[0] == 0xbf:
        assert wire[-1] == 0xff
        return wire[:-1] + PRODUCER_WIRE + b"\xff"
    assert 0xa0 <= wire[0] <= 0xb6
    return bytes([wire[0] + 1]) + wire[1:] + PRODUCER_WIRE


def field_wire(key, value_wire):
    return wp(b"\xa1" + cbor2.dumps(key) + value_wire)


def probability_wires(value_wire):
    return (field_wire(0, value_wire), field_wire(6, value_wire),
            wp(b"\xa1\x01\x81\x82" + NH100 + value_wire))


def d(**fields):
    """cpb-data with the mandatory producer."""
    out = {3: ROVER}
    out.update({int(k[1:]): v for k, v in fields.items()})
    return out


class CPBValidationTests(unittest.TestCase):
    def reject(self, wire):
        with self.assertRaises((ValueError, cbor2.CBORDecodeError)):
            cpb.decode_cpb(wire)

    def test_producer_is_mandatory(self):
        with self.assertRaisesRegex(ValueError, "producer"):
            cpb.encode_cpb({0: 0.5})
        with self.assertRaisesRegex(ValueError, "producer"):
            cpb.decode_cpb(bytes.fromhex("a100f93800"))
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(d(f0=0.5))), d(f0=0.5))

    def test_producer_and_next_hop_must_be_node_eids(self):
        bad = ([1, 0],                      # dtn:none
               [2, [0, cpb.IPN_LOCAL_NODE, 0]],  # LocalNode, 3-element form
               [2, [cpb.IPN_LOCAL_NODE, 0]],     # LocalNode, 2-element form
               [2, [100]], [2, [1, 2, 3, 4]], [2, 100], [2, "100.0"],
               [2, [1 << 32, 1, 0]], [1, "node"], [1, "//"], [1, b"//n/"],
               [2, [-1, 0]], [2, [True, 0]], [2, [1.0, 0]],
               100, "dtn://node/", [2], [2, [1, 0], 0], None)
        for eid in bad:
            with self.subTest(eid=eid):
                with self.assertRaises((TypeError, ValueError)):
                    cpb.encode_cpb({3: eid})
                with self.assertRaises((TypeError, ValueError)):
                    cpb.encode_cpb(d(f1=[[eid, 0.5]]))
                self.reject(cbor2.dumps({3: eid}))
                self.reject(cbor2.dumps({3: ROVER, 1: [[eid, 0.5]]}))

    def test_duplicate_keys_before_dictionary_collapse(self):
        for wire in (
            "a200f9380000f93c00", "a200f938001800f93c00",
            "bf00f9380000f93c00ff", "a208010802", "bf0801180802ff",
        ):
            with self.subTest(wire=wire):
                self.reject(wp(bytes.fromhex(wire)))
        # A duplicate producer key is also rejected.
        self.reject(wp(wp(bytes.fromhex("a0"))))

    def test_top_map_and_keys_require_untagged_uint(self):
        for wire in ("d9d9f7a0", "80", "40", "f6"):
            self.reject(bytes.fromhex(wire))
        for key in ("f4", "f5", "20", "f90000", "c24100", "d9d9f700", "60"):
            with self.subTest(key=key):
                self.reject(wp(bytes.fromhex("a1" + key + "f93800")))

    def test_known_uint_fields_reject_semantically_coerced_values(self):
        invalid = ("f4", "f5", "20", "f90000", "c24101", "d9d9f700",
                   "c249010000000000000000", "40", "60", "80", "a0", "f6")
        for key in (2, 4, 5, 7, 8):
            for value in invalid:
                with self.subTest(key=key, value=value):
                    wire = field_wire(key, bytes.fromhex(value))
                    if key == 4:  # Supply a creation time to isolate the error.
                        wire = bytes([wire[0] + 1]) + b"\x02\x01" + wire[1:]
                    self.reject(wire)

    def test_probabilities_require_untagged_floats(self):
        for value in ("00", "01", "20", "f4", "f5", "f6", "40", "60",
                      "c24101", "d9d9f7f93800", "80"):
            for wire in probability_wires(bytes.fromhex(value)):
                with self.subTest(wire=wire.hex()):
                    self.reject(wire)

    def test_known_containers_require_raw_wire_types(self):
        for wire in ("a101d9d9f780", "a10181d9d9f782" + NH100.hex() + "f93800",
                     "a101a0", "a1018180", "a10181818202821864",
                     "a101818382028218640000f93800"):
            with self.subTest(wire=wire):
                self.reject(wp(bytes.fromhex(wire)))
        for wire in ("a103d9d9f7" + cbor2.dumps(ROVER).hex(), "a10340", "a10360",
                     "a103a0", "a10380"):
            with self.subTest(wire=wire):
                self.reject(bytes.fromhex(wire))

    def test_uint64_boundaries_and_ipn_encodings(self):
        fqnn = (977000 << 32) | 100
        data = {1: [[[2, [100, 0]], 0.5], [[2, [fqnn, 1]], 0.75],
                    [[2, [cpb.UINT64_MAX, 0]], 1.0],
                    [[1, "//node/service"], 0.25], [[3, {"x": 1}], 0.0]],
                2: cpb.UINT64_MAX, 3: [2, [977000, 200, 0]], 4: cpb.UINT64_MAX,
                5: 255, 7: 1, 8: cpb.UINT64_MAX, cpb.UINT64_MAX: None}
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(data)), data)
        self.assertEqual(fqnn, 0x000EE86800000064)
        self.assertEqual(cpb.node_identity([2, [fqnn, 1]]),
                         cpb.node_identity([2, [977000, 100, 0]]))
        with self.assertRaisesRegex(ValueError, "metric type"):
            cpb.encode_cpb(d(f5=256))
        for key in (2, 4, 5, 7, 8):
            for value in (-1, True, False, 1.0, 1 << 64):
                with self.subTest(key=key, value=value):
                    invalid = d(f2=1)
                    invalid[key] = value
                    with self.assertRaises(ValueError):
                        cpb.encode_cpb(invalid)
        for key in (-1, True, False, 1.0, 1 << 64):
            with self.assertRaises(ValueError):
                cpb.encode_cpb({3: ROVER, key: None})

    def test_version_handling_and_validity_requires_creation_time(self):
        with self.assertRaises(cpb.UnsupportedVersionError):
            cpb.decode_cpb(cpb.encode_cpb(d(f7=1)).replace(b"\x07\x01", b"\x07\x02"))
        # A higher version is refused before version-1 field typing applies.
        with self.assertRaises(cpb.UnsupportedVersionError):
            cpb.decode_cpb(bytes.fromhex("a2034568656c6c6f0702"))
        with self.assertRaises(cpb.UnsupportedVersionError):
            cpb.encode_cpb(d(f7=2))
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(d(f7=1))), d(f7=1))
        for bad in (d(f4=1), d(f2=0, f4=1)):
            with self.assertRaisesRegex(ValueError, "requires"):
                cpb.encode_cpb(bad)
        with self.assertRaisesRegex(ValueError, "requires"):
            cpb.decode_cpb(wp(bytes.fromhex("a10401")))
        with self.assertRaisesRegex(ValueError, "requires"):
            cpb.decode_cpb(wp(bytes.fromhex("a202000400")))
        self.assertEqual(cpb.decode_cpb(wp(bytes.fromhex("a202010400"))), d(f2=1, f4=0))

    def test_duplicate_next_hop_node_identities(self):
        fqnn = (977000 << 32) | 100
        pairs = (([2, [100, 0]], [2, [100, 1]]),          # service ignored
                 ([2, [fqnn, 0]], [2, [977000, 100, 5]]),  # 2- vs 3-element form
                 ([2, [100, 0]], [2, [0, 100, 0]]),       # default allocator 0
                 ([1, "//node/a"], [1, "//node/b"]))
        for first, second in pairs:
            data = d(f1=[[first, 0.5], [second, 0.75]])
            with self.subTest(first=first, second=second):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    cpb.encode_cpb(data)
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    cpb.decode_cpb(cbor2.dumps(data))

    def test_trailing_bytes_at_each_embedding_layer(self):
        base = wp(b"\xa0")
        for tail in (b"\x00", b"\xa0", b"\xff"):
            self.reject(base + tail)
            with self.assertRaises(ValueError):
                cpb.decode_btsd(cbor2.dumps(base) + tail)
            with self.assertRaises(ValueError):
                cpb.decode_btsd(cbor2.dumps(base + tail))
        for wire in (base, b"\xd9\xd9\xf7" + cbor2.dumps(base)):
            with self.assertRaises(ValueError):
                cpb.decode_btsd(wire)

    def test_all_truncated_prefixes_rejected(self):
        data = {0: 0.75, 1: [[[2, [(977000 << 32) | 100, 0]], 0.5]], 2: 100,
                3: ROVER, 4: 3600, 5: 1, 6: 0.5, 7: 1, 8: 0,
                9: cbor2.CBORTag(60000, {"nested": [1, b"text"]})}
        for wire, decoder in ((cpb.encode_cpb(data), cpb.decode_cpb),
                              (cpb.encode_btsd(data), cpb.decode_btsd)):
            for end in range(len(wire)):
                with self.subTest(end=end, decoder=decoder.__name__):
                    with self.assertRaises((ValueError, cbor2.CBORDecodeError)):
                        decoder(wire[:end])

    def test_indefinite_receive_containers_and_strings(self):
        wire = bytes.fromhex("bf00f93800019f9f9f029f1864ffffff"
                             "f93c00ffffff")
        expected = d(f0=0.5, f1=[[[2, [100]], 1.0]])
        # The ipn SSP above has one element, so it must be rejected ...
        self.reject(wp(wire))
        # ... while a well-formed indefinite-length encoding is accepted.
        wire = bytes.fromhex("bf00f93800019f9f9f029f186400ffff"
                             "f93c00ffffff")
        expected = d(f0=0.5, f1=[[[2, [100, 0]], 1.0]])
        self.assertEqual(cpb.decode_cpb(wp(wire)), expected)
        whole = wp(wire)
        outer = b"\x5f" + cbor2.dumps(whole[:5]) + cbor2.dumps(whole[5:]) + b"\xff"
        self.assertEqual(cpb.decode_btsd(outer), expected)
        text_wire = b"\xa1\x01\x81\x82\x82\x01\x7f" + cbor2.dumps("//no")
        text_wire += cbor2.dumps("de/x") + b"\xff\xf9\x38\x00"
        self.assertEqual(cpb.decode_cpb(wp(text_wire)), d(f1=[[[1, "//node/x"], 0.5]]))

    def test_malformed_cbor_rejected(self):
        for wire in ("a109ff", "bf09ff", "a1091f", "a1093f", "a109df00",
                     "a109f800", "a109fc", "a1095f6161ff", "a1097f4161ff",
                     "a1095f5fffff", "a1099fff00", "a109bf00ff"):
            with self.subTest(wire=wire):
                self.reject(wp(bytes.fromhex(wire)))

    def test_all_float_widths_reject_oor_nonfinite_and_flush(self):
        values = (-2.0, -0.0, 0.0, 2.0 ** -24, 2.0 ** -15,
                  2.0 ** -14, 0.5, 1.0, 2.0, math.inf, -math.inf, math.nan)
        for prefix, fmt in ((b"\xf9", ">e"), (b"\xfa", ">f"), (b"\xfb", ">d")):
            for value in values:
                for key, wire in zip(("f0", "f6", "f1"),
                                     probability_wires(prefix + struct.pack(fmt, value))):
                    with self.subTest(width=fmt, value=value, wire=wire.hex()):
                        if (not math.isfinite(value)) or value < 0.0 or value > 1.0:
                            self.reject(wire)
                            continue
                        expected = value
                        if 0.0 < expected < cpb.MIN_NORMAL_BINARY16:
                            expected = 0.0
                        result = cpb.decode_cpb(wire)
                        actual = (result[1][0][1] if key == "f1"
                                  else result[int(key[1:])])
                        self.assertEqual(actual, expected)
        for fmt, prefix in ((">f", b"\xfa"), (">d", b"\xfb")):
            self.assertEqual(cpb.decode_cpb(field_wire(0, prefix + struct.pack(fmt, 0.1)))[0],
                             struct.unpack(fmt, struct.pack(fmt, 0.1))[0])

    def test_exhaustive_binary16_receive_policy(self):
        for bits in range(1 << 16):
            packed = bits.to_bytes(2, "big")
            value = struct.unpack(">e", packed)[0]
            wire = wp(b"\xa1\x00\xf9" + packed)
            if (not math.isfinite(value)) or value < 0.0 or value > 1.0:
                with self.assertRaises(ValueError, msg=f"binary16 0x{bits:04x}"):
                    cpb.decode_cpb(wire)
            else:
                expected = value
                if 0.0 < expected < 2.0 ** -14:
                    expected = 0.0
                self.assertEqual(cpb.decode_cpb(wire)[0], expected, f"binary16 0x{bits:04x}")

    def test_encoder_float_policy_and_api_numeric_convenience(self):
        for value in (0, 1, 0.0, 0.5, 1.0):
            wire = cpb.encode_cpb(d(f0=value))
            self.assertEqual(wire[2], 0xf9)
            self.assertEqual(cpb.decode_cpb(wire)[0], float(value))
        for value in (True, False, "0.5"):
            with self.assertRaises(TypeError):
                cpb.encode_cpb(d(f0=value))
        for value in (-1, 2, math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                cpb.encode_cpb(d(f0=value))
        self.assertEqual(cpb._encode_prob_float16(2.0 ** -15), bytes.fromhex("f90000"))
        self.assertEqual(cpb._encode_prob_float16(2.0 ** -14), bytes.fromhex("f90400"))
        with self.assertRaises(ValueError):
            cpb._encode_prob_float16(2.0 ** -15, strict=True)
        with self.assertRaises(ValueError):
            cpb._encode_prob_float16(0.95, strict=True)

    def test_unknown_keys_are_retained_without_meaning(self):
        values = [None, True, False, -1, 1 << 80, b"opaque", "text",
                  [1, {"nested": 2}], {24: 0, -1: 0}, math.inf,
                  cbor2.CBORTag(60000, ["tagged", {24: 0, -1: 0}]),
                  cbor2.CBORSimpleValue(32), cbor2.undefined]
        for value in values:
            with self.subTest(value=value):
                wire = cpb.encode_cpb(d(f9=value))
                self.assertEqual(cpb.decode_cpb(wire), cbor2.loads(wire))
                self.assertEqual(cpb.encode_cpb(cpb.decode_cpb(wire)), wire)
        self.assertTrue(math.isnan(cpb.decode_cpb(wp(bytes.fromhex("a109f97e00")))[9]))

    def test_unknown_shared_references_remain_valid_across_fields(self):
        result = cpb.decode_cpb(wp(bytes.fromhex("a209d81c81010ad81d00")))
        self.assertEqual(result, d(f9=[1], f10=[1]))
        self.assertIs(result[9], result[10])
        cyclic = cpb.decode_cpb(wp(bytes.fromhex("a109d81c81d81d00")))[9]
        self.assertIs(cyclic[0], cyclic)

    def test_unknown_nested_maps_use_core_deterministic_order(self):
        # Bytewise order places 0x1818 before 0x20; length-first reverses it.
        producer = cbor2.dumps(ROVER).hex()
        self.assertEqual(cpb.encode_cpb(d(f9={24: 0, -1: 0})).hex(),
                         "a203" + producer + "09a21818002000")
        nested = d(f9=[{24: 0, -1: 0}, cbor2.CBORTag(60000, {24: 0, -1: 0})])
        self.assertEqual(cpb.encode_cpb(nested).hex(),
                         "a203" + producer + "0982a21818002000d9ea60a21818002000")

    def test_large_path_array_uses_full_cbor_length_range(self):
        data = d(f1=[[[2, [index + 1, 0]], 0.5] for index in range(256)])
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(data)), data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
