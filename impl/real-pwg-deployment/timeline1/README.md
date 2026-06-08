# timeline1 Snapshot — CPB on Real ION DTN (PWG Tailscale Testbed)

This directory is a self-contained snapshot of the `timeline1` branch work for the draft-perry-dtn-cpb experiment on the IPNSIG Planetary Working Group (PWG) Tailscale mesh.

**Date of this snapshot update:** 2026-06-08 (includes latest canonical 121B artifact and lab notes)

## Minimum Bar of Proof for the CPB RFC (what this snapshot demonstrates)

The goal was a pragmatic "prove it works" demonstration on real ION stacks (no HDTN, no heavy custom tuning) using bputa/CFDP injection over UDPCL on the live Tailscale underlay.

Key evidence present here:

- **Canonical 121-byte reference bundle** (exact example used in the draft XML artwork):
  - Reproducible with the included `life_of_a_bundle.py --dst ... --write-bundle`
  - Full BEFORE (high-level + pre-CBOR structures), WIRE (exact 121 bytes + compact hex matching the draft), AFTER (decode recovers the CPB map `{0: 0.64990234375, 1: [[268484820, 0.64990234375]]}` + "save a horse, ride a cowboy" payload).
  - Included files: `proof_simple.bundle`, `live_demo_20260607_083850.bundle`, `live_cpb_20260608_001833.bundle` (fresh from latest run).

- **Live injection over real ION stack**: Multiple `bputa <121B-file> ipn:268485121.64` (CFDP entity) from soulkiller to orin while orin was reachable. Bundles reached the remote ION agent (see bplist "Queued for forwarding..." evidence in the notes).

- **Prior real deliveries with intact CPB decode** (from the completed 72-message + 32 test-nodes-only campaign):
  - 72 bundles in `cpb_72_with_my/` (3 real nodes × 3 targets × 8 quirky one-liner payloads, with and without CPB).
  - 32 in `cpb_test_to_each_other/` (bidirectional Moon 268484801 ↔ Mars 268484820, with/without CPB).
  - Verified examples (e.g. `moon_to_mars_with_cpb_01_save.bundle`, `from_..._01_save.bundle`) were pulled from receivers and successfully decoded with the exact original CPB block 200 + payload intact.
  - Selected verification copies in `cpb_with_verification/`.

- **Honest limitations documented** (so they can be followed up if reviewers ask):
  - "Long emulated" DTNEx contacts (June 6 → Sep 14 2026, 10 MB/s confidence 1.0) caused bundles to queue ("Queued for forwarding to 'ipn:268484820.0'." etc.) without delivery in short test windows. Exact `ionadmin l contact` output is in the quickref.
  - Orin (268485121) had only a partial ION install (no `bprecv` binary). Direct BP listeners produced error files; successful captures used the CFDP file-delivery path + the `find /tmp ... -size 12[0-2]c -mmin -N` recipe.
  - All details + reproduction commands in `life_of_a_bundle_quickref.txt`.

Full narrative, exact commands for live demo, before/wire/after hexdumps, CFDP capture recipe, and "followup items ready" list are in:

- `life_of_a_bundle_quickref.txt` (primary lab notebook + demo reference)
- `LIVE_TRANSMISSION_STATUS.txt` (project history)

The supporting Python tools that generate/decode the canonical bundles (`life_of_a_bundle.py`, `cpb.py`, `packet.py`) and the slide generator (`make_life_pptx.py`) are **now included directly in this snapshot directory** for self-contained reproduction.

## Contents

- **Bundles**:
  - `cpb_72_with_my/` — 72 messages (full set)
  - `cpb_test_to_each_other/` — 32 messages (test nodes Moon/Mars only, bidirectional, with/without CPB; includes the verified moon_to_mars_with_cpb examples)
  - `cpb_to_mars/`, `cpb_with_verification/` — selected subsets
  - Loose canonical 121B files (see above)

- **Narrative & instructions**:
  - `life_of_a_bundle_quickref.txt`
  - `LIVE_TRANSMISSION_STATUS.txt`
  - `ION-PWG-DTN-FAQ.md` (+ PDF)
  - `pwg-node-addition-request.email.txt`

- **Reproduction tools** (added 2026-06-08 for self-containment):
  - `life_of_a_bundle.py`
  - `cpb.py`
  - `packet.py`
  - `make_life_pptx.py`
  - `receiver_daemon.py`

- **Node configs & launchers**:
  - `host26848512{1,2,3}.rc`
  - `start-*.sh` (soulkiller/122, orin/121, horus/123)
  - `*.service.template` (systemd units; note the soulkiller one was corrected in this snapshot)
  - `update-rc-ips.sh`
  - `run_real_test.sh` (marked LEGACY — see header comment)

- **Logs & misc**:
  - `receive_logs/` (mostly bprecv-not-found traces documenting the orin tooling discovery; see `receive_logs/README.txt`)
  - Service templates, etc.

## How to Use for Reproduction / Live Demo

1. `cd` into this directory.
2. Read `life_of_a_bundle_quickref.txt` (top sections for the canonical BEFORE/WIRE/AFTER; "LIVE DEMO COMMANDS" and "ORIN CAPTURE NOTES" for the practical steps).
3. Generate a fresh canonical: `python3 life_of_a_bundle.py --dst 268485121 --write-bundle /tmp/my_121.bundle`
4. On a running ION node with cfdp entity .64 configured: `bputa /tmp/my_121.bundle ipn:268485121.64`
5. On receiver side, use the CFDP find recipe (or bprecv if full tools are installed) and `python3 life_of_a_bundle.py --decode-file <file>` to show the AFTER decode.
6. For slides: `python3 make_life_pptx.py` (adjust as needed).

See the quickref for the exact "minimum bar" evidence list, the long-emulated contact diagnosis, and the prepared followup items (shorter contacts, orin tooling completion, etc.).

## Notes on This Snapshot

- All .rc files intentionally contain the long-duration contacts (`+8640000`) to the dedicated emulated nodes (Moon 268484801, Mars 268484820) and gateway (268485000). This is the state that produced the observed queuing behavior documented in the notes.
- The snapshot is intentionally a lab notebook + artifact bundle, not a polished "clean room" package. It preserves the honest state of the real PWG Tailscale + ION runs.
- Passwords and absolute paths (`/home/nick/...`) appear in comments and scripts — this matches the actual experimental environment.

For the draft RFC XML "Implementation Status / Real ION Testbed" section, refer to the parent repository (the quickref + this snapshot provide the supporting evidence and reproduction material).

---

This snapshot was refreshed 2026-06-08 as part of bringing the timeline1 branch up to the minimum bar of proof while keeping detailed lab notes. See git history for the exact commit.