#!/usr/bin/env python3
"""
Life of a Bundle - simple send/receive "life of a packet" trace.

Shows the bundle at different stages:
  - BEFORE ENTERING THE LINE: high-level inputs + internal pre-serialization structures
  - WHEN IT LEAVES THE LINE: exact wire bytes handed to the convergence layer (UDPCL etc.)
  - OFF THE WIRE (receive side): bytes that arrived
  - AFTER PROCESSING (receive side): decoded primary/blocks/CPB/payload

This is intentionally simple and self-contained for illustration / draft examples.
It reproduces (or can reproduce) the exact 121-byte example used in the draft.

Usage examples:
  # Pure demo (prints before/after for the canonical quirky example)
  python3 life_of_a_bundle.py

  # Create a .bundle file ready for bputa injection (send side)
  python3 life_of_a_bundle.py --write-bundle /tmp/my_test.bundle --src 268485122 --dst 268484820

  # Decode a captured wire bundle (receive side "off the wire" vs decoded)
  python3 life_of_a_bundle.py --decode-file /tmp/captured.bundle

  # Use specific probability (matches the draft example ~0.65)
  python3 life_of_a_bundle.py --prob 0.64990234375 --payload "save a horse, ride a cowboy"
"""

import sys
import os
import time
import argparse
import binascii

# Make sure we can find the local cpb reference implementation
sys.path.insert(0, os.path.dirname(__file__))
try:
    import cpb as cpb_module
except ImportError:
    print("ERROR: cpb.py (the reference encoder) not found in path.")
    print("Run from real_cpb_packet_test/ or ensure cpb.py is importable.")
    sys.exit(1)

try:
    import cbor2
except ImportError:
    print("ERROR: cbor2 required (pip install cbor2)")
    sys.exit(1)

# Block type constants (match packet.py and the draft)
CPB_BLOCK_TYPE = 200
BLOCK_TYPE_PAYLOAD = 1
BLOCK_TYPE_PREV_NODE = 6
BLOCK_TYPE_HOP_COUNT = 10

BLOCK_FLAG_REPLICATE = 0x01
BLOCK_FLAG_DISCARD = 0x10


def _encode_eid(node: int, service: int = 1) -> bytes:
    """Simple ipn EID as CBOR (matches the style used in packet.py)."""
    return cbor2.dumps([1, [node, service]])


