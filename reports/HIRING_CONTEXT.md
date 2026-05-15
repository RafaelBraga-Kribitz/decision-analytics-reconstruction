# Hiring context — DACH role mapping

## Purpose

This document maps the three-module portfolio capabilities (population segmentation, MILP-backed allocation, Bayesian probabilistic tracking) to **specific roles at specific companies** in the DACH market (Germany, Austria, Switzerland).

It is not a generic "data scientist seeks role" pitch. It is a targeted register of where each capability in this repository creates verifiable signal for a hiring committee — written to be readable by both the candidate (to prioritize applications) and a reviewer asking "why does this person belong in our pipeline?"

For honest framing: all data is synthetic, the program context is anonymized, and the cost figures are reconstruction outputs. See [`reports/epistemic_boundaries.md`](epistemic_boundaries.md) for scope.

---

## Why DACH specifically

The DACH region is structurally over-indexed in three role families that this portfolio addresses directly:

1. **Operations research and optimization at industrial scale** — Vienna, Stuttgart, Zurich, and Munich host the European core of warehouse automation, manufacturing logistics, and supply-chain optimization. Roles routinely require MILP, simulation, and constrained-resource modeling, not just predictive ML.

2. **Regulated decision systems with reproducibility expectations** — Basel (pharma), Frankfurt (banking), Munich (insurance) hire heavily for analytics roles where the deliverable must survive audit. Versioned artifacts, schema contracts, and uncertainty quantification are not "nice-to-have" — they are mandatory for the artifact to be usable.

3. **Probabilistic forecasting under measurement uncertainty** — Climate, energy, demand, and risk roles in Berlin, Hamburg, and Zurich increasingly require Bayesian methods (PyMC, Stan) over point-estimate ML, because the decision layer needs posteriors, not predictions.

A candidate whose portfolio demonstrates all three — segmentation that feeds a constrained optimizer that feeds a probabilistic tracker, with full artifact lineage — is not common. The combination is the signal.

---

## Role family overview

| Role family | Capability hook | Key DACH employers |
|-------------|-----------------|--------------------|
| Operations Research / Optimization Engineer | Module B (MILP + duals + shadow prices) | Knapp AG, TGW Logistics, Jungheinrich, Linde, BMW Group |
| Quantitative Analyst (Risk / Capital) | Module B (FX corridor constraints + dual feasibility) | Erste Group, Raiffeisen, UBS, Credit Suisse, Deutsche Bank |
| ML / Decision Scientist (Pharma) | Module A (segmentation + propensity) + Module C (Bayesian posteriors) | Roche, Novartis, Bayer, Siemens Healthineers, Boehringer Ingelheim |
| Forecasting / Demand Planner | Module C (hierarchical Bayesian + scenario catalog) | Siemens Energy, Vestas, RWE, E.ON, Lufthansa |
| Senior Data Scientist / Analytics Engineer (General) | Three-module system with contracts + reproducibility | SAP, Zalando, N26, HelloFresh, Delivery Hero |

---

## Per-company mapping

### Knapp AG (Austria — Hart bei Graz)

**What they do:** Warehouse automation, AI-driven order picking, supply-chain optimization for retail and pharma distributors.

**Role examples:**
- Optimization Engineer (Warehouse Routing)
- Data Scientist (Demand Forecasting)
- Operations Research Specialist

**Verbatim signals from their job descriptions (paraphrased):**
- "Optimization of warehouse routing under capacity and throughput constraints"
- "Simulation of stochastic demand scenarios"
- "Cooperation with industrial engineering team on bin-allocation models"

**Portfolio mapping:**
- **Module B** is the direct analog. The MILP allocates 18 geographic units × 11 channels × 14 weeks with per-channel reach caps — structurally identical to allocating SKUs across warehouse zones × picking shifts × order priorities. The bundle-level coupling constraints are the same pattern as pick-bundle coupling at Knapp.
- **Shadow-price exports** answer the OR/IE team's question "what is the marginal cost of relaxing the cap on station 7?" — a question that any Knapp routing team asks daily.
- **Module C's Monte Carlo scenario catalog** maps to demand uncertainty propagation.

**What to say in an interview:**
> "I built a constrained allocation system with $44M [verified 2018 campaign spend] across 18 regions × 11 channels × 14 weeks. The MILP returns shadow prices for every binding constraint, so a planner can read off the marginal value of relaxing a reach cap. The structural pattern — bundle coupling, capacity constraints, dual certificates — is the same one you face when assigning picks across cells. I have a working solver, a budget sensitivity curve at 0.25×–2.0× nominal, and a transparent naive baseline that documents 58% lift on the linearized objective."

