#!/bin/bash
# Robust start for horus (node 268485123) (manual or via systemd)
# bash /home/nick/ion-config/start-horus.sh
#
# Thin wrapper around the unified any-node launcher (start-dtn.sh).
# The unified script auto-detects the current host and brings up the full
# stack (ION + explicit cfdpclock/bputa + DTNEx). This keeps systemd service
# templates and old habits working while centralizing the real logic.
#
# Note: start-123.sh is a symlink to this file for backward compatibility.

exec "$(dirname "$0")/start-dtn.sh" "$@"
