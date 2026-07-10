#!/bin/bash
# Unified launcher for all DTN services (ION + CFDP/bputa + DTNEx).
# Run this from *any* of the PWG testbed nodes:
#   bash /home/nick/ion-config/start-dtn.sh
#
# It auto-detects the node (soulkiller/122, orin/121, horus/123) using
# hostname or Tailscale IP and customizes the RC file, DTNEx conf, logs, etc.
#
# The old per-node scripts (start-soulkiller.sh etc.) are now thin wrappers
# around this one for backward compatibility (systemd services, muscle memory).
#
# What gets started:
#   - Clean SDR/shm + ionstart with the node .rc (includes plans, outducts, cfdp entities)
#   - Explicit cfdpclock + "s 'bputa'" to guarantee RUNNING status + 6 entities
#   - DTNEx (dtnex-*.conf) for dynamic contact exchange
#
# Result on a healthy node: bpclock, ipnfw, 3x udpclo, cfdpclock, bputa, dtnex
# with cfdpadmin showing bputa + cfdpclock RUNNING and 6 remote entities.

set -euo pipefail

CONFIG_DIR="/home/nick/ion-config"
DTNEX_DIR="/home/nick/ion-dtn-dtnex"
ION_LOG="$CONFIG_DIR/ion.log"

# --- Auto-detect which node we are on (hostname preferred, IP fallback) ---
detect_node() {
  local hname
  hname=$(hostname 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "")
  local tsip
  tsip=$(tailscale ip -4 2>/dev/null | head -1 || echo "")
  local ts0ip
  ts0ip=$(ip -4 addr show tailscale0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 || echo "")

  if [[ "$hname" == *soulkiller* || "$hname" == *122* ]]; then
    NODE=122; HOST=soulkiller; DTNEX_NAME=dtnex-soulkiller
  elif [[ "$hname" == *orin* || "$hname" == *121* ]]; then
    NODE=121; HOST=orin; DTNEX_NAME=dtnex-orin
  elif [[ "$hname" == *horus* || "$hname" == *123* || "$hname" == *third* ]]; then
    NODE=123; HOST=horus; DTNEX_NAME=dtnex-horus
  elif [[ "$tsip" == "100.91.23.41" || "$ts0ip" == "100.91.23.41" ]]; then
    NODE=122; HOST=soulkiller; DTNEX_NAME=dtnex-soulkiller
  elif [[ "$tsip" == "100.92.115.65" || "$ts0ip" == "100.92.115.65" ]]; then
    NODE=121; HOST=orin; DTNEX_NAME=dtnex-orin
  elif [[ "$tsip" == "100.65.168.37" || "$ts0ip" == "100.65.168.37" ]]; then
    NODE=123; HOST=horus; DTNEX_NAME=dtnex-horus
  else
    echo "ERROR: Could not auto-detect node." >&2
    echo "  hostname=$hname  tailscale=$tsip" >&2
    echo "Provide hints: NODE=122 HOST=soulkiller DTNEX_NAME=dtnex-soulkiller $0" >&2
    exit 1
  fi

  RC_FILE="$CONFIG_DIR/host268485${NODE}.rc"
  DTNEX_CONF="$DTNEX_DIR/${DTNEX_NAME}.conf"
  DTNEX_LOG="/tmp/${DTNEX_NAME}.log"
}

detect_node

echo "==> [${HOST} ${NODE}] Unified DTN launcher (auto-detected)"
echo "    RC file : $RC_FILE"
echo "    DTNEx   : $DTNEX_CONF"

# Robust pre-clean (identical logic to the previous per-node start-*.sh)
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
ionstart -I "$RC_FILE" > "$ION_LOG" 2>&1 &

sleep 5

# Explicit CFDP bring-up so cfdpclock + bputa are reliably RUNNING + entities present.
# (The .rc already declares the 6 entities and "s 'bputa'", but this guarantees the daemons
#  are attached and marked RUNNING even after partial/lingering previous runs.)
echo "==> Ensuring cfdpclock + bputa (s 'bputa') for CPB use ..."
pkill -x cfdpclock 2>/dev/null || true
sleep 1
cfdpclock &
sleep 5
(echo "s 'bputa'"; echo "l"; echo "q") | cfdpadmin 2>/dev/null | cat || true

echo ""
echo "==> Processes:"
ps aux | grep -E '[b]pclock|[i]pnfw|[u]dpclo|[c]fdpclock|[b]puta|[d]tnex' | cat || true

echo ""
echo "==> ION log tail (last 15):"
tail -15 "$ION_LOG" || true

echo ""
echo "==> cfdpadmin l (expect cfdpclock + bputa RUNNING + 6 entities):"
(echo "l"; echo "q") | cfdpadmin 2>/dev/null | cat || true

# DTNEx (only launch if the node-specific conf actually exists on *this* machine)
if [ -x /usr/local/bin/dtnex ] && [ -f "$DTNEX_CONF" ]; then
  pkill -x dtnex 2>/dev/null || true
  sleep 1
  echo "==> Starting DTNEx for ${HOST}..."
  cd "$DTNEX_DIR"
  nohup /usr/local/bin/dtnex -c "${DTNEX_NAME}.conf" >> "$DTNEX_LOG" 2>&1 &
  echo "DTNEx ${HOST} PID $!"
else
  echo "==> Skipping DTNEx (no /usr/local/bin/dtnex or $DTNEX_CONF not present on this node)"
fi

echo ""
echo "==> Ready on ipn:268485${NODE} (${HOST})"
echo "    Example: bpsource ipn:268485${NODE}.1 \"hello from ${HOST} at \$(date)\" ipn:268485000.1"
echo "    Stop   : ionstop; killm; pkill -x cfdpclock dtnex 2>/dev/null || true"
echo "    Verify : ps aux | grep -E '[b]pclock|[c]fdpclock|[b]puta|[d]tnex' ; (echo l; echo q) | cfdpadmin"
