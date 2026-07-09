---
id: IMP-V05
title: "Residual chart encoding fixes: PPC bands, dual-axis B8, heatmap scales, HDI band fills, quadrant/correlation cleanups"
absorbs: [V1, V3, V10, A20]
overlaps_triage: [AUD-S2, AUD-A9]
priority: P2
effort: medium
depends_on: [IMP-V01, IMP-V02]
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 69
status: filed
---

# IMP-V05 — Residual Chart Encoding Fixes

The governance chart sprints (F-053..F-067) fixed the honesty-critical
defects; this document collects the remaining *encoding-quality* defects so
they land once, inside the shared visual system (IMP-V01 template/palette)
and the canonical chart library (IMP-V02) — which is why both are hard
dependencies: fixing these charts before single-sourcing means fixing them
twice.

Per-chart inventory:

1. **PPC nested bands, single hue (V1).**
   `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/viz/ppc_plot.py:55-59`
   stacks the 95/80/50% posterior-predictive bands all in `#636EFA`,
   distinguished only by alpha; the same single-hue band pattern appears in
   `portfolio/quarto/post_mortem.qmd:109-117`. In grayscale or for
   low-contrast vision the three nested intervals are undecodable.
   *Fix spec:* distinct band lightness steps from the shared sequential
   ramp + direct interval labels on the right edge ("95%", "80%", "50%"),
   decodable without the legend and in grayscale.
2. **Dual-axis twinx B8, duplicated (V3).**
   `reports/eda/generate_eda.py:1286-1330` (grouped bars + `twinx()` budget
   line) and `reports/eda/build_notebook.py:1099-1122` (horizontal bars +
   twinx, different metric pairing) both cram three encodings onto two
   unrelated axes, inviting spurious visual correlation — and the two
   surfaces don't even draw the same chart.
   *Fix spec:* replace with a small-multiples panel (reach cap / expected
   contacts / budget as three aligned charts sharing the department axis);
   single implementation via IMP-V02.
3. **Plotly HDI as dotted lines, no band (V10).**
   `viz/plotly_explorer.py:28-45` draws `hdi_low`/`hdi_high` as two dotted
   traces with no fill between, while every matplotlib surface renders the
   same estimand as a shaded band.
   *Fix spec:* filled band (`fill='tonexty'` semantics) with the same
   interval labeling convention as the static charts.
