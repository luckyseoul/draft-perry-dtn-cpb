#!/bin/bash
# Robust start for third node 268485123 (future host at 192.168.1.85)
set -euo pipefail
NODE="123"
HOST="third-host"
CONFIG_DIR="/home/nick/ion-config"
RC_FILE="$CONFIG_DIR/host268485${NODE}.rc"
LOG_FILE="$CONFIG_DIR/ion.log"

echo "==> [${HOST} ${NODE}] Pre-clean..."
ionstop 2>/dev/null || true; sleep 1; killm 2>/dev/null || true
rm -f /tmp/ion* /dev/shm/sem.*ion* 2>/dev/null || true
sudo sysctl -w kernel.shmmax=268435456 >/dev/null 2>&1 || true

if [ ! -f /tmp/default.key ]; then dd if=/dev/urandom of=/tmp/default.key bs=32 count=1 2>/dev/null || true; chmod 600 /tmp/default.key; fi
echo "a key default /tmp/default.key" | ionsecadmin 2>/dev/null || true

echo "==> Starting ION 268485123 ..."
ionstart -I "$RC_FILE" > "$LOG_FILE" 2>&1 &

sleep 5
ps aux | grep -E '[b]pclock|[i]pnfw|[u]dpclo|[c]fdpclock|[b]puta' | cat || true
tail -10 "$LOG_FILE" || true
