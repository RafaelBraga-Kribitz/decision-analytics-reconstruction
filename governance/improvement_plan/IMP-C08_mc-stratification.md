---
id: IMP-C08
title: "Monte Carlo scenario stratification: base-rate reweighting or proportional sampling"
absorbs: [C14]
overlaps_triage: []
priority: P2
effort: medium
depends_on: [IMP-C01]
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 65
status: filed
---

# IMP-C08 — Monte Carlo Scenario Stratification

`module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/scenarios/monte_carlo.py:34-45`
draws its scenario ensemble with equal one-third allocation across the three
canonical buckets (`baseline` / `extreme_tracker` / `compounded_herd` via
`_bucket_share` over `CANONICAL_BUCKETS`), regardless of each bucket's
empirical prevalence in the tracking data. By construction, `baseline`
dominates real polling; equal thirds therefore overweight the rare/extreme
buckets in every draw-pooled statistic. No reweighting step exists anywhere
downstream — the scenario box plot in
`portfolio/quarto/post_mortem.qmd:257-270` and any pooled summary implicitly
present a synthetic mixture as if it reflected scenario likelihood. The draw
budget itself (`_mc_n`: 10,000 full / 600 fast, `monte_carlo.py:34-37`) is
an unjustified constant with no Monte Carlo standard-error target behind it.

Equal-allocation stratification is a legitimate *variance-reduction design* —
the defect is that the design weights are never undone (or disclosed) when
draws are pooled.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- An empirical bucket-prevalence estimate computed from the canonical
  tracking data (the same bucket-assignment function from
  `features/shock_scores.py` applied to observed polls), recorded in the MC
  run manifest.
- One of two designs, chosen and documented:
  (a) **proportional sampling** — bucket draw counts follow estimated
  prevalence; or (b) **stratified with importance weights** — equal
  allocation retained, each draw carrying `weight =
  prevalence(bucket) / design_share(bucket)`, and every downstream summary
  (pooled means, quantiles, box plots, tables) consuming the weight column.
- Per-bucket (unpooled) views remain valid either way and are labeled as
  conditional-on-scenario, not likelihood-weighted.
- A draw-budget justification: `_mc_n` derived from a stated Monte Carlo
  standard-error target for the headline pooled statistic (e.g., MC-SE of
  the pooled margin mean ≤ 0.1 pp), with the arithmetic recorded next to the
  constant.

**Out-of-Scope:**
- The bucket-assignment thresholds and covariances themselves (IMP-C04).
- The validity of the posterior the draws start from (IMP-C01 — dependency,
  since reweighting draws from a non-converged posterior is polish on an
  invalid object).
- Chart encodings of the scenario views (IMP-V05).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Weighted pooled summary (Happy Path)**
- **Given** an MC run with stratified equal allocation and estimated
  prevalences (p_base, p_ext, p_herd),
- **When** any pooled statistic is computed,
- **Then** it is weight-aware (weighted mean/quantile), and recomputing it
  with weights forced to 1 changes the value — proving weights actually
  participate — while the manifest records both the prevalences and the
  design shares.

**Scenario: Proportional design (alternative Happy Path)**
- **Given** the proportional-sampling design is chosen,
- **When** the ensemble is drawn with n total draws,
- **Then** per-bucket draw counts match round(n × prevalence) within
  integer rounding, and rare buckets retain a documented minimum draw floor
  (so conditional views keep enough samples), with the floor's distortion of
  pooled stats corrected by weights.

**Scenario: Empty or near-empty bucket (Edge Case)**
- **Given** a tracking dataset where a bucket's estimated prevalence is 0
  (no observed poll assigned to it),
- **When** the ensemble is drawn,
- **Then** the bucket receives weight 0 in pooled statistics but may still
  be drawn at the minimum floor for conditional exploration, labeled
  `hypothetical (prevalence 0 in observed data)` in every artifact that
  shows it.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing design weights leaking into likelihood claims**
- **Given** any artifact pooling draws across buckets,
- **When** it is produced,
- **Then** it must never pool unweighted equal-allocation draws — a pooled
  statistic without the weight column applied (or without proportional
  design) is a verification failure, because it silently asserts a uniform
  scenario prior nobody chose.

**Scenario: Preventing silent prevalence drift**
- **Given** a change to the tracking dataset or bucket-assignment parameters,
- **When** the MC stage runs,
- **Then** prevalences are re-estimated in the same run (never read from a
  stale cache); the manifest's prevalence block must carry the tracking-data
  hash it was computed from, and a hash mismatch aborts.

**Scenario: Preventing arbitrary draw budgets**
- **Given** any future change to `_mc_n`,
- **When** the constant is edited,
- **Then** the recorded MC-SE derivation must be updated in the same change;
  a bare constant edit without the accompanying arithmetic fails review (the
  constant and its justification live together).

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A at the population level; at the scenario
  level, the change removes the implicit uniform-scenario prior that biased
  pooled outputs toward extreme narratives.
- **Performance & decay:** weight application must not change the MC stage's
  asymptotic cost; full run stays within its current pipeline budget, and
  `MC_FAST` (600 draws) keeps the same floor semantics so tests remain fast.
- **Data integrity:** the draws artifact schema gains `scenario_bucket`
  (already present), `draw_weight` (nullable: false, > 0, finite), and the
  manifest gains the prevalence block with dataset hash; the IMP-C07
  validator enforces the schema once available.
- **Reproducibility:** with seed 42, bucket assignment, draw counts, and
  weights are identical across runs; the weighted pooled headline statistic
  is reproducible to exact equality on the same platform and to a recorded
  tolerance across platforms.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Module C: reweight or proportionally sample the Monte Carlo scenario buckets; justify the draw budget (IMP-C08)
>
> **Problem.** `scenarios/monte_carlo.py:34-45` draws equal thirds across
> `baseline`/`extreme_tracker`/`compounded_herd` regardless of empirical
> prevalence, and no downstream reweighting exists — pooled summaries (e.g.,
> the scenario box plot at `post_mortem.qmd:257-270`) overweight rare
> buckets under an implicit uniform prior nobody chose. `_mc_n` (10,000/600)
> has no stated MC-standard-error target.
>
> **Acceptance criteria.**
> 1. Empirical bucket prevalences estimated from observed tracking polls,
>    recorded in the run manifest with the tracking-data hash.
> 2. Either proportional sampling (with a minimum per-bucket floor +
>    corrective weights) or equal-allocation stratification with a
>    `draw_weight` column consumed by every pooled statistic.
> 3. Pooled artifacts provably weight-aware (weights-forced-to-1 comparison
>    differs); per-bucket views labeled conditional-on-scenario.
> 4. `_mc_n` derived from a stated MC-SE target with the arithmetic recorded
>    beside the constant.
>
> **Blocked by:** IMP-C01 (draws must come from a converged posterior) —
> label `status:blocked` until it closes.
>
> **Spec:** `governance/improvement_plan/IMP-C08_mc-stratification.md`

**Labels:** `type:data`, `skill:module-c`, `effort:medium`, `priority:p2`,
`status:blocked`
