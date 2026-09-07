"""Wire-level CPB regressions, including all 65,536 binary16 bit patterns.

Run with ``python3 impl/test_cpb_validation.py`` from the repository root.
These vectors deliberately bypass encode_cpb when constructing malformed
inputs: a Python dict cannot represent duplicate CBOR map keys.
"""

import math
import struct
import unittest

import cbor2
import cpb


def field_wire(key, value_wire):
    return b"\xa1" + cbor2.dumps(key) + value_wire


def probability_wires(value_wire):
    return (field_wire(0, value_wire), field_wire(6, value_wire),
            b"\xa1\x01\x81\x82\x18\x64" + value_wire)


class CPBValidationTests(unittest.TestCase):
    def reject(self, wire):
        with self.assertRaises((ValueError, cbor2.CBORDecodeError)):
            cpb.decode_cpb(wire)

    def test_duplicate_keys_before_dictionary_collapse(self):
        for wire in (
            "a200f9380000f93c00", "a200f938001800f93c00",
            "bf00f9380000f93c00ff", "a208010802", "bf0801180802ff",
        ):
            with self.subTest(wire=wire):
                self.reject(bytes.fromhex(wire))

    def test_top_map_and_keys_require_untagged_uint(self):
        for wire in ("d9d9f7a0", "80", "40", "f6"):
            self.reject(bytes.fromhex(wire))
        for key in ("f4", "f5", "20", "f90000", "c24100", "d9d9f700", "60"):
            with self.subTest(key=key):
                self.reject(bytes.fromhex("a1" + key + "f93800"))

    def test_known_uint_fields_reject_semantically_coerced_values(self):
        invalid = ("f4", "f5", "20", "f90000", "c24101", "d9d9f700",
                   "c249010000000000000000", "40", "60", "80", "a0", "f6")
        for key in (2, 4, 5, 7):
            for value in invalid:
                with self.subTest(key=key, value=value):
                    wire = field_wire(key, bytes.fromhex(value))
                    if key == 4:  # Supply timestamp to isolate the wire-type error.
                        wire = b"\xa2\x02\x00" + wire[1:]
                    self.reject(wire)

    def test_probabilities_require_untagged_floats(self):
        for value in ("00", "01", "20", "f4", "f5", "f6", "40", "60",
                      "c24101", "d9d9f7f93800", "80"):
            for wire in probability_wires(bytes.fromhex(value)):
                with self.subTest(wire=wire.hex()):
                    self.reject(wire)

    def test_known_containers_and_source_require_raw_wire_types(self):
        for wire in ("a101d9d9f780", "a10181d9d9f7821864f93800",
                     "a103d9d9f740", "a10360", "a101a0", "a1018180",
                     "a10181811864", "a10181831864f9380000"):
            with self.subTest(wire=wire):
                self.reject(bytes.fromhex(wire))

    def test_next_hop_requires_uint_or_non_ipn_text(self):
        for next_hop in (b"dtn://node", True, False, -1, 1.0, None, [], {},
                         "ipn:100.0", "IPN:0.100.0", "100", "dtn:",
                         "1bad:node", "dtn://bad node", "dtn://bad\x00node",
                         cpb.IPN_LOCAL_NODE, 1 << 64):
            with self.subTest(next_hop=next_hop):
                self.reject(cbor2.dumps({1: [[next_hop, 0.5]]}))
                with self.assertRaises((TypeError, ValueError)):
                    cpb.encode_cpb({1: [[next_hop, 0.5]]})
        for wire in ("d9d9f71864", "c24164", "f90000"):
            self.reject(b"\xa1\x01\x81\x82" + bytes.fromhex(wire) + b"\xf9\x38\x00")

    def test_uint64_and_fqnn_boundaries(self):
        fqnn = (977000 << 32) | 100
        data = {1: [[100, 0.5], [fqnn, 0.75], [cpb.UINT64_MAX, 1.0],
                    ["dtn://node/service", 0.25]],
                2: cpb.UINT64_MAX, 3: b"\x00\xff", 4: cpb.UINT64_MAX,
                5: cpb.UINT64_MAX, 7: cpb.UINT64_MAX, cpb.UINT64_MAX: None}
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(data)), data)
        self.assertEqual(fqnn, 0x000EE86800000064)
        for key in (2, 4, 5, 7):
            for value in (-1, True, False, 1.0, 1 << 64):
                with self.subTest(key=key, value=value):
                    invalid = {2: 0, key: value}
                    with self.assertRaises(ValueError):
                        cpb.encode_cpb(invalid)
        for key in (-1, True, False, 1.0, 1 << 64):
            with self.assertRaises(ValueError):
                cpb.encode_cpb({key: None})

    def test_unknown_version_retained_and_validity_requires_timestamp(self):
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb({7: 123})), {7: 123})
        with self.assertRaisesRegex(ValueError, "requires"):
            cpb.encode_cpb({4: 1})
        with self.assertRaisesRegex(ValueError, "requires"):
            cpb.decode_cpb(bytes.fromhex("a10401"))
        self.assertEqual(cpb.decode_cpb(bytes.fromhex("a202000400")), {2: 0, 4: 0})

    def test_duplicate_exact_next_hop_identities(self):
        for next_hop in (100, "dtn://node/service"):
            data = {1: [[next_hop, 0.5], [next_hop, 0.75]]}
            with self.assertRaisesRegex(ValueError, "duplicate"):
                cpb.encode_cpb(data)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                cpb.decode_cpb(cbor2.dumps(data))
        self.reject(bytes.fromhex("a101828200f93800821800f93c00"))

    def test_trailing_bytes_at_each_embedding_layer(self):
        for tail in (b"\x00", b"\xa0", b"\xff"):
            self.reject(b"\xa0" + tail)
            with self.assertRaises(ValueError):
                cpb.decode_btsd(cbor2.dumps(b"\xa0") + tail)
            with self.assertRaises(ValueError):
                cpb.decode_btsd(cbor2.dumps(b"\xa0" + tail))
        for wire in (b"\xa0", bytes.fromhex("d9d9f741a0")):
            with self.assertRaises(ValueError):
                cpb.decode_btsd(wire)

    def test_all_truncated_prefixes_rejected(self):
        data = {0: 0.75, 1: [[(977000 << 32) | 100, 0.5]], 2: 100,
                3: b"producer", 4: 3600, 5: 1, 6: 0.5, 7: 1,
                8: cbor2.CBORTag(60000, {"nested": [1, b"text"]})}
        for wire, decoder in ((cpb.encode_cpb(data), cpb.decode_cpb),
                              (cpb.encode_btsd(data), cpb.decode_btsd)):
            for end in range(len(wire)):
                with self.subTest(end=end, decoder=decoder.__name__):
                    with self.assertRaises((ValueError, cbor2.CBORDecodeError)):
                        decoder(wire[:end])

    def test_indefinite_receive_containers_and_strings(self):
        wire = bytes.fromhex("bf00f93800019f9f1864f93c00ffff"
                             "035f41614162ffff")
        expected = {0: 0.5, 1: [[100, 1.0]], 3: b"ab"}
        self.assertEqual(cpb.decode_cpb(wire), expected)
        outer = b"\x5f" + cbor2.dumps(wire[:5]) + cbor2.dumps(wire[5:]) + b"\xff"
        self.assertEqual(cpb.decode_btsd(outer), expected)
        text_wire = b"\xa1\x01\x81\x82\x7f" + cbor2.dumps("dtn:")
        text_wire += cbor2.dumps("//node") + b"\xff\xf9\x38\x00"
        self.assertEqual(cpb.decode_cpb(text_wire), {1: [["dtn://node", 0.5]]})

    def test_malformed_cbor_rejected(self):
        for wire in ("a108ff", "bf08ff", "a1081f", "a1083f", "a108df00",
                     "a108f800", "a108fc", "a1085f6161ff", "a1087f4161ff",
                     "a1085f5fffff", "a1089fff00", "a108bf00ff"):
            with self.subTest(wire=wire):
                self.reject(bytes.fromhex(wire))

    def test_all_float_widths_clamp_reject_nonfinite_and_flush(self):
        values = (-2.0, -0.0, 0.0, 2.0 ** -24, 2.0 ** -15,
                  2.0 ** -14, 0.5, 1.0, 2.0, math.inf, -math.inf, math.nan)
        for prefix, fmt in ((b"\xf9", ">e"), (b"\xfa", ">f"), (b"\xfb", ">d")):
            for value in values:
                for wire in probability_wires(prefix + struct.pack(fmt, value)):
                    with self.subTest(width=fmt, value=value, wire=wire.hex()):
                        if not math.isfinite(value):
                            self.reject(wire)
                            continue
                        expected = min(1.0, max(0.0, value))
                        if 0.0 < expected < cpb.MIN_NORMAL_BINARY16:
                            expected = 0.0
                        result = cpb.decode_cpb(wire)
                        actual = result[1][0][1] if 1 in result else next(iter(result.values()))
                        self.assertEqual(actual, expected)
        for fmt, prefix in ((">f", b"\xfa"), (">d", b"\xfb")):
            self.assertEqual(cpb.decode_cpb(field_wire(0, prefix + struct.pack(fmt, 0.1)))[0],
                             struct.unpack(fmt, struct.pack(fmt, 0.1))[0])

    def test_exhaustive_binary16_receive_policy(self):
        for bits in range(1 << 16):
            packed = bits.to_bytes(2, "big")
            value = struct.unpack(">e", packed)[0]
            wire = b"\xa1\x00\xf9" + packed
            if not math.isfinite(value):
                with self.assertRaises(ValueError, msg=f"binary16 0x{bits:04x}"):
                    cpb.decode_cpb(wire)
            else:
                expected = min(1.0, max(0.0, value))
                if 0.0 < expected < 2.0 ** -14:
                    expected = 0.0
                self.assertEqual(cpb.decode_cpb(wire)[0], expected, f"binary16 0x{bits:04x}")

    def test_encoder_float_policy_and_api_numeric_convenience(self):
        for value in (0, 1, 0.0, 0.5, 1.0):
            wire = cpb.encode_cpb({0: value})
            self.assertEqual(wire[2], 0xf9)
            self.assertEqual(cpb.decode_cpb(wire)[0], float(value))
        for value in (True, False, "0.5"):
            with self.assertRaises(TypeError):
                cpb.encode_cpb({0: value})
        for value in (-1, 2, math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                cpb.encode_cpb({0: value})
        self.assertEqual(cpb._encode_prob_float16(2.0 ** -15), bytes.fromhex("f90000"))
        self.assertEqual(cpb._encode_prob_float16(2.0 ** -14), bytes.fromhex("f90400"))
        with self.assertRaises(ValueError):
            cpb._encode_prob_float16(2.0 ** -15, strict=True)
        with self.assertRaises(ValueError):
            cpb._encode_prob_float16(0.95, strict=True)

    def test_unknown_values_preserve_forward_compatibility(self):
        values = [None, True, False, -1, 1 << 80, b"opaque", "text",
                  [1, {"nested": 2}], {24: 0, -1: 0}, math.inf,
                  cbor2.CBORTag(60000, ["tagged", {24: 0, -1: 0}]),
                  cbor2.CBORSimpleValue(32), cbor2.undefined]
        for value in values:
            with self.subTest(value=value):
                wire = cpb.encode_cpb({8: value})
                self.assertEqual(cpb.decode_cpb(wire), cbor2.loads(wire))
                self.assertEqual(cpb.encode_cpb(cpb.decode_cpb(wire)), wire)
        self.assertTrue(math.isnan(cpb.decode_cpb(bytes.fromhex("a108f97e00"))[8]))

    def test_unknown_shared_references_remain_valid_across_fields(self):
        result = cpb.decode_cpb(bytes.fromhex("a208d81c810109d81d00"))
        self.assertEqual(result, {8: [1], 9: [1]})
        self.assertIs(result[8], result[9])
        cyclic = cpb.decode_cpb(bytes.fromhex("a108d81c81d81d00"))[8]
        self.assertIs(cyclic[0], cyclic)

    def test_unknown_nested_maps_use_core_deterministic_order(self):
        # Bytewise order places 0x1818 before 0x20; length-first reverses it.
        self.assertEqual(cpb.encode_cpb({8: {24: 0, -1: 0}}).hex(), "a108a21818002000")
        nested = {8: [{24: 0, -1: 0}, cbor2.CBORTag(60000, {24: 0, -1: 0})]}
        self.assertEqual(cpb.encode_cpb(nested).hex(),
                         "a10882a21818002000d9ea60a21818002000")

    def test_large_path_array_uses_full_cbor_length_range(self):
        data = {1: [[index, 0.5] for index in range(256)]}
        self.assertEqual(cpb.decode_cpb(cpb.encode_cpb(data)), data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
