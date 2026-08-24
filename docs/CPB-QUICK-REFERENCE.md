# Contact Probability Block (CPB) — Quick Reference

Short visual introduction to the unsubmitted CPB working draft
(*Probabilistic Contact Metadata for DTN Bundle Routing*): problem, wire
format, lifecycle, validation scope, and security defaults.

See [`draft-perry-dtn-cpb.xml`](../draft-perry-dtn-cpb.xml). Pre-submission
review copy (not on the IETF Internet-Drafts repository).

---

## 1. The problem in one sentence

DTN contacts are often **uncertain**, but BPv7 endpoint IDs must stay
**immutable** — so probability must not be stuffed into the destination URI.

### Why not `ipn:100.1?prob=0.75`?

![Why extension block](images/01-why-extension-block.png)

Routers that rewrite EIDs to carry metadata break integrity, security
bindings, and the BPv7 model. CPB puts probability in an **extension block**
instead.

---

## 2. What CPB is

CPB is a **BPv7 extension block** that carries *in-bundle* probability /
confidence metadata between nodes. It is a **transport for estimates**, not
a replacement for CGR, PRoPHET, MaxProp, or similar protocols.

Those protocols can **produce or consume** CPB data while keeping their own
algorithms. CPB is only the **in-bundle scalar** ([0,1] plus metric-type).
Encounter tables, contact plans, summary vectors, Spray copy-count **L**,
and MaxProp hop-lists stay in each protocol’s control plane (draft §5).

![Bundle anatomy](images/02-bundle-anatomy.png)

- Open questions (noise, adversaries, multi-domain trust, production interop)
  are listed in the draft and not claimed solved.
- Examples use block type **200 (0xC8)**; IANA assigns the permanent code.
  Implementations **must not** hardcode `0xC8`.

---

## 3. What’s inside a CPB (fields 0–7)

The block-type-specific data is a **CBOR map**:

![CPB fields](images/03-cpb-fields.png)

| Key | Meaning |
|-----|---------|
| 0 | Default probability |
| 1 | Per-path `[next-hop, probability]` list (senders **SHOULD NOT** exceed 8 on constrained links) |
| 2 | Timestamp (DTN epoch) |
| 3 | Source PCE identifier (optional) |
| 4 | Validity duration (TTL) |
| 5 | Metric type (0 PRoPHET · 1 CGR · 2 MaxProp · 3 RAPID · 4 generic) |
| 6 | Confidence / variance of the estimate |
| 7 | Format version (1 = this specification) |

**Important rule:** do **not** mix metric types in arithmetic (e.g. do not
average a PRoPHET DP with a CGR confidence).

---

## 4. Lifecycle at a router

![Lifecycle](images/07-cpb-lifecycle.png)

1. **Create or receive** a bundle that may carry one or more CPBs.
2. **Read** default / per-path probabilities (after trust/BIB policy).
3. **Decide** next hop using your routing policy.
4. **Optionally update** with fresher local estimates (append or
   strip-and-replace — see security section of the draft).
5. **Forward**; nodes that do not understand CPB pass the block through.

---

## 5. First-draft validation

The repository validates the published format and local reference code. It
does not report comparative routing-performance results.

```sh
python3 impl/test_cpb.py
python3 impl/test_config1_policies.py
python3 impl/test_sim_cpb_bridge.py
python3 impl/test_draft_consistency.py
make cddl
```

The checks cover the CBOR encoding examples and hex table, invalid floating
point handling, BTSD wrapping, encoder/decoder round trips, and deterministic
local policy/bridge behavior.

---

## 6. Security (draft §8)

Threats include false probabilities (sinkhole / blackhole), stale CPBs,
semi-trusted relays biasing routes, and inter-domain trust gaps.

- Prefer **BPSec BIB** integrity on CPBs used for routing.
- **Do not** encrypt CPB with BCB if intermediates must read it to route.
- Unauthorized or unverifiable CPBs: prefer **strict** (ignore for routing,
  still forward) over laundering signatures.
- Multi-CPB precedence applies **after** trust verification.

---

## 7. Recap

**Why is probability not allowed in the destination EID?**
BPv7 EIDs must stay immutable. Stuffing `?prob=…` into the URI invites
rewrites that break integrity bindings and the endpoint model. Put estimates
in an extension block instead.

**Name three CPB map fields and what they mean.**
Examples: **0** default probability; **1** per-path `[next-hop, probability]`
list; **5** metric-type (which semantic family the scalar belongs to). Also
common: **2** timestamp, **4** validity TTL, **7** format version.

**What does metric-type forbid between families?**
Cross-metric arithmetic — e.g. averaging a PRoPHET delivery predictability
with a CGR confidence. Consume only matching metric-types (draft §3.5).

**What is still open?**
Noisy or adversarial estimates, multi-domain trust, partial deployment
quality, and production-stack interoperability.
