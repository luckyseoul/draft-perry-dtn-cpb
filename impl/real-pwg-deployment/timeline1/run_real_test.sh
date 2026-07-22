#!/bin/bash
# End-to-end real bundle + CPB test launcher (run on sender side)
#
# NOTE: This script is LEGACY from an earlier phase of the project
# (pre "life of a bundle" canonical 121B work and the 72/32 bputa campaigns).
# It references older tools (sender.py, receiver.py --listen, CUDA batching,
# and a C sender via make). For the current canonical proof and live demo,
# see life_of_a_bundle.py (now included in this snapshot), the
# life_of_a_bundle_quickref.txt, and the start-*.sh + bputa workflows.
#
# This file is retained in the snapshot for historical completeness.

set -e
echo "=== Real CPB Bundle Creation + Receipt Test ===" (legacy script)
echo "CUDA batch generation: $(python3 -c 'from packet import has_cuda; print(has_cuda())')"

echo ""
echo "Step 1: Generate & prepare packets (CUDA accelerated if possible)"
python3 sender.py --count 20 --use-gpu

echo ""
echo "Step 2: On the RECEIVING machine, start the listener in another terminal:"
echo "   cd /home/nick/real_cpb_packet_test"
echo "   python3 receiver.py --listen --endpoint ipn:THEIR_NODE.1"
echo ""
echo "Step 3: (Optional but recommended) Build and use the proper C sender for real extension blocks"
echo "   make"
echo "   # Then get BTSD hex from the Python generator and run the C program"
echo ""
echo "This proves real bundles with real CPB blocks crossing the wire on both ends."
