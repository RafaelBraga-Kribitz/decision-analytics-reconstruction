---
id: IMP-C05
title: "Battleground/geo uncertainty integrity: evidence-based sigma, disclosed circularity, intervals on the chart"
absorbs: [C7, C8, V2]
overlaps_triage: [AUD-XCUT-005]
priority: P1
effort: high
depends_on: [IMP-C01, IMP-C02]
soft_depends_on: [IMP-V01]
queue: dual
target_repo: decision-analytics-reconstruction
issue: 63
status: draft
---

# IMP-C05 — Battleground / Geo Uncertainty Integrity

The department-level win-probability product has three linked integrity
defects:

1. **Appearance-calibrated noise (C7).**
   `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/geo/heatmap.py:36-40`
   sets `_SIGMA_IDIO_PP = 1.5` with the comment "calibrated to give
   ~15–20 pp HDI width for swing departments at typical national posterior
   widths" — the parameter controlling how uncertain every department looks
   was tuned to produce a target visual width, not derived from historical
   department-level poll-vs-result residual variance.
2. **Undisclosed double circularity (C8).** `_swing_factors`
   (`heatmap.py:76-93`) is computed from the realized
   `tsje_2018_department_results.csv`, then multiplied (`heatmap.py:131`)
   against a national posterior that is itself softly anchored to the same
   verified outcome (`config/calibration.yaml`: `use_outcome_anchor: true`,
   `outcome_anchor_sigma_pp: 0.5`; `models/tracking/hierarchical.py:140-149`).
   The retrodiction framing is honestly documented in
   `hierarchical.py:108-116`, but neither
   `schema_contracts/battleground_department_probability.yaml` nor the
   report caption discloses that the department probabilities consume outcome
   data at two separate points.
3. **Uncertainty dropped from the primary chart (V2).**
   `portfolio/quarto/post_mortem.qmd:307-336` renders the department bar
   chart from the point estimate `win_probability_a` alone on a
   red-yellow-green diverging scale; the computed HDI
   (`heatmap.py:139-140`, exported as `hdi_low`/`hdi_high` GeoJSON
   properties, `heatmap.py:180-190`) appears only as hover metadata on the
   separate choropleth (`post_mortem.qmd:353`). The chart most likely to be
   quoted in isolation communicates false precision. This is also the root
   of triage row AUD-XCUT-005 (national near-certainty vs department coin
   flips reads as incoherent when intervals are invisible).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `_SIGMA_IDIO_PP` replaced by a value estimated from historical
  department-level residual variance (2018 department results vs
  contemporaneous polling, or an equivalent documented reference), with the
  estimation recorded; if no defensible estimate is achievable, the parameter
  and every artifact it touches are explicitly downgraded to `illustrative`
  in schema and captions.
- Circularity disclosure in the output contract:
  `schema_contracts/battleground_department_probability.yaml` gains
  provenance fields/description noting (a) outcome-anchored national
  posterior and (b) outcome-derived swing factors; the report caption states
  the same in one sentence.
- Optionally (preferred): a published **unanchored companion table** — the
  same pipeline run with `use_outcome_anchor: false` — so readers can see
  forecast-mode vs retrodiction-mode department probabilities side by side.
- The primary department chart draws the interval: each bar carries its
  HDI whiskers/band; the color scale becomes colorblind-safe (per IMP-V01's
  shared palette once available).

**Out-of-Scope:**
- The national model's convergence and anchoring mechanics (IMP-C01;
  anchoring policy itself was settled by F-055/F-056 and stays as-is).
- φ→σ_obs observation-noise construction (IMP-C02).
- The Quarto report's hardcoded diagnostics table and stale narrative
  (IMP-C03 — which depends on this document because the methodology table
  must describe the post-remediation geo model).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Evidence-based idiosyncratic sigma (Happy Path)**
- **Given** the historical reference set of department-level polling errors
  (per-department |poll-implied margin − realized margin| for the reference
  election(s)),
- **When** the geo pipeline computes department distributions,
- **Then** the idiosyncratic sigma used equals the documented estimator's
  output (recorded in the run manifest with dataset hash and method), and
  the resulting per-department HDI widths follow from the estimate — not
  from a width target.

**Scenario: Contract-level circularity disclosure (Happy Path)**
- **Given** `battleground_department_probability.yaml`,
- **When** a consumer (Module B, dashboard, report) reads the contract,
- **Then** the contract's description declares the two outcome-data entry
  points (anchored posterior; outcome-derived swing factors) and labels the
  estimand `retrodiction` — a consumer cannot read the schema and believe
  this is an out-of-sample forecast.

**Scenario: Interval on the quoted chart (Happy Path)**
- **Given** the department win-probability bar chart in the Quarto report,
- **When** it renders for any department,
- **Then** the bar carries its `hdi_low`–`hdi_high` interval visually (not
  hover-only), and a department whose HDI spans 0.5 is visually
  distinguishable as uncertain rather than colored as a confident win/loss.

