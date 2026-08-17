# ION DTN PWG Testbed - Short FAQ

(Full PDF also in snapshot. This is the text version for the repo.)

Three-node setup on IPNSIG PWG Tailscale (IPNSIG PWG mesh)

## Current Node Setup
- node-268485123 (268485123) - 100.65.168.37 | Hostname: node-268485123 | 192.168.1.85 (nick)
- node-268485122 (268485122) - 100.91.23.41 | Hostname: node-268485122
- node-268485121 (268485121) - 100.92.115.65 | Hostname: node-268485121 | Jetson Node-268485121 Nano
- gateway (268485000) - 100.96.108.37

All use ION UDPCL :4556, long contacts, cfdp+bputa, DTNEx.

## How to Start/Stop
Use the start-*.sh scripts (they do the full clean + sysctl + key + ionstart + cfdp check + DTNEx launch).

## How to Ping
bping ipn:26848512X.3 or .4 (bpecho on target .4 or DTNEx .12161)

## CPB Experiment
See the updated Implementation Status in this commit for the 8/8 fixed test results on the live link, and the HDTN side experiment that was attempted then fully removed to keep the base stable.

Full details and exact rcs/starts in the timeline1/ subdir of this snapshot.