---

### TGW Logistics (Austria — Wels)

**What they do:** Intralogistics integration, automated sortation, AS/RS systems for e-commerce and fashion.

**Role examples:**
- Optimization Algorithm Developer
- Simulation Engineer
- Senior Analyst (Material Flow)

**Portfolio mapping:**
- **Module B's MILP** with PuLP solver and discrete bundle variables maps to TGW's flow-routing optimization. Same problem class: how do you allocate finite resources (conveyor belts, sortation lanes, picking arms) across competing demands?
- **Reach cap enforcement** ≈ throughput constraints per station per shift.
- **Schema-contracted parquet artifacts** signal that the candidate has worked on production-grade pipelines, not just notebooks.

**What to say in an interview:**
> "The MILP I built has 2,772 decision cells (18 × 11 × 14) plus bundle binaries. It solves in seconds with PuLP. The interesting part isn't the solve — it's the dual exports, the budget expansion curve, and the contract that the output parquet validates against. That's the pipeline architecture, not just the model."

---

### Roche (Switzerland — Basel)

**What they do:** Pharmaceutical R&D, diagnostics, personalized healthcare.

**Role examples:**
- Computational Biologist (with statistical modeling)
- Senior Data Scientist (Clinical Trial Operations)
- Bayesian Statistician (Regulatory)
- Decision Scientist (Commercial Analytics)

**Portfolio mapping:**
- **Module C's hierarchical Bayesian model** maps to clinical trial outcome modeling — house effects ↔ site effects, transparency-weighted variance ↔ site-quality-weighted variance.
- **Reproducibility framework** (versioned artifacts, schema contracts, MLflow tracking, seed manifests) is the operational hygiene that FDA/EMA submission packages require. This is harder to demonstrate in a portfolio than the model itself.
- **Module A's segmentation** maps to patient cohort stratification.

**What to say in an interview:**
> "Module C uses PyMC's NUTS sampler with a GaussianRandomWalk latent margin and per-pollster Normal offsets. The posterior is exported with HDI bands, every run produces a manifest with seed + git SHA + dependency hashes, and the diagnostics (Rhat, ESS, divergences) are documented in METHODOLOGY.md. If I were submitting an evidence package to a regulator, the artifact chain is already audit-traceable."

---

### Novartis (Switzerland — Basel)

**What they do:** Pharma — oncology, cardiovascular, immunology, neuroscience.

**Role examples:**
- Senior Statistician (Real-World Evidence)
- Data Scientist (Patient Journey Analytics)
- Quantitative Pharmacologist

**Portfolio mapping:**
- **Module A's propensity model with Platt calibration and per-department raking** maps to patient cohort enrichment and adherence prediction. The two-stage calibration (logistic + Platt + IPF rake) is the kind of multi-stage probability hygiene that real-world evidence teams need.
- **Bayesian uncertainty quantification** (Module C) is now standard for RWE submissions to EMA.

---

### Siemens Healthineers (Germany — Erlangen)

**What they do:** Medical imaging, lab diagnostics, AI-augmented diagnostic workflows.

**Role examples:**
- Senior Data Scientist (Imaging AI)
- Operations Research Engineer (Hospital Workflow)
- Bayesian Modeler (Predictive Maintenance)

**Portfolio mapping:**
- **Module B's resource allocation** maps directly to hospital scheduling: allocating MRI/CT slots × clinical priority tiers × time slots with reach caps (machine throughput, technician availability).
- **Module C's Bayesian posterior** with HDI bands matches the structure of imaging-AI confidence calibration.

---

### Erste Group (Austria — Vienna)

**What they do:** Universal banking across CEE, retail and corporate.

**Role examples:**
- Quantitative Analyst (Capital Allocation)
- Risk Modeler (IRB / Basel)
- Senior Data Scientist (CCB Analytics)

**Portfolio mapping:**
- **Module B's FX corridor constraints** (`FX_BAND_MAX_PCT_VS_BCP = 0.005`) and currency-band enforcement are the exact structure of currency-hedged capital allocation.
- **Dual feasibility reports** correspond to the regulatory pillar 2 capital sensitivity analyses (where the binding constraint informs capital add-ons).
- **Budget expansion curve at 0.25×–2.0× nominal** ≈ regulatory stress testing.

