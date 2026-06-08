"""
Minimal BPv7 bundle creation and parsing with CPB support.
Supports attaching the Contact Probability Block as an extension block.

This is a proof-of-concept assembler, not a full production BP library.
It produces bundles that ION can (in principle) handle when injected properly.

CUDA acceleration (via Numba) is available for batch generation of many test packets.
"""

import time
import struct
from typing import Optional, List, Tuple

try:
    import cbor2
except ImportError:
    print("ERROR: cbor2 is required. pip install cbor2")
    raise

# Try to import the real reference CPB implementation
import sys
import os
CPB_PATHS = [
    "/home/nick/draft-perry-dtn-cpb/impl",
    "/home/nick/orin-dtn-setup/cpb-impl",
    os.path.dirname(__file__),
]
for p in CPB_PATHS:
    if os.path.exists(os.path.join(p, "cpb.py")):
        sys.path.insert(0, p)
        break

try:
    import cpb as cpb_module
except ImportError:
    cpb_module = None
    print("WARNING: Real cpb.py not found. Using minimal stub.")


# --- Minimal BPv7 Bundle Assembler ---

BP_VERSION = 7
BUNDLE_FLAG_FRAGMENT = 0x01
BUNDLE_FLAG_ADMIN = 0x02
BUNDLE_FLAG_NOFRAG = 0x04
BUNDLE_FLAG_CUSTODY = 0x08
BUNDLE_FLAG_DEST_SINGLETON = 0x10
BUNDLE_FLAG_APP_ACK = 0x20

BLOCK_FLAG_REPLICATE = 0x01
BLOCK_FLAG_REPORT = 0x02
BLOCK_FLAG_DELETE = 0x04
BLOCK_FLAG_LAST = 0x08
BLOCK_FLAG_DISCARD = 0x10
BLOCK_FLAG_NOTPROC = 0x20
BLOCK_FLAG_EID_REF = 0x40

# Standard block types
BLOCK_TYPE_PAYLOAD = 1
BLOCK_TYPE_PREVIOUS_NODE = 6
BLOCK_TYPE_BUNDLE_AGE = 7
BLOCK_TYPE_HOP_COUNT = 10

# Our CPB block type (use experimental range until IANA assignment)
CPB_BLOCK_TYPE = 200  # As used in the draft examples


def _encode_eid(node: int, service: int = 1) -> bytes:
    """Encode a simple ipn EID as CBOR."""
    # ipn scheme: [scheme, [allocator, node, service]]
    # For simplicity we use the common 2-element form for ipn:node.service
    return cbor2.dumps([1, [node, service]])  # scheme 1 = ipn (simplified)


def create_bundle_with_cpb(
    src_node: int,
    dst_node: int,
    payload: bytes = b"CPB test payload",
    cpb_data: Optional[dict] = None,
    timestamp: Optional[int] = None,
) -> bytes:
    """
    Create a minimal valid BPv7 bundle containing a CPB extension block.
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Primary block (simplified)
    primary = [
        BP_VERSION,
        0,  # flags
        0,  # CRC type
        _encode_eid(src_node),           # source
        _encode_eid(dst_node),           # destination
        _encode_eid(src_node),           # report-to
        [timestamp, 0],                  # creation timestamp + seq
        3600,                            # lifetime
    ]
    primary_bytes = cbor2.dumps(primary)

    # Build extension blocks
    blocks = []

    # Previous Node block (optional but common)
    prev_node = [BLOCK_TYPE_PREVIOUS_NODE, 0, _encode_eid(src_node)]
    blocks.append(cbor2.dumps(prev_node))

    # Hop Count block
    hop_count = [BLOCK_TYPE_HOP_COUNT, 0, [0, 32]]
    blocks.append(cbor2.dumps(hop_count))

    # === CPB Extension Block ===
    if cpb_data is None and cpb_module is not None:
        # Generate a sensible default CPB
        cpb_data = {
            cpb_module.F_DEFAULT_PROB: 0.85,
            cpb_module.F_PATH_ENTRIES: [[dst_node, 0.85]],
            cpb_module.F_TIMESTAMP: timestamp,
            cpb_module.F_VALIDITY: 3600,
            cpb_module.F_METRIC_TYPE: 1,  # CGR confidence
            cpb_module.F_CONFIDENCE: 0.70,
        }

    if cpb_data is not None and cpb_module is not None:
        cpb_btsd = cpb_module.encode_btsd(cpb_data)
        cpb_block = [
            CPB_BLOCK_TYPE,
            0,  # block number
            BLOCK_FLAG_REPLICATE | BLOCK_FLAG_DISCARD,  # flags
            0,  # CRC
            cpb_btsd,
        ]
        blocks.append(cbor2.dumps(cpb_block))

    # Payload block (last)
    payload_block = [BLOCK_TYPE_PAYLOAD, 0, 0, payload]
    blocks.append(cbor2.dumps(payload_block))

    # Assemble full bundle
    bundle = primary_bytes
    for b in blocks:
        bundle += b

    return bundle


# --- CUDA / Numba Accelerated Batch Generation ---

def has_cuda():
    try:
        import numba.cuda
        return numba.cuda.is_available()
    except Exception:
        return False


def generate_many_test_packets(num_packets: int, src: int, dst: int, use_gpu: bool = True):
    """
    Generate many test bundles quickly.
    Uses Numba CUDA on GPU if available and requested.
    """
    packets = []
    base_prob = 0.70

    if use_gpu and has_cuda():
        try:
            import numpy as np
            from numba import cuda
            import math

            @cuda.jit
            def _gen_probs(out, base, n):
                i = cuda.grid(1)
                if i < n:
                    # Simple varying probability
                    out[i] = base + 0.1 * math.sin(i * 0.1)

            d_out = cuda.device_array(num_packets, dtype=np.float32)
            threads = 256
            blocks = (num_packets + threads - 1) // threads
            _gen_probs[blocks, threads](d_out, base_prob, num_packets)
            probs = d_out.copy_to_host()

            for i, p in enumerate(probs):
                cpb_data = {
                    "default_prob": float(p),
                    "path": [[dst, float(p)]],
                    "ts": int(time.time()) + i,
                    "valid": 3600,
                    "metric": 1,
                }
                pkt = create_bundle_with_cpb(src, dst, f"test packet {i}".encode(), cpb_data)
                packets.append(pkt)
            print(f"Generated {num_packets} packets using CUDA")
            return packets
        except Exception as e:
            print(f"CUDA batch generation failed ({e}), falling back to CPU")

    # CPU fallback
    for i in range(num_packets):
        p = base_prob + 0.05 * (i % 5 - 2)
        cpb_data = {
            "default_prob": round(p, 3),
            "path": [[dst, round(p, 3)]],
            "ts": int(time.time()) + i,
            "valid": 3600,
            "metric": 1,
        }
        pkt = create_bundle_with_cpb(src, dst, f"test packet {i}".encode(), cpb_data)
        packets.append(pkt)

    return packets


if __name__ == "__main__":
    print("CUDA available:" , has_cuda())
    pkts = generate_many_test_packets(4, 268485122, 268485121, use_gpu=True)
    print(f"Generated {len(pkts)} test packets")
    print("First packet length:", len(pkts[0]))
