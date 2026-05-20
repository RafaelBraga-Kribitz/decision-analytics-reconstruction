---
doc_id: DOC-BIZ-004
doc_type: narrative
doc_role: derived
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source:
- DOC-BIZ-001
derived_from:
- DOC-BIZ-001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
- novel_claims
---

# Competitive positioning — why this portfolio stands apart

## The typical data science portfolio

Most data science portfolios follow a recognizable pattern: a churn-prediction model, a recommendation engine, or a price-elasticity analysis. These projects demonstrate solid ML fundamentals — feature engineering, cross-validation, an ROC curve — but they share a structural ceiling.

A churn model answers one question ("will this customer leave?") using one model (logistic regression or gradient boosting) producing one output (a probability score). The business logic is implicit: whoever scores below 0.3 gets an email. The system boundary stops at the CSV export.

A recommendation engine is richer, but the optimization objective is usually implicit too: maximize click-through rate, minimize regret under a bandit policy. The constrained-resource problem — "we have a fixed budget, hard capacity limits, and uncertainty about outcomes; allocate across 18 regions and 11 channels over 14 weeks simultaneously" — almost never appears in a solo-project portfolio.

## What this portfolio does differently

This reconstruction addresses three coupled problems that rarely appear together in portfolio work:

### 1. Population heterogeneity at entity scale

Module A segments 15 000–50 000 synthetic entities into six behaviorally and demographically coherent groups, then computes per-entity participation propensity via a calibrated logistic regression with department-level rake multipliers. The output is not a model card; it is a verified parquet artifact (`participation_propensity.parquet`) with schema contracts enforced at every pipeline exit, MLflow-logged metrics (silhouette = 0.52+, AUC-ROC = 0.81+), and a reproducible seed-43 manifest.

A churn portfolio produces a confusion matrix. This portfolio produces a segmentation that feeds directly into the constraint matrix of a downstream optimizer.

### 2. Constrained resource allocation under hard feasibility rules

Module B allocates a $6 000 000 USD envelope across 18 geographic units, 11 reach channels, and 14 ISO weeks using a Mixed-Integer Linear Program (PuLP solver) with:

- Per-channel, per-region reach caps derived from census-calibrated population estimates
- BCP-aligned FX corridor constraints (Guaraní/USD band)
- Bundle-level coupling that prevents fractional channel commitments
- Shadow-price transparency: every binding constraint exports a dual value so a CFO can read off the marginal cost of relaxing each cap

The result is not "we allocated the budget"; it is an allocation with dual certificates, a sensitivity curve at 25 %–200 % of nominal budget, and a 58 % lift over a transparent naive baseline on the linearized persuasion-per-USD objective.

No churn model or recommendation engine in a typical DS portfolio ships a dual feasibility report.

### 3. Probabilistic measurement under systematic bias

Module C ingests survey measurements from multiple polling firms, models firm-specific house effects using a Bayesian hierarchical model (PyMC, Gaussian random walk on the latent preference margin), and outputs a daily posterior distribution with HDI bands. The system does not pick a single "best poll"; it quantifies disagreement and propagates uncertainty through to the scenario catalog.

This is the difference between "we read the polls" and "we have a posterior over the true preference margin with 90 % credible intervals".

## Quantified comparison

| Dimension | Typical DS portfolio | This portfolio |
|-----------|---------------------|----------------|
| Problem scope | Single-model, single-output | Three-module system with inter-module data contracts |
| Optimization | Implicit (email whoever scores low) | Explicit MILP with dual feasibility and shadow prices |
| Uncertainty handling | Confidence interval on predictions | Bayesian posterior with HDI; Monte Carlo scenario catalog |
| Coverage gate | Ad hoc or none | Module A: 80 %+, Module B: 80 %+, Module C: 81 %+ |
| Reproducibility | Seed in notebook | Full manifest: git SHA, seeds, artifact hashes, MLflow run |
| CI discipline | GitHub Actions lint/test | Pyright basic mode, Black, Ruff, pytest, coverage gate per module |
| Typical reviewer question answered | "Can it predict X?" | "What is the marginal value of relaxing constraint Y?" |

## Relevance to the DACH market

Austria, Germany, and Switzerland are disproportionately rich in operational analytics roles where this combination of skills matters directly.

**Logistics and manufacturing (Knapp AG, TGW Logistics, Jungheinrich):** Job descriptions at Knapp AG explicitly request "optimization of warehouse routing under capacity and throughput constraints" and "simulation of stochastic demand scenarios." Module B's MILP backbone and Module C's Monte Carlo scenario catalog map directly onto these requirements. A candidate who has built a constrained allocation system with dual exports and sensitivity analysis speaks the same language as the OR/IE teams at these companies.

**Pharma and medtech (Roche, Novartis, Siemens Healthineers):** Clinical trial resource planning, patient cohort segmentation, and regulatory evidence-package reproducibility all share the same structural requirements as this project: versioned artifacts, schema contracts, uncertainty quantification, and auditable pipeline steps. A candidate who can explain the difference between a point estimate and a posterior distribution — and who has implemented both with tested code — is immediately credible in this context.

**Financial services (Erste Group, Raiffeisen, UBS):** Constrained capital allocation under FX exposure is the daily work of quantitative analysts. Module B's FX band constraints and dual feasibility exports are not a portfolio prop; they are the exact structure of a currency-hedged allocation problem.

## The rarest signal

Most DS portfolios demonstrate that the candidate can train a model. This portfolio demonstrates that the candidate can:

1. Define a decision problem with hard constraints and an optimization objective
2. Build three modular components that hand off verified artifacts to each other
3. Quantify uncertainty and propagate it through to the decision layer
4. Instrument the system for reproducibility, auditability, and live inspection (`make pipeline-dev`, `poetry run mlflow ui`)

The DACH hiring market, particularly at operational scale (logistics routing, production planning, regulatory submissions), values this combination over any single model's AUC improvement. It is, simply, rarer.

---

*This document was written for portfolio-review purposes. All cost figures and entity counts are reconstruction outputs from synthetic data; see `reports/epistemic_boundaries.md` for scope boundaries.*