**What to say in an interview:**
> "The MILP enforces an FX corridor at ±0.5% of the BCP central rate. When the corridor binds, the dual value tells you the marginal cost of relaxing it — that's the same dual structure as the Basel III internal-models output. The sensitivity curve at 0.25×–2.0× of nominal envelope is structurally a budget-shock stress test."

---

### Raiffeisen (Austria — Vienna; Switzerland — St. Gallen)

**Role examples:**
- Quantitative Risk Analyst
- Data Scientist (Treasury / ALM)

**Portfolio mapping:** Same as Erste — FX-constrained allocation + dual feasibility + scenario sensitivity.

---

### UBS / Credit Suisse (Switzerland — Zurich)

**Role examples:**
- Quantitative Researcher (Multi-Asset)
- Risk Modeling Engineer
- Senior Data Scientist (Wealth Analytics)

**Portfolio mapping:**
- **Module B**: MILP + dual certificates ≈ portfolio optimization with KKT conditions.
- **Module C**: hierarchical Bayesian ≈ factor model with latent state + observation noise.

The vocabulary is different but the structure is identical. A candidate who can speak "shadow price" and "posterior HDI" in the same conversation maps to multi-asset quantitative research without retraining.

---

### Jungheinrich (Germany — Hamburg)

**What they do:** Forklift trucks, intralogistics, warehouse automation.

**Role examples:**
- Operations Research Engineer
- Data Scientist (Fleet Optimization)

**Portfolio mapping:** Module B (constrained allocation) + Module A (entity-scale segmentation for fleet utilization patterns).

---

### Lufthansa Group (Germany — Frankfurt, Munich)

**Role examples:**
- Senior Data Scientist (Network Planning)
- Operations Research Engineer (Crew Scheduling)
- Forecasting Specialist (Revenue Management)

**Portfolio mapping:**
- **Module B**: MILP allocation of fixed resources (slots, gates, crews) under multi-dimensional constraints.
- **Module C**: demand forecasting with hierarchical Bayesian (per-route or per-cabin segments).

---

### SAP (Germany — Walldorf)

**Role examples:**
- Senior Data Scientist (Supply Chain Cloud)
- Analytics Engineer (Predictive Maintenance)
- Decision Scientist (S/4HANA Analytics)

**Portfolio mapping:** All three modules — full-stack reproducibility, schema contracts, MLflow tracking, and CI/CD discipline are exactly what SAP looks for in analytics engineers on the SuccessFactors and Concur products.

---

### Zalando / N26 / HelloFresh / Delivery Hero (Berlin)

**Role examples:**
- Senior Data Scientist (Marketing Mix)
- ML Engineer (Production Pipelines)
- Decision Scientist (Pricing & Promotion)

**Portfolio mapping:**
- **Module A's propensity + Module B's MILP** is literally the marketing-mix modeling stack: segment customers, allocate marketing budget across channels and regions under caps, measure lift vs naive baseline.
- The DACH e-commerce stack expects production-grade pipelines, schema contracts, and CI gates. This portfolio demonstrates all three.

---

## Interview talking points (cross-role)

When a hiring manager asks "tell me about a project you're proud of," the answer should be structured:

### 1. The problem framing (30 seconds)
> "I reconstructed a national-scale resource-allocation decision system: 18 regions, 11 channels, 14 weeks, $44M envelope [verified 2018 campaign budget], polling-based outcome uncertainty. The decision question was 'where does each marginal dollar buy the most persuasion, subject to hard feasibility?' — not 'who will convert?'"

### 2. The architecture (60 seconds)
> "Three modules with contracts: Module A segments 15-50k entities into six behaviorally coherent groups and produces per-entity participation propensity. Module B is a MILP with bundle binaries, FX corridor constraints, and dual exports — it allocates the envelope and tells me which constraints are binding. Module C is a Bayesian hierarchical model with GaussianRandomWalk latent margin and per-pollster Normal offsets — it propagates measurement uncertainty into a scenario catalog. The modules hand off verified parquet artifacts; each artifact has a Pandera contract enforced at every pipeline exit."

### 3. The engineering rigor (45 seconds)
> "Every run produces a manifest with git SHA, random seeds, dependency hashes, and metric snapshots. MLflow tracks model runs. CI enforces Pyright basic mode, Black, Ruff, pytest with coverage gates (≥80% per module). Tests are structured: red-gate TDD, schema contracts, golden-path integration, plus reproducibility tests that validate metric bounds within floating-point tolerance."

