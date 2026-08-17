# Probabilistic Contact Metadata for DTN Bundle Routing

Contact Probability Block (CPB): a BPv7 extension block that carries
per-contact probability metadata in-bundle so delay-tolerant routers can
use confidence-weighted forwarding without rewriting endpoint identifiers.

- **Draft:** [`draft-perry-dtn-cpb-00`](draft-perry-dtn-cpb.xml)
  ([txt](draft-perry-dtn-cpb.txt) · [html](draft-perry-dtn-cpb.html) ·
  [pdf](draft-perry-dtn-cpb.pdf))
- **Status:** pre-submission review copy. Not posted to the IETF
  Internet-Drafts repository.
- **Quick reference:** [`docs/CPB-QUICK-REFERENCE.md`](docs/CPB-QUICK-REFERENCE.md)
  (diagrams under `docs/images/`)

## Building the draft

```sh
make
```

Produces `draft-perry-dtn-cpb.txt`, `draft-perry-dtn-cpb.html`, and
`draft-perry-dtn-cpb.pdf` from the XML source via xml2rfc. The `lib/`
i-d-template submodule is initialized on first `make`, or run
`git submodule update --init`.

If `python3 -m venv` / `ensurepip` fails on your system, see
`scripts/ensure-template-venv.sh` and the bootstrap logic in the top-level
`Makefile`.

## Reference implementation

[`impl/`](impl/) contains the CPB encoder/decoder (draft §3), conformance
tests, and the discrete-event simulator used for the Configuration 1 results
in draft §12.5. ION data-plane artifacts live under
`impl/real-pwg-deployment/` and `impl/real-cpb-ion-test/`.

### Quick start

From the repository root:

```sh
cd impl
pip install -e '.[test]'
python3 test_cpb.py
python3 test_config1_policies.py
python3 test_sim_cpb_bridge.py
python3 test_draft_consistency.py
python3 config1_sim.py --quick
python3 config1_sim.py --battery paper --strategy both
```

Alternative (also from the repository root):

```sh
pip install -r impl/requirements.txt
python3 impl/test_cpb.py
python3 impl/config1_sim.py --quick
```

Useful simulator options (from `impl/`):

```sh
python3 config1_sim.py --help
python3 config1_sim.py --strategy cpb --csv results.csv
python3 config1_sim.py --max-bundles 8000 --quick
```

Policy labels (draft §12):

| Label | Rule |
|-------|------|
| **baseline** | Earliest predicted arrival; confidence ignored |
| **CPB** | `cost = latency / confidence` |

**Delivery is primary.** Hop-retry budget `R` (`--hop-retries` /
`--sweep-hop-retries`) is a lever, not a claim that CPB wins every axis:

| R | baseline deliv | CPB deliv | Δ delivery | notes |
|---|----------------|-----------|------------|--------|
| 2 | ≈0.9789 | ≈0.9901 | **≈+0.011** | tight contact budget — larger CPB delivery edge |
| 3 | ≈0.9965 | ≈0.9984 | ≈+0.0019 | draft §12.5 / default |
| 4 | ≈0.9988 | ≈0.9991 | ≈+0.0003 | ceiling — absolute delivery high, gap shrinks |

Mean latency usually improves under **CPB**; **p95 often does not**. Use
tighter R when delivery of certain traffic matters more than waiting for
extra windows. Parallel paper sweep:  
`python3 impl/config1_sim.py --battery paper --strategy both --sweep-hop-retries 2,3,4`

## License

- Code in [`impl/`](impl/): [MIT](LICENSE)
- Draft text: see BCP 78 / Trust Legal Provisions as applied to the document
