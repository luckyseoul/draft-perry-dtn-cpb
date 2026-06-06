#!/bin/bash
# Robust start for ION node 122 on soulkiller (manual or via systemd)
# bash /home/nick/ion-config/start-soulkiller.sh
set -euo pipefail

NODE="122"
HOST="soulkiller"
CONFIG_DIR="/home/nick/ion-config"
RC_FILE="$CONFIG_DIR/host268485${NODE}.rc"
LOG_FILE="$CONFIG_DIR/ion.log"

echo "==> [${HOST} ${NODE}] Pre-clean and prepare ION..."
ionstop 2>/dev/null || true
sleep 1
killm 2>/dev/null || true
rm -f /tmp/ion* /dev/shm/sem.*ion* 2>/dev/null || true

sudo sysctl -w kernel.shmmax=268435456 >/dev/null 2>&1 || true
sudo sysctl -w kernel.shmall=65536 >/dev/null 2>&1 || true

if [ ! -f /tmp/default.key ]; then
  dd if=/dev/urandom of=/tmp/default.key bs=32 count=1 2>/dev/null || true
  chmod 600 /tmp/default.key
fi
echo "a key default /tmp/default.key" | ionsecadmin 2>/dev/null || true

echo "==> [${HOST} ${NODE}] Starting ION with $RC_FILE ..."
ionstart -I "$RC_FILE" > "$LOG_FILE" 2>&1 &

sleep 5

echo "==> Processes:"
ps aux | grep -E '[b]pclock|[i]pnfw|[u]dpclo|[c]fdpclock|[b]puta' | cat || true

echo ""
echo "==> Log tail (last 15):"
tail -15 "$LOG_FILE" || true

echo ""
echo "==> cfdpadmin l (expect cfdpclock + bputa):"
cfdpadmin 2>/dev/null <<'EOC' | cat || true
l
q
EOC

echo ""
echo "==> Ready. Example: bpsource ipn:268485${NODE}.1 \"hello from ${HOST} at \$(date)\" ipn:268485000.1"
echo "==> Stop: ionstop; killm"

# Launch DTNEx for dynamic contact graph exchange (after ION ready)
if [ -x /usr/local/bin/dtnex ] && [ -f /home/nick/ion-dtn-dtnex/dtnex-soulkiller.conf ]; then
  pkill -x dtnex 2>/dev/null || true
  sleep 1
  echo "Starting DTNEx for soulkiller..."
  cd /home/nick/ion-dtn-dtnex
  nohup /usr/local/bin/dtnex -c dtnex-soulkiller.conf >> /tmp/dtnex-soulkiller.log 2>&1 &
  echo "DTNEx soulkiller PID $!"
fi