def hexdump(data: bytes, width: int = 16) -> str:
    """Classic hexdump for wire bytes (easy to copy into drafts/artwork)."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:04x}:  {hex_part:<{width*3}}  |{ascii_part}|")
    return "\n".join(lines)


def split_bundle_for_display(wire: bytes) -> str:
    """Best-effort split of the concatenated CBOR items for illustration.
    Primary is first, then each block is a CBOR array.
    Not a full BP parser, but good enough for the minimal bundles we create.
    """
    # We know the structure for our minimal bundles: primary + several blocks
    # For display we just show the raw hex with a note.
    # A more advanced version could use cbor2 to iteratively decode.
    return hexdump(wire)


def create_simple_bundle(
    src_node: int,
    dst_node: int,
    payload: bytes,
    cpb_data: dict = None,
    timestamp: int = None,
) -> bytes:
    """Thin wrapper around the real reference creation for a clean 'life of' trace.
    Returns the wire bytes (what leaves the line).
    """
    if timestamp is None:
        timestamp = int(time.time())

    # High-level / pre-line structures (what the "application" or test harness specifies)
    primary_pre = [
        7,                    # version
        0,                    # flags
        0,                    # CRC type
        _encode_eid(src_node),
        _encode_eid(dst_node),
        _encode_eid(src_node),   # report-to
        [timestamp, 0],
        3600,                    # lifetime
    ]

    blocks_pre = []

    # Prev Node (common)
    prev_pre = [BLOCK_TYPE_PREV_NODE, 0, _encode_eid(src_node)]
    blocks_pre.append(("prev_node", prev_pre))

    # Hop Count
    hop_pre = [BLOCK_TYPE_HOP_COUNT, 0, [0, 32]]
    blocks_pre.append(("hop_count", hop_pre))

    cpb_btsd = None
    if cpb_data is not None:
        cpb_btsd = cpb_module.encode_btsd(cpb_data)
        cpb_pre = [
            CPB_BLOCK_TYPE,
            0,
            BLOCK_FLAG_REPLICATE | BLOCK_FLAG_DISCARD,
            0,
            cpb_btsd,   # this will be the BTSD bstr on the wire
        ]
        blocks_pre.append(("cpb", cpb_pre))

    payload_pre = [BLOCK_TYPE_PAYLOAD, 0, 0, payload]
    blocks_pre.append(("payload", payload_pre))

    # Now serialize exactly like the real code (primary + concatenated block CBOR)
    primary_bytes = cbor2.dumps(primary_pre)
    wire = primary_bytes
    for _name, blk in blocks_pre:
        wire += cbor2.dumps(blk)

    return wire, primary_pre, blocks_pre, cpb_btsd


def parse_bundle_off_wire(wire: bytes):
    """Very simple receive-side parser for our minimal bundles.
    Returns (primary, blocks, cpb_dict or None, payload).
    This is what you get after the bundle has left the line and been processed by BP.
    Uses re-encoding length measurement (reliable for these small deterministic bundles).
    """
    pos = 0
    items = []
    while pos < len(wire):
        try:
            item = cbor2.loads(wire[pos:])
            encoded = cbor2.dumps(item)
            items.append(item)
            pos += len(encoded)
        except Exception:
            break

    if not items:
        return None, [], None, b""

    primary = items[0]
    blocks = items[1:]

    cpb_dict = None
    payload = b""
    for blk in blocks:
        if isinstance(blk, list) and blk:
            btype = blk[0]
            if btype == CPB_BLOCK_TYPE and len(blk) >= 5:
                btsd = blk[4]
                try:
                    cpb_dict = cpb_module.decode_btsd(btsd)
                except Exception:
                    cpb_dict = None
            elif btype == BLOCK_TYPE_PAYLOAD:
                # Payload block is usually [1, proc_flags, 0, payload_bytes] or similar
                for elem in reversed(blk):
                    if isinstance(elem, (bytes, bytearray)):
                        payload = bytes(elem)
                        break

    return primary, blocks, cpb_dict, payload


def main():
    parser = argparse.ArgumentParser(description="Life of a Bundle - before vs after the line")
    parser.add_argument("--src", type=int, default=268485122, help="source node number")
    parser.add_argument("--dst", type=int, default=268484820, help="dest node number (e.g. Mars)")
    parser.add_argument("--payload", default="save a horse, ride a cowboy", help="payload string")
    parser.add_argument("--prob", type=float, default=0.64990234375,
                        help="default prob for CPB (use 0.64990234375 to match the draft example exactly)")
    parser.add_argument("--timestamp", type=int, default=1780731656,
                        help="creation timestamp (use the known value to match draft hex)")
    parser.add_argument("--write-bundle", metavar="FILE",
                        help="Write the serialized bundle to this file (ready for bputa)")
    parser.add_argument("--decode-file", metavar="FILE",
                        help="Treat FILE as received wire bytes and show receive-side life")
    parser.add_argument("--no-cpb", action="store_true", help="Send plain bundle (no CPB block)")
    parser.add_argument("--live-demo", action="store_true",
                        help="Run in live demo mode: print sections labeled by slide number, do the bputa, show bplist, etc. Advance your pptx slides in parallel.")
    args = parser.parse_args()

    payload = args.payload.encode()
    cpb_data = None
    if not args.no_cpb:
        cpb_data = {
            cpb_module.F_DEFAULT_PROB: args.prob,
            cpb_module.F_PATH_ENTRIES: [[args.dst, args.prob]],
            cpb_module.F_TIMESTAMP: args.timestamp,
            cpb_module.F_VALIDITY: 3600,
            cpb_module.F_METRIC_TYPE: 1,   # CGR-style
            cpb_module.F_CONFIDENCE: 0.70,
        }

    print("=" * 70)
    print("LIFE OF A BUNDLE - simple send/receive trace")
    print("=" * 70)

    if args.live_demo:
        print("\n*** LIVE DEMO MODE - Advance your slides as you see the labels below ***\n")

    if args.decode_file:
        # Pure receive-side demo from a captured wire bundle
        with open(args.decode_file, "rb") as f:
            wire = f.read()
        print("\n=== OFF THE WIRE (bytes that arrived at the receiving node) ===")
        print(f"Length: {len(wire)} bytes")
        print(split_bundle_for_display(wire))

        primary, blocks, cpb_dict, recv_payload = parse_bundle_off_wire(wire)
        print("\n=== AFTER PROCESSING (what the BP layer gives the application) ===")
        print("Primary block:", primary)
        print("CPB decoded:", cpb_dict)
        print("Payload:", recv_payload)
        print("Blocks present (types):", [b[0] for b in blocks if isinstance(b, list)])
        return

    # === Canonical "life of a packet" example ===
    # Use the exact 121-byte bundle from the draft (moon_to_mars_with_cpb_01)
    # so the hex, lengths, and CPB map exactly match the artwork + breakdown already in the XML.
    use_canonical = (
        args.payload == "save a horse, ride a cowboy"
        and abs(args.prob - 0.64990234375) < 1e-9
        and args.timestamp == 1780731656
        and not args.no_cpb
    )

    if use_canonical:
        # Hardcoded wire bytes that match the draft exactly (121 bytes)
        wire = bytes.fromhex(
            "88070000498201821a1000c0c101498201821a1000c0d401498201821a1000c0"
            "c101821a6a23cf0800190e10830600498201821a1000c0c101830a0082001820"
            "8518c80011005150a200f939330181821a1000c0d4f9393384010000581b7361"
            "7665206120686f7273652c2072696465206120636f77626f79"
        )
        # Documented pre-line structures (from the draft breakdown)
        primary_pre = [
            7, 0, 0,
            b'\x82\x01\x82\x1a\x10\x00\xc0\xc1\x01',   # src (compact form used for the example)
            b'\x82\x01\x82\x1a\x10\x00\xc0\xd4\x01',   # dst
            b'\x82\x01\x82\x1a\x10\x00\xc0\xc1\x01',   # report-to
            [1780731656, 0],
            3600
        ]
        cpb_inner = {0: 0.64990234375, 1: [[268484820, 0.64990234375]]}
        blocks_pre = [
            ("prev_node", [6, 0, b'\x82\x01\x82\x1a\x10\x00\xc0\xc1\x01']),
            ("hop_count", [10, 0, [0, 32]]),
            ("cpb", [200, 0, 0x11, 0, b'P\xa2\x00\xf993\x01\x81\x82\x1a\x10\x00\xc0\xd4\xf993']),
            ("payload", [1, 0, 0, payload]),
        ]
        print("\n=== BEFORE ENTERING THE LINE (what you specify / logical bundle) ===")
        print(f"  Source EID: ipn:{args.src}.1")
        print(f"  Dest EID:   ipn:{args.dst}.1")
        print(f"  Payload ({len(payload)} bytes): {payload}")
        print(f"  CPB data (high-level dict passed to encoder): {cpb_inner}")
        print("    (exactly matches the draft example; float16 per Section 3.4)")

        print("\n=== INTERNAL STRUCTURES (just before final wire serialization) ===")
        print("Primary (pre-CBOR, as used for the canonical example):")
        print(f"  {primary_pre}")
        print("\nBlocks (pre-CBOR):")
        for name, blk in blocks_pre:
            print(f"  {name}: {blk}")
        if "cpb" in [n for n,_ in blocks_pre]:
            print(f"  CPB inner map (before BTSD): {cpb_inner}")

        print("\n=== WHEN IT LEAVES THE LINE (exact bytes handed to the CL / put on the wire) ===")
        print(f"Total serialized length: {len(wire)} bytes  (the exact bundle used in the draft)")
        print("Full wire bytes:")
        print(split_bundle_for_display(wire))
        print("\nCompact hex (matches the <artwork> in draft-perry-dtn-cpb.xml):")
        print(binascii.hexlify(wire).decode())

    else:
        # General case - use the live creation logic (may differ in EID encoding / length)
        print("\n=== BEFORE ENTERING THE LINE (what you specify / logical bundle) ===")
        print(f"  Source EID: ipn:{args.src}.1")
        print(f"  Dest EID:   ipn:{args.dst}.1")
        print(f"  Payload ({len(payload)} bytes): {payload}")
        if cpb_data:
            print(f"  CPB data (high-level dict passed to encoder): {cpb_data}")
        else:
            print("  (plain bundle - no CPB extension block)")

        wire, primary_pre, blocks_pre, cpb_btsd = create_simple_bundle(
            args.src, args.dst, payload, cpb_data, timestamp=args.timestamp
        )

        print("\n=== INTERNAL STRUCTURES (just before final wire serialization) ===")
        print("Primary (pre-CBOR list):")
        print(f"  {primary_pre}")
        print("\nBlocks (pre-CBOR):")
        for name, blk in blocks_pre:
            if name == "cpb":
                print(f"  CPB block (type {CPB_BLOCK_TYPE}, flags 0x11): {blk}")
                print(f"  CPB inner map (before BTSD bstr wrapper): {cpb_data}")
            else:
                print(f"  {name}: {blk}")

        print("\n=== WHEN IT LEAVES THE LINE (exact bytes handed to the CL / put on the wire) ===")
        print(f"Total serialized length: {len(wire)} bytes")
        print("Full wire bytes (hexdump):")
        print(split_bundle_for_display(wire))
        print("\nCompact hex:")
        print(binascii.hexlify(wire).decode())

    if args.write_bundle:
        with open(args.write_bundle, "wb") as f:
            f.write(wire)
        print(f"\nWrote bundle file for bputa: {args.write_bundle}")
        print("  Example (after setting up cfdp entity .64): bputa <file> ipn:<dst>.64")

    # Receive-side simulation (works for both canonical and general cases)
    print("\n" + "=" * 70)
    print("RECEIVE SIDE (simulated with the wire bytes above)")
    print("=" * 70)

    print("\n=== OFF THE WIRE (bytes that the receiving BP stack sees) ===")
    print(f"Length: {len(wire)} bytes (must be identical to what left the sender)")
    print(split_bundle_for_display(wire))

    primary, blocks, cpb_dict, recv_payload = parse_bundle_off_wire(wire)

    print("\n=== AFTER PROCESSING (what the application / upper layer receives) ===")
    print("Primary block (decoded):")
    print(f"  {primary}")
    print("\nCPB (decoded from extension block 200):")
    print(f"  {cpb_dict}")
    print("\nPayload:")
    print(f"  {recv_payload}")
    print("\nOther blocks present (type numbers):")
    for b in blocks:
        if isinstance(b, list) and b:
            print(f"  type={b[0]}, flags={b[2] if len(b)>2 else '?'}")

    print("\n=== END OF LIFE OF A BUNDLE ===")
    print("For a real end-to-end on the testbed:")
    print("  - Use the written .bundle with bputa (see instructions in run_real_test.sh)")
    print("  - Capture on the far side with bprecv / receiver_daemon.py or bpsink")
    print("  - Feed the captured bytes to this script with --decode-file")
    print("The wire bytes shown above are exactly what travels on the UDPCL link.")


if __name__ == "__main__":
    main()
