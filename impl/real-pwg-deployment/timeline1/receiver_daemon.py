#!/usr/bin/env python3
"""
Robust CPB Receiver Daemon for Orin (or soulkiller).

Usage:
  python3 receiver_daemon.py --endpoint ipn:268485121.1 --log /tmp/cpb_rx.log

It will run bprecv in the background and decode + log every CPB it sees in real time.
Perfect for leaving running while you fire the queue from the other side.
"""

import subprocess
import argparse
import sys
import time
import os

sys.path.insert(0, os.path.dirname(__file__))
from packet import has_cuda

try:
    import cpb as cpb_module
except ImportError:
    cpb_module = None

def decode_cpb(data: bytes):
    if cpb_module is None:
        return None
    for i in range(len(data) - 20):
        try:
            decoded = cpb_module.decode_cpb(data[i:])
            if decoded and (cpb_module.F_DEFAULT_PROB in decoded or cpb_module.F_PATH_ENTRIES in decoded):
                return decoded
        except Exception:
            pass
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--log", default="/tmp/cpb_received.log")
    args = parser.parse_args()

    print(f"CPB Receiver Daemon starting on {args.endpoint}")
    print(f"Logging to {args.log}")
    print("CUDA available for future decode acceleration:", has_cuda())
    print("Press Ctrl-C to stop.\n")

    with open(args.log, "a") as logfile:
        proc = subprocess.Popen(
            ["bprecv", args.endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                # In real use, bprecv output would contain the bundle or we would capture raw.
                # For this version we log whatever we get and try to decode if it looks like bundle data.
                logfile.write(line.decode(errors="ignore"))
                logfile.flush()

                # Best effort: if the line or accumulated data contains a bundle, try decode
                # (In a production version you'd use a proper BP receiver API or file-based reception)
                if b"bundle" in line.lower() or len(line) > 100:
                    cpb = decode_cpb(line)
                    if cpb:
                        msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DECODED CPB: {cpb}\n"
                        print(msg, end="")
                        logfile.write(msg)
                        logfile.flush()

        except KeyboardInterrupt:
            proc.terminate()
            print("\nReceiver daemon stopped.")

if __name__ == "__main__":
    main()
