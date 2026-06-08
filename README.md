# Decision Analytics Reconstruction

Retrospective reconstruction of a national-scale decision analytics system for
population modeling, constrained resource allocation, and probabilistic scenario
analysis.

[![CI](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml)
[![Module A Dashboard (Render)](https://img.shields.io/badge/Module_A-Streamlit_Dashboard-brightgreen)](https://decision-analytics-module-a.onrender.com)
[![Module B API (Railway)](https://img.shields.io/badge/Module_B-FastAPI_Docs-brightgreen)](https://decision-analytics-module-b.up.railway.app/docs)
[![Module C Report](https://img.shields.io/badge/Module_C-Quarto_Report-blue)](https://RafaelBraga-Kribitz.github.io/decision-analytics-reconstruction/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](.python-version)

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
make dashboard
```

For deployment, read `docs/DEPLOYMENT.md`. For architecture, read
`ARCHITECTURE.md`. For governance, read `governance/AUDIT_PROCEDURE.md`.

## Status

This branch is replacing the previous local planning harness with a tracked
findings-and-ratchet governance system. Known inherited test/lint failures are
recorded in the session notes and will be promoted to findings where relevant.
