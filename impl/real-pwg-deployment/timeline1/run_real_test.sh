#!/bin/bash
# End-to-end real bundle + CPB test launcher (run on sender side)

set -e
echo "=== Real CPB Bundle Creation + Receipt Test ==="
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
