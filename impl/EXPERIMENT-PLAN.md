# Planned experimental evaluation

Status: planned only. Execution requires a separate author decision. This
repository reports no experimental results or demonstrated routing benefits.
Experimental scaffolding is retained in `impl/`.

- Compare matched routing configurations with and without CPB consumption.
  Define contact uncertainty, traffic, resource limits, and random seeds
  before execution. Measure delivery ratio, delay, transmissions, and cost.
- Vary estimate accuracy, age, missing data, and update frequency. Examine
  stability and local fallback under stale or misleading metadata.
- Plan interoperability checks across independent BPv7 implementations,
  including legacy nodes, multiple CPBs, authentication, and fragmentation.
- Specify sample sizes, analysis methods, and acceptance criteria in advance.
  Report configurations, versions, uncertainty, and unsuccessful outcomes.

`config1_sim.py` is preliminary local scaffolding. `test_cpb_validation.py`
checks malformed input and schema constraints and is included in CI and
`make test`. Neither file supplies results for the planned routing or
interoperability experiments.
