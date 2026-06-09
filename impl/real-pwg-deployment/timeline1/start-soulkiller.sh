#!/bin/bash
# Robust start for ION node 122 on soulkiller (manual or via systemd)
# bash /home/nick/ion-config/start-soulkiller.sh
#
# Now a thin wrapper around the unified any-node launcher (start-dtn.sh).
# The unified script auto-detects the current host and brings up the full
# stack (ION + explicit cfdpclock/bputa + DTNEx). This keeps systemd service
# templates and old habits working while centralizing the real logic.

exec "$(dirname "$0")/start-dtn.sh" "$@"
