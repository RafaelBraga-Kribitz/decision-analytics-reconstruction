<p align="center">
  <img
    src="docs/assets/decision-analytics-reconstruction-hero-banner.png"
    alt="Decision Analytics Reconstruction — evidence, estimation, and uncertainty across population segmentation, resource allocation, and probabilistic scenario analysis"
    width="100%"
  />
</p>

# Decision Analytics Reconstruction

Retrospective reconstruction of a national-scale decision analytics system:
population modeling, constrained resource allocation, and probabilistic scenario
analysis — wired as a single reproducible pipeline with governance ratchets.

[![CI](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/ci.yml)
[![Governance](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/governance.yml/badge.svg)](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction/actions/workflows/governance.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](.python-version)

Hosted demo availability is governed by finding **F-021** and its verification
script (`scripts/check_live_deployment_urls.py`) — this README does not claim
URLs that the script has not verified live. Free-tier hosts sleep; if a demo is
down, F-021 has regressed and must be reopened.

## Three differentiators

1. **Honest epistemic layering** — Every artifact is tagged verified / calibrated /
   simulated / illustrative (`reports/epistemic_boundaries.md`). Headline numbers
   live in one SSOT table (`reports/NUMERIC_SSOT.md`); golden metrics are CI-gated.

2. **End-to-end wiring, not slide-ware** — `make pipeline-full` runs Module A → B
   → C with the allocation parquet handshake enforced (F-040). Monte Carlo draws
   fail loudly when B→C contacts are zero.

3. **Governance-as-code** — Findings YAML + adversary verification scripts
   (`make verify`) replace narrative “audit complete” claims. One finding per PR;
   regressions reopen closed items automatically.

## Verified anchors (Series A)

| Quantity | Value |
|---|---|
| Outcome margin | **+3.70 pp** (46.43% vs 42.73%) |
| Turnout | **61.25%** |
| Production run scale | **50,000** voters (4.26M design reference) |
| Campaign window | **14 weeks** |

Full table: [`reports/NUMERIC_SSOT.md`](reports/NUMERIC_SSOT.md).

## Skills evidence (what reviewers can run)

| Skill / claim | Evidence in repo |
|---|---|
| Segmentation + propensity | Module A pipeline, silhouette/ARI/Brier CI gates |
| MILP under real constraints | Module B OPTIMAL baseline, 80% coverage floor |
| Bayesian tracking + MC scenarios | Module C PyMC models, walk-forward estimand fix (F-034), leave-one-wave-out out-of-sample scoring on the 8 real tracking waves (`reports/module_c_lowo_metrics.json`; n=8 caveat, see `reports/VALIDATION.md` §Module C) |
| Pipeline integration | `dvc.yaml`, `make pipeline-full`, `tests/test_golden_metrics.py` |
| Statistical honesty | AUC circularity documented; no causal counterfactual fiction |
| Reproducibility | `make test`, `scripts/generate_golden_metrics.py`, fresh-clone path in CONTRIBUTING |

Case narrative: [`reports/CASE_STUDY.md`](reports/CASE_STUDY.md). Validation gates:
[`reports/VALIDATION.md`](reports/VALIDATION.md).

## Quick start

```bash
poetry install
make test

# Full integrated pipeline (A → B → C → EDA)
make pipeline-full

# Local demos
make dashboard       # Module A — Streamlit
make module-b-api    # Module B — FastAPI (http://127.0.0.1:8088/docs)
make module-c-all    # Module C — forecasting artifacts
```

## Modules

| Module | Role | Entry |
|---|---|---|
| **A** | Population dataset, segmentation, participation propensity | `module_a_population_segmentation/` |
| **B** | Constrained allocation MILP + routing | `module_b_resource_allocation/` |
| **C** | Survey aggregation, Bayesian tracking, MC scenarios | `module_c_forecasting_scenarios/` |

Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md). Contracts: `schema_contracts/`.

## Governance

AI-assisted work starts with:

```bash
make session-start   # → governance/SESSION_HANDOUT.md
```

Authority: `PROJECT_CHARTER.md`, `governance/AUDIT_PROCEDURE.md`, `governance/findings/`.

## Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Live URL verification: finding **F-021**
(human platform auth required).

## Author

<table>
  <tr>
    <td width="110">
      <img
        src="docs/assets/Author_MDS_Rafael_Braga-Kribitz_kroped.png"
        alt="Rafael Braga-Kribitz"
        width="96"
      />
    </td>
    <td>
      <strong>Rafael Braga-Kribitz</strong><br />
      Seiersberg-Pirka, Austria · Portfolio project, 2026<br />
      <a href="https://www.linkedin.com/in/rafaelbragakribitz/">LinkedIn</a>
      ·
      <a href="mailto:rafaelbragakribitz@gmail.com">rafaelbragakribitz@gmail.com</a>
    </td>
  </tr>
</table>
