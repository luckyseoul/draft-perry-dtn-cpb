# Contact Probability Block (CPB) — Quick Reference Guide

**Purpose:** a quick catch-up so anyone reading this repo (or reviewing the
draft later) can understand the *concept* without first reading the full
Internet-Draft at length.

Fifteen-minute visual intro to **draft-perry-dtn-cpb-00**
(*Probabilistic Contact Metadata for DTN Bundle Routing*): problem, wire idea,
fields, lifecycle, experiment headline, and security defaults. Normative text
stays in the Internet-Draft
([`draft-perry-dtn-cpb.xml`](../draft-perry-dtn-cpb.xml)); this guide is
non-normative.

**Audience:** people who know BPv7 basics and need why / what / how before (or
instead of) a full draft pass.

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

- **Experimental** status: open questions (noise, adversaries, multi-domain
  trust, production interop) are listed in the draft and not claimed solved.
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
| 2 | Timestamp (seconds since DTN epoch origin; see draft for units) |
| 3 | Source PCE identifier (optional) |
| 4 | Validity duration (TTL) |
| 5 | Metric type (0 PRoPHET · 1 CGR · 2 MaxProp · 3 RAPID · 4 generic) |
| 6 | Confidence / variance of the estimate |
| 7 | Format version (1 = this specification) |

**Important rule:** do **not** mix metric types in arithmetic (for example,
do not average a PRoPHET delivery predictability with a CGR confidence).

---

## 4. Lifecycle at a router

![Lifecycle](images/07-cpb-lifecycle.png)

1. **Create or receive** a bundle that may carry one or more CPBs.
2. **Read** default / per-path probabilities (after trust/BIB policy).
3. **Decide** next hop using the local routing policy.
4. **Optionally update** with fresher local estimates (append or
   strip-and-replace — see draft §8).
5. **Forward**; nodes that do not understand CPB pass the block through.

---

## 5. Configuration 1 experiment

The simulator `impl/config1_sim.py` uses **Configuration 1**:

![Topology](images/04-config1-topology.png)

- 4 rovers → 4 orbiters → 1 relay → 3 grounds
- First-hop success probabilities in **[0.78, 0.96]**
- Space-side hops ~**0.99**
- Paper battery: **10 seeds**, ~**80k** bundles per arm per seed

### Routing policies (labels match draft §12)

![Policies](images/05-routing-policies.png)

| Label | Cost / rule |
|-------|-------------|
| **baseline** | Earliest predicted arrival (ignore confidence) |
| **cpb** | `latency / confidence` |

### Headline results (paper battery)

![Results](images/06-paper-battery-results.png)

**Delivery first.** Contact-window retries per hop (`R`) are a lever — not
“cpb always wins”:

| R | baseline deliv | cpb deliv | Δ delivery |
|---|----------------|-----------|------------|
| **2** (tight budget) | ≈0.9789 | ≈0.9901 | **≈+0.011** |
| **3** (draft default) | ≈0.9965 | ≈0.9984 | ≈+0.0019 |
| **4** (more retries) | ≈0.9988 | ≈0.9991 | ≈+0.0003 |

On Configuration 1, **cpb** improves **delivery** and usually **mean latency**;
**p95 is often worse** (longer-period high-confidence paths). Path confidence
is higher under **cpb**. Use small R when the traffic class values delivery
under few contact attempts; large R when absolute completion rate matters
more and extra windows are acceptable.

**Two experiment parts (draft §12.1):** (1) wire format and ION data-plane
survival of the extension block; (2) routing value of confidences of the
class CPB carries (simulator; bridge tests check that encode/decode
preserves the cost ranking).

Reproduce:

```sh
cd impl
python3 test_cpb.py
python3 test_config1_policies.py
python3 test_sim_cpb_bridge.py
python3 config1_sim.py --battery paper --strategy both
```

---

## 6. Security in one slide (draft §8)

Threats include false probabilities (sinkhole / blackhole), stale CPBs,
semi-trusted relays biasing routes, and inter-domain trust gaps.

Defaults to remember:

- Prefer **BPSec BIB** integrity on CPBs used for routing.
- **Do not** encrypt CPB with BCB if intermediates must *read* it to route.
- Unauthorized or unverifiable CPBs: prefer **strict** (ignore for routing,
  still forward) over laundering signatures.
- Multi-CPB precedence applies **after** trust verification.

---

## 7. How to read the full draft

| Sections | Content |
|----------|---------|
| §1–2 | Problem + why extension blocks |
| §3–4 | Wire format + operational semantics |
| §5–7 | Protocol fit, backwards compatibility, operations |
| §8–9 | Security + IANA |
| §10–11 | Overhead + implementation status |
| §12 | Experiment (Config 1 + ION data-plane notes) |
| §13 | Reference implementation |

---

## 8. Recap (question → answer)

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

**What cost formula does the Config 1 “cpb” policy use?**  
`cost = latency / confidence` (end-to-end path confidence product). Baseline
uses earliest arrival only and ignores confidence.

**On Config 1, what improves under cpb?**  
**Delivery** and **mean latency** improve; **p95 latency does not** (slightly
worse on this topology). Path confidence is higher under cpb.

**What remains open for Standards Track / ops?**  
Noisy or adversarial estimates, multi-domain trust, partial deployment
quality, production-stack interop, and in-band consumption by live CGR (or
similar) — listed in draft §12.11; not claimed solved by Experimental -00.

---

*Non-normative. For normative language, use the Internet-Draft.*
