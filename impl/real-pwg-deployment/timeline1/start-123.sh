#!/bin/bash
# Robust start for third node 268485123 / horus (manual or via systemd)
# bash /home/nick/ion-config/start-123.sh
#
# Now a thin wrapper around the unified any-node launcher (start-dtn.sh).
# The unified script auto-detects the current host and brings up the full
# stack (ION + explicit cfdpclock/bputa + DTNEx). This keeps systemd service
# templates and old habits working while centralizing the real logic.

exec "$(dirname "$0")/start-dtn.sh" "$@"
