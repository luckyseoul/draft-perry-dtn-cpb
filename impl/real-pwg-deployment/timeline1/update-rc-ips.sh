#!/bin/bash
# Post-join helper: update host*.rc with fresh Tailscale IPs from the PWG net.
# Usage (after both nodes joined and you have the values):
#   bash ~/ion-config/update-rc-ips.sh \
#     --soul 100.123.45.67 \
#     --orin 100.123.45.68 \
#     --gw   100.96.108.99     # the current 268485000 TS IP
#
# Then restart on each: bash ~/ion-config/start-*.sh
set -euo pipefail

SOUL_NEW=""
ORIN_NEW=""
GW_NEW=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --soul) SOUL_NEW="$2"; shift 2 ;;
    --orin) ORIN_NEW="$2"; shift 2 ;;
    --gw)   GW_NEW="$2"; shift 2 ;;
    -h|--help) echo "see header"; exit 0 ;;
    *) echo "unknown $1"; exit 1 ;;
  esac
done

if [[ -z "$SOUL_NEW" || -z "$ORIN_NEW" || -z "$GW_NEW" ]]; then
  echo "ERROR: need --soul --orin --gw"
  exit 1
fi

echo "Updating rcs with:"
echo "  soulkiller new: $SOUL_NEW"
echo "  orin new:       $ORIN_NEW"
echo "  gateway (000):  $GW_NEW"

# soulkiller rc (this machine)
RC122=~/ion-config/host268485122.rc
if [[ -f "$RC122" ]]; then
  sed -i "s|Tailscale IP: .*|Tailscale IP: $SOUL_NEW|" "$RC122" || true
  sed -i "s|100\.96\.108\.37:4556|$GW_NEW:4556|g" "$RC122"
  sed -i "s|100\.70\.177\.14:4556|$ORIN_NEW:4556|g" "$RC122"
  sed -i "s|udp/100\.96\.108\.37:4556|udp/$GW_NEW:4556|g" "$RC122"
  sed -i "s|udp/100\.70\.177\.14:4556|udp/$ORIN_NEW:4556|g" "$RC122"
  # update any old comments
  sed -i "s|268485000 at .*|268485000 at $GW_NEW:4556|" "$RC122" || true
  echo "Updated $RC122"
fi

# orin rc (will also need to be pushed or run on orin)
RC121=~/ion-config/host268485121.rc
if [[ -f "$RC121" ]]; then
  sed -i "s|Tailscale IP: .*|Tailscale IP: $ORIN_NEW|" "$RC121" || true
  sed -i "s|100\.96\.108\.37:4556|$GW_NEW:4556|g" "$RC121"
  sed -i "s|100\.107\.44\.6:4556|$SOUL_NEW:4556|g" "$RC121"
  sed -i "s|udp/100\.96\.108\.37:4556|udp/$GW_NEW:4556|g" "$RC121"
  sed -i "s|udp/100\.107\.44\.6:4556|udp/$SOUL_NEW:4556|g" "$RC121"
  sed -i "s|268485000 at .*|268485000 at $GW_NEW:4556|" "$RC121" || true
  echo "Updated local $RC121 (scp or edit on orin too)"
fi

echo "Done. Review diffs, then scp the 121 rc to orin if needed:"
echo "  scp ~/ion-config/host268485121.rc nick@NEW_ORIN_IP:/home/nick/ion-config/"
echo "Then on each node: bash ~/ion-config/start-*.sh"
