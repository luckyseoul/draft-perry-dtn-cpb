#!/bin/bash
# Robust start for ION node 123 on horus (manual or via systemd)
# bash /home/nick/ion-config/start-horus.sh
# Now includes full daemon launches + aggressive clean for stubborn SDR on horus.
set -euo pipefail

NODE="123"
HOST="horus"
CONFIG_DIR="/home/nick/ion-config"
RC_FILE="$CONFIG_DIR/host268485${NODE}.rc"
LOG_FILE="$CONFIG_DIR/ion.log"

echo "==> [${HOST} ${NODE}] Pre-clean and prepare ION (aggressive for SDR)..."
pkill -9 -x bpclock 2>/dev/null || true
pkill -9 -x ipnfw 2>/dev/null || true
pkill -9 -x cfdpclock 2>/dev/null || true
pkill -9 -x bputa 2>/dev/null || true
pkill -9 -x dtnex 2>/dev/null || true
pkill -9 -x udpclo 2>/dev/null || true
pkill -9 -f 'ionstart' 2>/dev/null || true
ionstop 2>/dev/null || true
killm 2>/dev/null || true
sleep 1
# aggressive shm/sem cleanup (horus often has 40+ lingering sems)
for id in $(ipcs -m 2>/dev/null | awk 'NR>3 && $1 ~ /^[0-9x]/ {print $2}'); do ipcrm -m $id 2>/dev/null || true; done
for id in $(ipcs -s 2>/dev/null | awk 'NR>3 && $1 ~ /^[0-9x]/ {print $2}'); do ipcrm -s $id 2>/dev/null || true; done
rm -f /tmp/ion* /dev/shm/sem.*ion* /dev/shm/*ion* 2>/dev/null || true

sudo sysctl -w kernel.shmmax=1073741824 kernel.shmall=262144 2>&1 || true
sysctl kernel.shmmax kernel.shmall 2>/dev/null | cat || true

if [ ! -f /tmp/default.key ]; then
  dd if=/dev/urandom of=/tmp/default.key bs=32 count=1 2>/dev/null || true
  chmod 600 /tmp/default.key
fi
# Make bputa binary discoverable by cfdpclock for "s 'bputa'" entity task (fixes "NOT RUNNING" and exec errors)
ln -sf /usr/local/bin/bputa /usr/bin/bputa 2>/dev/null || true
ln -sf /usr/local/bin/bputa /usr/local/sbin/bputa 2>/dev/null || true
export PATH=/usr/local/bin:$PATH

echo "a key default /tmp/default.key" | ionsecadmin 2>/dev/null || true

echo "==> [${HOST} ${NODE}] Starting ION with $RC_FILE ..."
ionstart -I "$RC_FILE" > "$LOG_FILE" 2>&1 &

sleep 6

echo "==> Launch daemons..."
bpclock &
ipnfw &
udpclo 100.96.108.37:4556 &
udpclo 100.91.23.41:4556 &
udpclo 100.65.168.37:4556 &
cfdpclock &

sleep 5

echo "==> cfdpadmin s 'bputa' (and l)..."
cfdpadmin 2>/dev/null <<'EOC' | cat || true
s 'bputa'
l
q
EOC

sleep 2
echo "==> Re-checking bputa..."
cfdpadmin 2>/dev/null <<'EOC' | cat || true
s 'bputa'
l
q
EOC

echo ""
echo "==> Processes:"
ps -ef | grep -E '[b]pclock|[i]pnfw|[u]dpclo|[c]fdpclock|[b]puta' | cat || true

echo ""
echo "==> Log tail (last 15):"
tail -15 "$LOG_FILE" || true

echo ""
echo "==> cfdpadmin l (expect cfdpclock + bputa + 6 entities):"
cfdpadmin 2>/dev/null <<'EOC' | cat || true
l
q
EOC

echo ""
echo "==> Ready. Example: bputa ipn:268485${NODE}.64 /tmp/testfile"
echo "==> Stop: ionstop; killm"

# Launch DTNEx ...
if [ -x /usr/local/bin/dtnex ] && [ -f /home/nick/ion-dtn-dtnex/dtnex-horus.conf ]; then
  pkill -x dtnex 2>/dev/null || true
  sleep 1
  echo "Starting DTNEx for horus..."
  cd /home/nick/ion-dtn-dtnex
  nohup /usr/local/bin/dtnex -c dtnex-horus.conf >> /tmp/dtnex-horus.log 2>&1 &
  DTNPID=$!
  echo "DTNEx horus PID $DTNPID"
  sleep 2
  if ps -p $DTNPID >/dev/null 2>&1; then 
    echo "DTNEX horus confirmed running"
  else 
    echo "DTNEX horus not running, retrying..."; 
    nohup /usr/local/bin/dtnex -c dtnex-horus.conf >> /tmp/dtnex-horus.log 2>&1 & 
    echo "DTNEx horus retry PID $!"
  fi
fi
