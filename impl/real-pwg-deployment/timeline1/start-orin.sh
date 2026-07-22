#!/bin/bash
# Robust start for ION node 121 on orin
set -euo pipefail
NODE="121"
HOST="orin"
CONFIG_DIR="/home/nick/ion-config"
RC_FILE="$CONFIG_DIR/host268485${NODE}.rc"
LOG_FILE="$CONFIG_DIR/ion.log"
echo "==> [${HOST} ${NODE}] Pre-clean..."
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
for id in $(ipcs -m 2>/dev/null | awk 'NR>3 && $1 ~ /^[0-9x]/ {print $2}'); do ipcrm -m $id 2>/dev/null || true; done
for id in $(ipcs -s 2>/dev/null | awk 'NR>3 && $1 ~ /^[0-9x]/ {print $2}'); do ipcrm -s $id 2>/dev/null || true; done
rm -f /tmp/ion* /dev/shm/sem.*ion* 2>/dev/null || true
sudo sysctl -w kernel.shmmax=1073741824 kernel.shmall=262144 2>&1 || true
if [ ! -f /tmp/default.key ]; then dd if=/dev/urandom of=/tmp/default.key bs=32 count=1 2>/dev/null || true; chmod 600 /tmp/default.key; fi
# Make bputa binary discoverable by cfdpclock for "s 'bputa'" entity task (fixes "NOT RUNNING" and exec errors)
ln -sf /usr/local/bin/bputa /usr/bin/bputa 2>/dev/null || true
ln -sf /usr/local/bin/bputa /usr/local/sbin/bputa 2>/dev/null || true
export PATH=/usr/local/bin:$PATH

echo "a key default /tmp/default.key" | ionsecadmin 2>/dev/null || true
echo "==> ionstart..."
ionstart -I "$RC_FILE" > "$LOG_FILE" 2>&1 &
sleep 6
echo "==> daemons..."
bpclock & ipnfw &
udpclo 100.96.108.37:4556 & udpclo 100.91.23.41:4556 & udpclo 100.65.168.37:4556 &
cfdpclock &
sleep 5
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
ps -ef | grep -E '[b]pclock|[i]pnfw|[u]dpclo|[c]fdpclock|[b]puta' | cat || true
if [ -x /usr/local/bin/dtnex ] && [ -f /home/nick/ion-dtn-dtnex/dtnex-orin.conf ]; then
  pkill -x dtnex 2>/dev/null || true; sleep 1; cd /home/nick/ion-dtn-dtnex; nohup /usr/local/bin/dtnex -c dtnex-orin.conf >> /tmp/dtnex-orin.log 2>&1 &
  DTNPID=$!
  echo "DTNEx orin PID $DTNPID"
  sleep 2
  if ps -p $DTNPID >/dev/null 2>&1; then 
    echo "DTNEX orin confirmed running"
  else 
    echo "DTNEX orin not running, retrying..."; 
    nohup /usr/local/bin/dtnex -c dtnex-orin.conf >> /tmp/dtnex-orin.log 2>&1 & 
    echo "DTNEx orin retry PID $!"
  fi
fi
