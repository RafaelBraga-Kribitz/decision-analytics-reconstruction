---
doc_id: DOC-REP-011
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Statistical Note: Synthetic Data Independence Assumptions

**Scope:** Module A synthetic population generation
**Audience:** Technical reviewers; any consumer of `population_master_clean.parquet`
**Status:** Known limitation, documented and bounded

---

## The limitation

The Module A synthetic generator produces individual-level population attributes using **conditional probability draws**: each field is drawn conditionally on a small set of parent fields, but the joint distribution of all 14 modeling features is not explicitly specified or validated.

In practice, the generator enforces:

1. **Department assignment** — from verified TSJE electoral roll weights (sum = 1.0).
2. **Rural flag** — raked to DGEEC 38.3% rural share via binary bit-flipping (marginal correct).
3. **Language bucket** — raked to DGEEC bilingualism marginals via categorical raking (marginal correct).
4. **Gender** — drawn from DGEEC gender shares (marginal correct).
5. **Age** — drawn from a department-stratified age distribution calibrated to TSJE youth cohort anchor.
6. **Internet access** — drawn conditionally on `rural_flag` (urban 73.4%, rural 27.9%).
7. **NBI stress** — drawn conditionally on `rural_flag` and `department`.
8. **Structural dependency** — drawn conditionally on `rural_flag` and `department`.

**What is not enforced:** Higher-order joint dependencies between these fields. For example:

- The generator does not enforce that rural Jopará-bilingual youth have a specific NBI stress distribution that differs from rural Spanish-only youth of the same age.
- The correlation between `internet_access_flag` and `language_census_bucket` is not validated against any national survey.
- The joint distribution of `structural_dependency_proxy × age × rural_flag` is not validated against DGEEC household surveys.

---

## Why this matters

For **segmentation:** K-Means clusters in the 14-feature space will reflect the correlation structure of the synthetic data, not the real population. If real correlations are stronger or weaker than the synthetic ones, the segment boundaries — and their propensity profiles — will differ from what a real-data model would produce.

For **propensity model:** The logistic regression coefficient on, e.g., `rural_offline_compound` is calibrated to the synthetic joint distribution. If the real rural × offline × structural dependency correlation is stronger, the model would underweight this compound signal.

For **calibration:** All nine national-level calibration anchors (participation rate, youth rate, gender rates, etc.) are marginal checks. The model can pass all marginal checks while having a miscalibrated joint structure.

---

## What is validated

The following are directly enforced:

| Check | Tolerance | Source |
|-------|-----------|--------|
| National participation rate mean | ±0.1 pp | TSJE 2018 |
| Rural population share | ±0.3 pp | DGEEC 2018 |
| Language marginals (3 buckets) | ±1 pp each | DGEEC bilingualism |
| Gender marginals | ±0.2 pp | DGEEC 2018 |
| Youth cohort count and rate | ±1% count, ±0.5 pp rate | TSJE 2018 |
| Departmental participation rates (4 verified) | ±0.5 pp | TSJE 2018 |
| Internet penetration (urban/rural) | ±2 pp | ICT survey ~2018 |

These are checked at every pipeline run by `evaluation/validator.py`.

---

## What is not validated (and the consequence)

| Joint distribution | Real-world consequence of error |
|---------------------|--------------------------------|
| Language × rural × age | Rural young Guaraní-speakers may be over- or under-represented in the Youth Volatile segment |
| NBI stress × department × urban-rural | Structurally Dependent segment composition may not match real geographic concentration |
| Internet access × language × age | Digital reachability scores may be miscalibrated for specific strata combinations |

The consequence is **segmentation boundary uncertainty**: the six segment labels are operationally correct in their marginal profiles, but their joint-feature boundaries may not be stable if the data-generating process were swapped to real TSJE microdata.

---

## Recommended mitigation (upgrade path)

1. **Correlation validation artifact:** Draw a random sample of 10k synthetic entities. Compute the Spearman correlation matrix across the 14 modeling features. Compare selected pairwise correlations against published DGEEC household survey microdata (available for download from the DGEEC website) for the overlapping variables. Flag deviations > 0.15 Spearman rank correlation units.

2. **Copula-based generation:** Replace the independent conditional draws for the six synthetic fields above with a Gaussian copula that preserves the observed correlation structure from the DGEEC household survey for the variables that overlap. This does not change the marginal distributions (already calibrated) but would enforce realistic joint structure.

3. **Sensitivity analysis on segment composition:** Re-run segmentation under ±20% perturbations of the internet penetration parameters to assess how sensitive the Youth Volatile / Rural Committed boundary is to the internet access assumptions.

These mitigations are out-of-scope for the current reconstruction but are documented here so that any consumer of the segmentation outputs can assess the operational risk from the independence assumption.

---

## Honest framing for interviewers

The synthetic population is **calibrated at the margins** — every available verified anchor is enforced. The independent-draws assumption is a design choice, not an oversight. In a real engagement with access to TSJE microdata and DGEEC household survey overlaps, the joint structure would be validated against actual correlations. The reconstruction demonstrates the methodology for doing so; the correlation validation step is the natural next artifact to produce.