**Scenario: Unanchored companion run (Edge Case)**
- **Given** the same input data with `use_outcome_anchor: false`,
- **When** the geo pipeline runs,
- **Then** it completes and publishes the companion table; departments whose
  win-probability classification (>0.5 vs <0.5) flips between anchored and
  unanchored runs are listed in the companion artifact — the anchored table
  must not be the only published view.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing calibration-to-appearance**
- **Given** any dispersion/uncertainty parameter in the geo pipeline,
- **When** its value is set or changed,
- **Then** the justification recorded may never be a target visual property
  ("gives ~X pp width", "looks reasonable"); a parameter without a
  data-derived or hypothesis-ledger justification fails review.

**Scenario: Preventing false-precision excerpts**
- **Given** any exported artifact (PNG, GeoJSON, CSV, dashboard tab) carrying
  department win probabilities,
- **When** it is produced,
- **Then** it must carry the interval columns/encodings and the
  retrodiction label; producing a point-estimate-only excerpt of this
  product is a failing state for the verification layer.

**Scenario: Preventing silent re-anchoring**
- **Given** the companion unanchored artifact,
- **When** any future change causes the anchored and unanchored tables to
  become byte-identical (i.e., the "unanchored" run silently consumed the
  anchor),
- **Then** the verification script fails — the two configurations must
  provably diverge on the fixture.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** department-level treatment must be uniform — no
  department may receive a bespoke sigma or manual probability adjustment
  outside the documented estimator.
- **Performance & decay:** the geo stage (both anchored and companion
  unanchored runs) must complete within the existing pipeline budget
  (< 5 min combined under `MC_FAST`); the companion run may reuse the
  national posterior draws rather than resampling.
- **Data integrity:** the contract gains bounds — `win_probability_a`,
  `hdi_low`, `hdi_high` ∈ [0,1] with `hdi_low ≤ win_probability_a ≤
  hdi_high`; violations abort the export (enforced by the IMP-C07 validator
  once available, and by the geo exporter's own assertion until then).
- **Reproducibility:** with seed 42 and identical inputs, department
  probabilities are identical across runs; the run manifest records the
  sigma estimator inputs' hash.

## 5. Queue Stub (ready to file)

This is a `dual` document. The **finding** owns the undisclosed-circularity
slice (a published schema/artifact misrepresents its estimand — governance
class). The **issue** owns the redesign slice (sigma estimation, companion
run, chart interval).

**Finding YAML:**

```yaml
id: F-XXX            # assigned at filing time
title: "Battleground department probabilities consume outcome data twice without contract disclosure"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: <filing date>
closed_at: null
recurrence_count: 0
evidence: |
  geo/heatmap.py:76-93 derives swing factors from the realized
  tsje_2018_department_results.csv; heatmap.py:131 multiplies them by a
  national posterior that is outcome-anchored (config/calibration.yaml
  use_outcome_anchor: true, sigma 0.5pp; hierarchical.py:140-149). The
  retrodiction framing is documented in hierarchical.py:108-116 but
  schema_contracts/battleground_department_probability.yaml and the
  post_mortem.qmd captions do not disclose either outcome-data entry point.
  Downstream consumers can read the schema and mistake retrodiction for
  forecast — the F-055/F-056 defect class at the contract layer.
verification_script: scripts/check_battleground_circularity_disclosure.py
notes: |
  Proposed script behavior: (1) parse the schema contract and require the
  estimand/provenance declaration strings (retrodiction label; anchored
  posterior; outcome-derived swing factors); (2) grep the Quarto source for
  the disclosure sentence adjacent to the fig-battleground block; (3) fail
  if either surface loses the disclosure.
  Spec: governance/improvement_plan/IMP-C05_geo-uncertainty-integrity.md
```

**GitHub issue body:**

> **Title:** Module C: evidence-based geo sigma, unanchored companion table, intervals on the battleground chart (IMP-C05)
>
> **Problem.** `_SIGMA_IDIO_PP = 1.5` is calibrated to a target visual HDI
> width (`geo/heatmap.py:36-40`), not to historical department residual
> variance; the primary bar chart (`post_mortem.qmd:307-336`) shows point
> probabilities only, with HDIs relegated to hover metadata on a separate
> figure.
>
> **Acceptance criteria.**
> 1. Idiosyncratic sigma estimated from a documented historical reference
>    (method + dataset hash in run manifest), or the product downgraded to
>    `illustrative` in schema and captions.
> 2. Companion unanchored table published (`use_outcome_anchor: false`),
>    with a flip list for departments whose classification changes.
> 3. Bar chart draws per-department HDI; color scale colorblind-safe
>    (IMP-V01 palette when available).
> 4. Contract bounds enforced: hdi_low ≤ win_probability_a ≤ hdi_high, all
>    in [0,1].
>
> **Blocked by:** IMP-C01 (valid posterior), IMP-C02 (observation model) —
> label `status:blocked` until both close.
>
> **Spec:** `governance/improvement_plan/IMP-C05_geo-uncertainty-integrity.md`

**Labels:** `type:feature`, `skill:module-c`, `effort:high`, `priority:p1`,
`status:blocked`
