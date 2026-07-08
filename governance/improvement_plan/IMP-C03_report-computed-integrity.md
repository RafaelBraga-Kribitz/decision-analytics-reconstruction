---
id: IMP-C03
title: "Post-mortem report computed-from-artifact integrity"
absorbs: [C2, C3, C9]
overlaps_triage: [AUD-C4]
priority: P1
effort: medium
depends_on: [IMP-C01, IMP-C02, IMP-C05]
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-C03 — Post-Mortem Report Computed-From-Artifact Integrity

The published Quarto report `portfolio/quarto/post_mortem.qmd` contains three
classes of hand-typed content that contradicts the code and artifacts it
claims to describe. All three share one root cause: numbers and labels typed
as literals in the report source instead of computed from run artifacts.

**Interval mislabel recurrence (C2).** `post_mortem.qmd:101` sets the
figure caption `"Daily posterior preference-proxy margin (pp) with 95% HDI
bands..."` and `:116` sets the trace legend `name="95% HDI"`, while the model
computes a **94%** HDI: `models/tracking/hierarchical.py:29` loads
`HDI_PROB = float(_load_sampler_config().get("hdi_prob", 0.94))` from
`config/pymc_sampler.yaml:8` (`hdi_prob: 0.94`). This is a recurrence of the
closed finding F-068 (interval mislabel) *outside its verification scope*:
`scripts/check_module_c_interval_honesty.py:31-40` checks only
`hierarchical.py` and `reports/eda/generate_eda.py` — the Quarto surface is
unwatched. The same stale "95%" labels also appear at `:180`
(`tbl-cap "...Wide credible intervals..."` table headed "HDI 95% low/high" at
`:189`) and `:216` (fig-cap "95% HDI").

**Hardcoded diagnostics table (C3).** `post_mortem.qmd:370-401`
(`label: tbl-diagnostics`, the "Sampling Diagnostics" section) is a literal
`display(HTML("""..."""))` block containing hand-typed strings: `"4"`
divergences (`:385`), `"&gt; 1.01"` for R̂ (`:387`), `"&lt; 100"` for ESS
(`:388`). Nothing is read from `idata` or any diagnostics artifact — if a
rerun produces 0 or 40 divergences, the report still says 4. The PPC table
directly below (`:427-462`, `label: tbl-ppc-summary`) shows the correct
pattern: it reads `ppc_summary.json` and formats computed values.

