<p align="center">
  <img
    src="docs/assets/decision-analytics-reconstruction-hero-banner.png"
    alt="Decision Analytics Reconstruction — evidence, estimation, and uncertainty across population segmentation, resource allocation, and probabilistic scenario analysis"
    width="100%"
  />
</p>

# Decision Analytics Reconstruction

Retrospective reconstruction of a national-scale decision analytics system for
population modeling, constrained resource allocation, and probabilistic scenario
analysis.

[![CI](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml)
[![Governance](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/governance.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/governance.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](.python-version)

All three modules run locally in two commands (see Quick Start). Hosted demos
are tracked as open finding `F-021` and will be linked here only once they
return HTTP 200 from CI — this README does not claim deployments that are not
live.

## Source Of Truth

The project authority is `PROJECT_CHARTER.md`. Governance, findings, ADRs, and
session handoffs live under `governance/`. Start AI-assisted work with:

```bash
make session-start
```

## What This Repository Contains

- `module_a_population_segmentation/`: population dataset generation, cleaning,
  segmentation, participation propensity modeling, and Streamlit dashboard.
- `module_b_resource_allocation/`: constrained allocation, routing support,
  budget sensitivity, and FastAPI service.
- `module_c_forecasting_scenarios/`: survey measurement aggregation, Bayesian
  tracking, scenario simulation, and Quarto reporting.
- `schema_contracts/`: versioned artifact contracts for module boundaries.
- `docs/registry/`: machine-readable documentation inventory (internal metadata; no per-file YAML headers).

## Quick Start

```bash
poetry install
make test

# Local demos
make dashboard       # Module A — Streamlit dashboard
make module-b-api    # Module B — FastAPI service (docs at http://127.0.0.1:8088/docs)
make module-c-all    # Module C — forecasting artifacts
```

For deployment, read `docs/DEPLOYMENT.md`. For architecture, read
`ARCHITECTURE.md`. For governance, read `governance/AUDIT_PROCEDURE.md`.

## Status

This branch is replacing the previous local planning harness with a tracked
findings-and-ratchet governance system. Known inherited test/lint failures are
recorded in the session notes and will be promoted to findings where relevant.
