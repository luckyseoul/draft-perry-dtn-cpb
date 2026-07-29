# Probabilistic Contact Metadata for DTN Bundle Routing

<p align="center">
  <img src="logo.png" alt="DTN CPB routing" width="168" />
</p>

Individual Internet-Draft defining the Contact Probability Block (CPB): a
BPv7 extension block that carries per-contact probability metadata in-bundle
so delay-tolerant routers can use confidence-weighted forwarding without
rewriting endpoint identifiers.

- **Draft:** `draft-perry-dtn-cpb-00` (Experimental) — GitHub working copy;
  not yet filed on the IETF Internet-Drafts repository. The rendered
  **Expires** line is xml2rfc boilerplate (document date + 6 months), not a
  datatracker clock.
- **Quick reference:** [`docs/CPB-QUICK-REFERENCE.md`](docs/CPB-QUICK-REFERENCE.md)
  — short catch-up (why / what / how + diagrams) so a reader can grasp the
  concept without working through the full Internet-Draft first. Non-normative;
  diagrams under `docs/images/`.

## Building the draft

```sh
make
```

Produces `draft-perry-dtn-cpb.txt` and `draft-perry-dtn-cpb.html` from the XML
source via xml2rfc. The `lib/` i-d-template submodule is initialized on first
`make`, or run `git submodule update --init`.

If `python3 -m venv` / `ensurepip` fails on your system, see
`scripts/ensure-template-venv.sh` and the bootstrap logic in the top-level
`Makefile`.

## Reference implementation

[`impl/`](impl/) contains the CPB encoder/decoder (draft §3), conformance
tests, and the discrete-event simulator used for the Configuration 1 results
in draft §12.5. PWG ION data-plane artifacts live under
`impl/real-pwg-deployment/` and `impl/real-cpb-ion-test/`.

### Quick start

```sh
cd impl

pip install -e '.[test]'

# Conformance and honesty checks
python3 test_cpb.py
python3 test_config1_policies.py
python3 test_sim_cpb_bridge.py
python3 test_draft_honesty.py

# Fast sim smoke test (baseline + cpb)
python3 config1_sim.py --quick

# Paper battery (10 seeds; matches draft §12.5)
python3 config1_sim.py --battery paper --strategy both
```

Alternative:

```sh
pip install -r requirements.txt
python3 test_cpb.py
python3 config1_sim.py --quick
```

Useful simulator options:

```sh
python3 config1_sim.py --help
python3 config1_sim.py --strategy cpb --csv results.csv
python3 config1_sim.py --max-bundles 8000 --quick
```

Policy labels (draft §12):

| Label | Rule |
|-------|------|
| **baseline** | Earliest predicted arrival; confidence ignored |
| **cpb** | `cost = latency / confidence` |

**Delivery is primary.** Hop-retry budget `R` (`--hop-retries` /
`--sweep-hop-retries`) is a lever, not a claim that cpb wins every axis:

| R | baseline deliv | cpb deliv | Δ delivery | notes |
|---|----------------|-----------|------------|--------|
| 2 | ≈0.9789 | ≈0.9901 | **≈+0.011** | tight contact budget — larger cpb delivery edge |
| 3 | ≈0.9965 | ≈0.9984 | ≈+0.0019 | draft §12.5 / default |
| 4 | ≈0.9988 | ≈0.9991 | ≈+0.0003 | ceiling — absolute delivery high, gap shrinks |

Mean latency usually improves under **cpb**; **p95 often does not**. Use
tighter R when delivery of certain traffic matters more than waiting for
extra windows. Parallel paper sweep:  
`python3 impl/config1_sim.py --battery paper --strategy both --sweep-hop-retries 2,3,4 --workers 86`

## License

- Reference code in [`impl/`](impl/): [MIT](LICENSE)
- Draft text: IETF Trust Legal Provisions (BCP 78)

`CONTRIBUTING.md` is the standard IETF template for contributions that enter
the IETF standards process. Repository code remains MIT-licensed under
`LICENSE`.