### 4. The honest framing (15 seconds)
> "Data is synthetic — calibrated to census weights and TSJE participation rates, but synthetic. The dollar figures are reconstruction outputs traced through manifests, not audited cash. I'm careful to distinguish verified anchors from illustrative parameters in `epistemic_boundaries.md`."

### 5. The transferability (15 seconds)
> "The MILP backbone is the same pattern as warehouse routing or capital allocation. The Bayesian tracking is the same pattern as clinical trial outcome modeling or demand forecasting. The contracts-and-manifests discipline is the same pattern as any regulated decision system."

---

## Application strategy

### Tier 1: high-fit, high-priority

Apply within two weeks of role posting; tailor cover letter to mention the relevant module by name.

- Knapp AG — Optimization Engineer
- TGW Logistics — Simulation Engineer
- Roche — Senior Data Scientist (Clinical Trial Operations)
- Erste Group — Quantitative Analyst (Capital Allocation)
- Siemens Healthineers — OR Engineer (Hospital Workflow)

### Tier 2: structurally aligned, medium-priority

- Novartis, Bayer, Boehringer Ingelheim — RWE / Decision Science roles
- UBS, Credit Suisse — Quantitative Researcher (Multi-Asset)
- Jungheinrich, BMW, Linde — OR Engineer roles
- Lufthansa — Network Planning / Crew Scheduling
- SAP — Senior Data Scientist (Supply Chain Cloud)

### Tier 3: capability-overlap but cultural fit varies

- Zalando, N26, HelloFresh, Delivery Hero — Marketing Mix / Pricing
- Vestas, Siemens Energy, RWE, E.ON — Forecasting Specialist
- McKinsey Analytics, BCG Gamma, Bain Vector — Senior Consultant (Operations)

### Always-on filters

When scanning DACH job boards (StepStone, karriere.at, JobUp.ch, LinkedIn DACH), prioritize roles that mention:

- "Mixed-integer programming" or "MILP" or "MIP" or "constraint programming"
- "Bayesian" or "PyMC" or "Stan" or "probabilistic programming"
- "Operations research" or "OR"
- "Reproducibility" or "MLOps" or "ML pipelines"
- "Schema contracts" or "data contracts"
- "Optimization under uncertainty"

De-prioritize roles that are pure "predict X" without a decision layer — the portfolio's signal is wasted there.

---

## Honest caveats for the hiring committee

A reviewer will (and should) ask:

**"Was this real work?"**
> The data is synthetic, calibrated to public Paraguay TSJE 2018 participation rates and BCP FX series. The architecture and engineering discipline are real. The dollar figures, entity counts, and persuasion contacts are reconstruction outputs — plausible magnitudes traced through manifests, not cash that moved. The reconstruction is honest about its scope; see `epistemic_boundaries.md`.

**"Why three modules instead of one?"**
> The problem class is not single-model: it's decision-making under heterogeneity, constraints, and measurement uncertainty. Each module addresses one of the three; they hand off via verified artifacts. Compressing them into a single model would hide the decision interfaces — exactly the interfaces a CFO or OR team needs to inspect.

**"Did you actually solve the MILP, or just describe it?"**
> The solver runs (`make module-b-allocate SEED=20180422`). The manifest, parquet outputs, and dual exports are checked in. The 58% lift vs naive baseline is reproducible from a fresh clone.

**"What would you do differently with more time?"**
> (1) Replace the synthetic propensity labels with a real adherence cohort if I had access; (2) add a nonlinear naive baseline so the persuasion lift is comparable on the diminishing-returns curve, not only the linearized one; (3) extend Module C to a multi-candidate Dirichlet rather than two-party margin.

---

## Resources

- [`reports/business_case.md`](business_case.md) — CFO-readable framing with glossary
- [`reports/competitive_positioning.md`](competitive_positioning.md) — why this portfolio is structurally different
- [`reports/epistemic_boundaries.md`](epistemic_boundaries.md) — verified vs simulated vs illustrative
- [`reports/reproducibility_validation.md`](reproducibility_validation.md) — fresh-clone validation procedure
- [`module_c_forecasting_scenarios/METHODOLOGY.md`](../module_c_forecasting_scenarios/METHODOLOGY.md) — Bayesian model specification

---

*This document is a portfolio-positioning aid, not a job application. It exists to help the candidate prioritize where to spend application effort, and to help a hiring committee parse the portfolio in their own vocabulary.*