4. **Heatmap scales (A20).** `generate_eda.py` chart_a4 (~:386-409) pins
   `vmin=0, vmax=1` for a mean-propensity metric living in ~0.5–0.7,
   washing out all real variation; chart_a9 (~:639) uses a custom
   blue-white-red diverging cmap for correlations with no non-hue sign cue
   beyond the numeric annotations.
   *Fix spec:* A4 scale bounded to the observed range (with the range
   stated in the subtitle so narrowness is disclosed, not hidden — this
   chart's near-constancy is itself F-052 evidence); A9 keeps annotations
   and adds a sign-redundant encoding (cell hatching or +/− glyphs) with a
   colorblind-safe diverging ramp from IMP-V01.
5. **Riders from the triage ledger:** AUD-S2 (S2 quadrant labels wrong —
   correct the quadrant semantics while re-encoding under the shared
   template) and AUD-A9 (A9 correlation QA is internal-only — the corrected
   A9 either graduates to the published set with the fixes above or is
   explicitly retired from `FIGURE_MANIFEST.yaml`).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:** the five items above, implemented once in the canonical chart
library and consumed by every surface (static EDA report, notebook,
dashboard, Quarto). No data, model, or estimand changes — encodings,
scales, labels, and layout only.

**Out-of-Scope:**
- Reliability diagrams (IMP-V04). Battleground bar intervals (IMP-C05).
- Palette/template definition (IMP-V01) and the single-sourcing refactor
  mechanics (IMP-V02) — this document lands *after* both.
- Any chart already governed by a closed finding's verification script
  (F-053..F-067): those invariants must stay green throughout.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Decodable nested intervals (Happy Path)**
- **Given** the PPC chart rendered from a posterior-predictive artifact with
  50/80/95% bands,
- **When** the export is converted to grayscale,
- **Then** the three bands remain visually distinct (distinct lightness
  steps) and each band's right-edge label identifies its level without a
  legend lookup.

**Scenario: B8 without dual axes (Happy Path)**
- **Given** the B8 reach/contacts/budget data for all departments,
- **When** the canonical B8 renders,
- **Then** no axes object in the figure carries two unrelated scales
  (statically checkable: no `twinx` in the canonical library), the three
  metrics appear as aligned small multiples sharing one department ordering,
  and the notebook surface renders the identical figure via the same
  library call.

**Scenario: Narrow-range heatmap disclosure (Edge Case)**
- **Given** the A4 department×segment propensity matrix whose observed
  values span [0.52, 0.68],
- **When** the heatmap renders,
- **Then** the color scale spans the observed range (padded to sensible
  ticks), the subtitle states the range explicitly, and a near-constant
  matrix therefore *looks* near-constant in color while the subtitle says
  so — the scale neither fabricates contrast nor hides it.

**Scenario: Interactive/static interval parity (Happy Path)**
- **Given** the same daily-posterior artifact rendered by the Plotly
  explorer and the static C1 chart,
- **When** both render,
- **Then** both show the HDI as a filled band with the same nominal-level
  label text (which, per IMP-C03, derives from the configured `hdi_prob`).

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing dual-axis reintroduction**
- **Given** the canonical chart library at any future revision,
- **When** the chart-integrity checks run,
- **Then** no chart in the published set may pair two unrelated quantitative
  scales on one plot via twin axes; a new `twinx` call site in the library
  is a failing state.

**Scenario: Preventing alpha-only interval stacking**
- **Given** any chart drawing nested uncertainty intervals,
- **When** it renders,
- **Then** interval levels must differ in more than opacity alone
  (lightness step, boundary line, or direct label required) — alpha-only
  nesting is not a permitted encoding in the library.

**Scenario: Preventing scale-choice concealment**
- **Given** any heatmap or filled-scale chart whose color range is not
  [data min, data max] or a documented standard range,
- **When** it renders,
- **Then** the chosen range must be stated on the figure; an undisclosed
  truncated or expanded scale is a verification failure.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — presentation layer only; no estimand or
  data changes.
- **Performance & decay:** full static chart regeneration
  (`generate_eda.py` successor via the canonical library) stays within its
  current runtime budget (< 2 min on the canonical artifacts); the Plotly
  band fill must not visibly degrade explorer interactivity.
- **Data integrity:** every fixed chart continues to consume manifest-
  registered artifacts (IMP-V02 lineage); the F-053..F-067 verification
  scripts all still pass after re-encoding (their invariants are inputs to
  this work, not casualties).
- **Reproducibility:** re-rendering from unchanged artifacts is
  deterministic; figure regression fixtures (per IMP-V01 template) cover
  each re-encoded chart.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Residual chart encoding fixes: PPC band hues, B8 small multiples, Plotly HDI fills, A4/A9 heatmap scales, S2 quadrants (IMP-V05)
>
> **Problem.** Five encoding defects remain after the governance chart
> sprints: PPC 95/80/50 bands differ only in alpha
> (`viz/ppc_plot.py:55-59`; also `post_mortem.qmd:109-117`); B8 uses twinx
> dual axes, implemented differently in `generate_eda.py:1286-1330` vs
> `build_notebook.py:1099-1122`; the Plotly explorer draws HDIs as dotted
> lines without band fill (`plotly_explorer.py:28-45`); A4 pins a [0,1]
> color scale on a ~0.5–0.7 metric and A9's diverging palette lacks a
> non-hue sign cue (`generate_eda.py` ~:386-409, ~:639); AUD-S2 quadrant
> labels are wrong and AUD-A9's corrected chart needs a publish-or-retire
> decision.
>
> **Acceptance criteria.**
> 1. PPC bands: lightness-stepped, direct-labeled, grayscale-decodable.
> 2. B8: small-multiples replacement, zero `twinx` in the canonical
>    library, notebook renders the identical figure.
> 3. Plotly explorer: filled HDI band, label text driven by configured
>    `hdi_prob`.
> 4. A4: observed-range scale + on-figure range disclosure; A9:
>    colorblind-safe diverging ramp + sign-redundant encoding; S2 quadrant
>    labels corrected; A9 publish-or-retire recorded in FIGURE_MANIFEST.
> 5. All F-053..F-067 verification scripts remain green.
>
> **Blocked by:** IMP-V01 (palette/template), IMP-V02 (single sourcing) —
> label `status:blocked` until both close.
>
> **Spec:** `governance/improvement_plan/IMP-V05_residual-encodings.md`

**Labels:** `type:visualization`, `skill:shared`, `effort:medium`,
`priority:p2`, `status:blocked`
