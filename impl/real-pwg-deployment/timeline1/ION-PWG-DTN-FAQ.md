# ION DTN PWG Testbed - Short FAQ

Three-node setup on IPNSIG PWG Tailscale (samo.grasic@account)

## Current Node Setup

All nodes use ION (UDP CL on port 4556), long-duration bidirectional contacts, cfdp + bputa support, and are on the main PWG Tailscale network.

- horus (268485123) - 100.65.168.37 | Hostname: horus | 192.168.1.85 (nick, pw=drpepper)
- soulkiller (268485122) - 100.91.23.41 | Hostname: soulkiller | this machine
- orin (268485121) - 100.92.115.65 | Hostname: orin | Jetson Orin Nano
- dtngw / gateway (268485000) - 100.96.108.37 | Public DTN gateway (bpecho often on .12161 per lab notes)

Note: Confirm with 'tailscale status'. Gateway IP has been stable. All rcs use the current TS IPs in outducts/plans.

## How to Start / Stop ION

Use the per-node start scripts (they do full clean, shmmax, key, ionstart -I rc + status):

bash ~/ion-config/start-soulkiller.sh
bash ~/ion-config/start-orin.sh   # ssh nick@100.92.115.65
bash ~/ion-config/start-123.sh    # ssh nick@100.65.168.37 (horus)

Manual equivalent (script does this + killm + rm shm):

sudo sysctl -w kernel.shmmax=268435456
ionstop 2>/dev/null || true ; killm 2>/dev/null || true
rm -f /tmp/ion* /dev/shm/sem.*ion* 2>/dev/null || true
ionstart -I ~/ion-config/host268485122.rc > ~/ion-config/ion.log 2>&1 &

- Stop: ionstop ; killm

Note: Systemd templates are in ~/ion-config/ion-*.service.template (copy to /etc/systemd/system/ and enable for auto-start if desired).

## How to Ping Remote Nodes (bping)

bping needs a bpecho listener on the target (DTNEx nodes run it on .12161):

# On target:
bpecho ipn:268485122.4

# From sender:
bping ipn:268485121.3 -c 3   # orin -> soulkiller
bping ipn:268485122.3 -c 3   # soulkiller -> orin

- Use distinct service numbers (.3 vs .4) for local loop tests.

Note: No reply? Check tailscale mesh + that the rc outducts/plans have the *current* TS IPs, and that the contact graph on dtngw includes the node (may require manual add via PWG ops).

## How to Send / Receive Bundles

# Send:
bpsource ipn:268485122.1 "Hello from soulkiller to horus $(date)"

# Receive (on target):
bpsink ipn:268485123.1

# Inspect:
bplist

- bpsource takes destEID and optional text (local node is source).
- For the CFDP path used in CPB tests: the rcs already have the cfdpadmin section with s 'bputa'.

## Common Issues & Fixes

- SDR 'Can't get shared memory segment' / key=65280 size=0: sudo sysctl -w kernel.shmmax=268435456 then run the start-*.sh (scripts do killm + clean + the sysctl).
- Security database not found: start scripts create /tmp/default.key and run the ionsecadmin 'a key ...' line.
- Bundles not flowing: verify tailscale status (same net?), rc outducts/plans have today's TS IPs, and dtngw contact graph knows about the node (request manual addition via PWG mailing list / matrix if needed).
- bputa missing or 'No such file': the ION tree on horus was copied from soulkiller; ensure /usr/local/bin/bputa exists and is in PATH.
- ipnadmin syntax errors on start: rc had garbage lines from manual edits - use the clean versions in ~/ion-config/ or re-run update-rc-ips.sh.

## Key Files

- ~/ion-config/ on every node: the rcs, start-*.sh, ion.log, update-rc-ips.sh, *.service.template, host268485123.rc skeleton
- Dashboard: ~/ion-config/master-dtn-dashboard.py (rich live view)
- This FAQ: ~/ion-config/ION-PWG-DTN-FAQ.pdf (also copied to nicknite@192.168.1.44)
- Deeper notes: ~/ion-config/SOULKILLER-NEXT-STEPS.txt
- CPB real experiment: ~/draft-perry-dtn-cpb/impl/real-cpb-ion-test/ (8+8 results, bundles, recv_cpb.py, updated draft)

Keep the start scripts, rcs, dashboard, and this FAQ in sync across soulkiller, orin, horus, and the backup at nicknite. For new nodes use the same Tailscale key from the HedgeDoc and the update-rc-ips.sh pattern.