**Superseded methodology prose (C9).** `post_mortem.qmd:301` introduces the
battleground section as "derived by mapping the last-day posterior margin
through a logistic transformation with synthetic geographic heterogeneity",
and the Methodology Summary table rows at `:473-479` state
`GaussianRandomWalk(sigma ~ HalfNormal(2.0))`, `Normal(0, 3)` house priors,
and "Logistic transformation of posterior margin + synthetic geographic
jitter". All three describe the superseded v0.1 model. Actual code:
`geo/heatmap.py` v0.2 computes TSJE-derived swing factors through a Gaussian
CDF (`heatmap.py:33,76-93,135`), and `hierarchical.py:134` uses
`HalfNormal(1.5)` for `sigma_rw`, `:136` `HalfNormal(2.5)` for `sigma_house`
(the report's `Normal(0, 3)` house prior matches neither). The v0.1 formula
being described is the same fabricated formula F-070 removed.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `portfolio/quarto/post_mortem.qmd` in full: interval-probability labels
  (`:101`, `:116`, `:180`, `:189`, `:216`), the hardcoded diagnostics table
  (`:370-401`), the battleground methodology prose (`:301`), and the
  Methodology Summary table (`:469-482`).
- A diagnostics artifact contract: the tracking pipeline must export a
  machine-readable diagnostics summary (R̂ max, ESS bulk/tail min, divergence
  count, chains) that the report reads, mirroring the existing
  `ppc_summary.json` pattern at `:427-462`.
- Extension of the F-068-class verification surface
  (`scripts/check_module_c_interval_honesty.py`) to cover `post_mortem.qmd`.
- A static cross-check of the Methodology Summary table against the code
  constants it cites (`hierarchical.py:134,136`, `geo/heatmap.py:33`).

**Out-of-Scope:**
- Whether the diagnostics values themselves pass (IMP-C01 owns making R̂/ESS/
  divergences actually acceptable; this document only requires the report to
  *truthfully display* whatever they are).
- The battleground chart's dropped uncertainty and color scale (IMP-C05/V2).
- The φ→σ_obs and prior-family narrative accuracy beyond the constants named
  above (IMP-C02).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Interval labels derived from config (Happy Path)**
- **Given** `config/pymc_sampler.yaml:8` sets `hdi_prob: 0.94`,
- **When** `post_mortem.qmd` renders,
- **Then** every interval label in the report (fig-caps at `:101`, `:216`,
  trace name at `:116`, table headers at `:189`) displays "94% HDI" — and
  the string is produced by an f-string interpolating the loaded `hdi_prob`
  value (or the `interval_prob` attr stamped into the daily parquet's
  provenance), so a future config change to 0.90 re-renders as "90% HDI"
  with no report edit.

**Scenario: Diagnostics table computed from a rerun artifact (Edge Case)**
- **Given** a pipeline rerun whose full-NUTS fit produces 0 divergences and
  R̂ max 1.004,
- **When** the report renders against that run's exported diagnostics
  summary,
- **Then** `tbl-diagnostics` shows "0" and "1.004" with ✅ status cells —
  computed by the same pass-criterion logic in code, not retyped — and if
  the diagnostics artifact is missing, the section renders an explicit
  "diagnostics artifact not found" notice (as `:167` and `:421-424` already
  do for missing data), never a stale table.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing hand-typed metric values in the report source**
- **Given** any numeric diagnostic, coverage, or interval-probability value
  displayed by `post_mortem.qmd`,
- **When** the report source is inspected statically,
- **Then** no such value may appear as a string literal inside a
  `display(HTML(...))` block — every displayed metric must be interpolated
  from a loaded artifact (`idata`-derived JSON, parquet column, or config
  key). A literal "4 divergences" or "95%" in the source is a failing state
  even if it happens to be currently true.

**Scenario: Preventing methodology prose drifting from code constants**
- **Given** the Methodology Summary table names prior distributions and the
  battleground mapping,
- **When** the verification script compares the table's stated constants
  against `hierarchical.py:134` (`HalfNormal(1.5)`), `:136`
  (`HalfNormal(2.5)`), and `geo/heatmap.py:33` (`c_battleground_v0.2`,
  Gaussian-CDF swing model),
- **Then** any mismatch — including the currently-published
  `HalfNormal(2.0)` / `Normal(0, 3)` / "logistic transformation ... synthetic
  geographic jitter" strings — fails the gate before merge.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — no model behavior changes; this is a
  report-integrity guarantee.
- **Performance & decay:** the diagnostics-summary export is a
  post-sampling aggregation over an already-fitted `idata` and must add
  < 10 s to the tracking pipeline; the verification script is static text
  analysis and must complete in < 5 s within `make verify`.
- **Data integrity:** the diagnostics summary JSON must carry the run's
  `model_version` and `created_at` so a report rendered against a stale
  artifact is detectable; report render must abort (not silently reuse) when
  the summary's `model_version` mismatches the daily parquet's.
- **Reproducibility:** rendering the report twice against the same run
  directory must produce identical displayed metric values; no report-side
  randomness or re-sampling is permitted.

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "post_mortem.qmd publishes hand-typed diagnostics, stale 95% labels, and superseded v0.1 methodology"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 1   # F-068 (interval mislabel) recurrence on an unwatched surface
evidence: |
  portfolio/quarto/post_mortem.qmd:101 fig-cap "95% HDI" and :116 name="95% HDI"
  (also :180/:189/:216) contradict models/tracking/hierarchical.py:29 HDI_PROB
  loaded from config/pymc_sampler.yaml:8 (hdi_prob: 0.94) — F-068 recurrence
  outside the scope of scripts/check_module_c_interval_honesty.py, which checks
  only hierarchical.py and reports/eda/generate_eda.py.
  post_mortem.qmd:370-401 "Sampling Diagnostics" is a literal display(HTML(...))
  with hardcoded "4" divergences / "> 1.01" R-hat / "< 100" ESS strings never
  computed from idata — unlike the PPC table at :427-462, which correctly reads
  ppc_summary.json.
  post_mortem.qmd:301 and :473-479 describe the superseded v0.1 battleground
  formula ("logistic transformation ... synthetic geographic jitter" — the
  F-070 fabricated formula) and wrong prior constants (HalfNormal(2.0),
  Normal(0, 3)) versus actual code (geo/heatmap.py v0.2 Gaussian-CDF swing
  factors; hierarchical.py:134 HalfNormal(1.5), :136 HalfNormal(2.5)).
verification_script: scripts/check_post_mortem_computed_integrity.py
notes: |
  Proposed script behavior: (1) parse post_mortem.qmd and fail on any
  interval-probability percentage appearing as a bare string literal in a
  fig-cap/name/table header — the label must be interpolated from hdi_prob;
  (2) fail if the tbl-diagnostics cell content contains hardcoded numerals
  inside a display(HTML(...)) literal rather than f-string interpolation from
  a loaded diagnostics artifact; (3) cross-check the Methodology Summary table
  rows against hierarchical.py's HalfNormal(1.5)/HalfNormal(2.5) constants and
  geo/heatmap.py's MODEL_VERSION, failing on "logistic transformation",
  "synthetic geographic jitter", "HalfNormal(2.0)", or "Normal(0, 3)".
  Closure requires the diagnostics-summary export to exist first (the report
  cannot compute from an artifact that is not emitted) — writing that emitter
  plus this script is the first half of the remediation per AUDIT_PROCEDURE.md.
  Depends on IMP-C01 (diagnostics worth displaying), IMP-C02 and IMP-C05
  (methodology table rows describe those components' post-remediation state).
  Spec: governance/improvement_plan/IMP-C03_report-computed-integrity.md
```
