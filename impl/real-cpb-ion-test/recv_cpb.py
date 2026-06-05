#!/usr/bin/env python3
"""
Simple CPB decoder for received bundle files.
Usage: python3 recv_cpb.py <received_bundle_file>
If the received file is the full bundle bytes (e.g. from CFDP receive of a .bundle or bprecvtest dump), this will extract and decode the CPB ext block.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
try:
    import cpb as c
except ImportError:
    print("cpb.py not found in path")
    sys.exit(1)
if len(sys.argv) < 2:
    print("Usage: python3 recv_cpb.py <bundle_file>")
    sys.exit(1)
path = sys.argv[1]
data = open(path, "rb").read()
print(f"Scanning {path} ({len(data)} bytes) for CPB...")
found = False
for i in range(len(data)-400, max(0, len(data)-5)):
    try:
        d = c.decode_cpb(data[i:])
        if d and c.F_DEFAULT_PROB in d:
            print("DECODED CPB:", d)
            found = True
            break
    except:
        pass
if not found:
    print("No CPB found (may be plain bundle or not full bytes)")