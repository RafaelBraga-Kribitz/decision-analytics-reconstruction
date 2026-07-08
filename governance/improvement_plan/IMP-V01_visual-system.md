---
id: IMP-V01
title: "Shared visual system: colorblind-safe palette and figure template"
absorbs: [V7]
overlaps_triage: [AUD-XCUT-004]
priority: P1
effort: medium
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 66
status: filed
---

# IMP-V01 — Shared Visual System

`reports/eda/generate_eda.py:45-52` defines `SEG_COLORS`, the six-segment
categorical color map every EDA chart draws from:

```
SEG_COLORS = {
    "rural_committed": RED,                      # "#e60000"
    "urban_high_volatility": BLUE,
    "structurally_dependent_bloc": ORANGE,
    "committed_opposition": PURPLE,
    "rural_low_propensity": TEAL,
    "youth_volatile": GREEN,                      # "#2ca02c"
}
```

`RED` (`#e60000`) and `GREEN` (`#2ca02c`) sit in the same six-color legend.
Under deuteranopia/protanopia (~8% of men) these two hues collapse toward the
same perceived color, and the map is reused wherever all six segments render
simultaneously: `chart_a2` (age-by-segment facets, `generate_eda.py:277-324`),
`chart_a5` (propensity violins, `:422-458`), `chart_a12` (reachability step
histograms, `:817-843`), `chart_a13` (preference-strength facets,
`:849-899`), `chart_a10` (PCA biplot, `:680-759`), and `chart_s2` (propensity
× reachability bubble matrix, `:1992-2094`). Three of these — A10, A12, S2 —
rely on color as the *only* channel distinguishing `rural_committed` from
`youth_volatile`: A10 and S2 label points/bubbles by proximity text but the
six-way legend swatch is still the primary key; A12 uses step-outline color
alone with no per-line marker or direct label. Triage row `AUD-XCUT-004`
(`open_unfiled`, root cause `figure_template`) separately records
watermark/legend collisions across all modules — the same root cause: there
is no shared figure template governing margins, watermark placement, or
legend rules, so each chart function reinvents them.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- One shared, importable palette module (e.g.
  `reports/eda/visual_system/palette.py`) defining the canonical
  `segment_label → color` mapping for the six segments currently hard-coded
  as `SEG_COLORS` (`generate_eda.py:34-52`), chosen from a colorblind-safe
  family (Okabe-Ito-class: hues selected for pairwise separability under
  protanopia, deuteranopia, and tritanopia simulation — not merely "looks
  different to me").
- One shared figure-template helper (margins, watermark/source-attribution
  zone — currently duplicated ad hoc via `annotate_source(ax)` and
  `fig.text(0.5, -0.01/-0.02, SOURCE, ...)` calls scattered across
  `generate_eda.py`, legend placement conventions, and a direct-labeling
  preference for categorical charts with ≥4 series).
- Adoption by both chart pipelines (`reports/eda/generate_eda.py` and
  `reports/eda/build_notebook.py`, which defines its own local `COLOR` dict
  for chart B8 rather than importing a shared source) and by the Module A
  dashboard (`module_a_population_segmentation/app/streamlit_dashboard.py`,
  via `visualization/segment_profiles.py:49-64`'s `segment_size_chart`,
  which currently uses Plotly Express's default colorway with no reference
  to `SEG_COLORS` at all).
- A palette-contrast / CVD-simulation check as a documented verification
  step (static, no model fitting).
- Concrete charts this palette/template governs at launch: A2, A5, A10, A12,
  A13, S2, and the dashboard's segment size chart.

**Out-of-Scope:**
- Per-chart encoding redesigns beyond adopting the shared palette/template
  (dual-axis abuse, single-hue alpha stacking, fixed-range color scales) —
  those are `IMP-V05`.
- Making the two chart pipelines call one implementation instead of two
  (`IMP-V02`); this IMP only requires both pipelines to *source their colors
  and template from the same module*, not to be a single codebase.
- The reliability-diagram-specific aspect-ratio and disclaimer requirements
  (`IMP-V04`), which depend on this IMP for palette/template mechanics but
  define their own acceptance criteria.
- Dashboard-specific defects not caused by the missing shared palette (the
  SHAP `st.pyplot(None)` risk at `streamlit_dashboard.py:222-225` is
  `IMP-V06`).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Palette passes CVD-simulation contrast check (Happy Path)**
- **Given** the shared palette module assigns each of the six canonical
  `segment_label` values (`rural_committed`, `urban_high_volatility`,
  `structurally_dependent_bloc`, `committed_opposition`,
  `rural_low_propensity`, `youth_volatile`) a hex color,
- **When** the palette-contrast/CVD verification step simulates protanopia,
  deuteranopia, and tritanopia over all 15 pairwise color comparisons,
- **Then** every pair's simulated perceptual distance exceeds a documented
  minimum threshold, and the check exits 0 with `[PASS]`; the current
  `RED`/`GREEN` pair (`generate_eda.py:46,51`) is the motivating case that
  must move from "fails" to "passes" under this check.

**Scenario: Legend-only charts carry a redundant encoding (Edge Case)**
- **Given** a chart whose legend is the primary key for all six segments
  with no other structural cue (A10's PCA biplot legend, A12's step-outline
  legend, S2's bubble-label legend),
- **When** the shared figure template is applied to that chart's generator
  function,
- **Then** the chart also carries a non-color redundant channel (direct
  label, distinct marker, or line style per segment) so segment identity
  survives both grayscale and CVD-simulated rendering — verified by a static
  check that `chart_a10`, `chart_a12`, and `chart_s2` each invoke the
  template's redundant-encoding helper, not `SEG_COLORS`/`ax.legend` alone.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing ad hoc color literals outside the shared module**
- **Given** any chart-generating function in `generate_eda.py`,
  `build_notebook.py`, or `module_a_population_segmentation/.../visualization/*.py`,
- **When** it needs a segment/category color,
- **Then** it must import the shared palette module's mapping — a
  grep/AST-based check fails the build if a new `SEG_COLORS`-shaped literal
  dict, or a raw hex string keyed by a `segment_label` value, appears
  anywhere outside the shared module (this is the recurrence guard for
  `build_notebook.py`'s independent `COLOR` dict pattern).

**Scenario: Preventing new legend-only differentiation**
- **Given** any new or modified chart with four or more categorical series
  sharing one legend,
- **When** the figure-template validator runs (part of `make verify`),
- **Then** it fails if color is the only channel distinguishing the series —
  closing the `AUD-XCUT-004` root cause rather than patching individual
  charts one at a time.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A for model behavior — no model output
  changes. This IMP is itself an accessibility guarantee: ~8% of men have
  red-green color vision deficiency, and the six-segment legend is a
  decision-facing artifact (targeting/segment charts), so a color collision
  here is a readability-equity issue for that viewer population, not a
  protected-attribute proxy in the model.
- **Performance & decay:** the palette-contrast/CVD check is static (color
  math only, no model fitting or data load) and must complete in under 5s so
  it adds negligible cost to `make verify`.
- **Data integrity:** the palette module's key set must exactly match the
  canonical six `segment_label` values produced by
  `population_segmentation.models.segmentation`; a chart encountering a
  seventh, unmapped segment value must fail loudly (current `GREY` fallback
  in `generate_eda.py` via `SEG_COLORS.get(seg, GREY)` silently hides this —
  the shared module must instead raise or flag it as a completeness gap).
- **Reproducibility:** palette hex values are fixed constants, not derived
  or randomized per run; regenerating any governed chart twice from the same
  input must produce byte-identical color assignments.

## 5. Queue Stub (ready to file)

```
Title: Adopt a shared colorblind-safe palette and figure template across the EDA pipeline and Module A dashboard

## Problem
`reports/eda/generate_eda.py:45-52` assigns RED (#e60000) and GREEN
(#2ca02c) to two of six segments in `SEG_COLORS`, a legend reused across at
least six charts that show all segments simultaneously. Under
deuteranopia/protanopia (~8% of men) these two hues are hard to distinguish.
A10 (`generate_eda.py:680-759`), A12 (`:817-843`), and S2 (`:1992-2094`) rely
on color as the only channel separating segments in their legends. Separately,
`build_notebook.py` defines its own local `COLOR` dict instead of importing
from `generate_eda.py`, and the Module A dashboard's
`segment_size_chart` (`module_a_population_segmentation/src/population_segmentation/visualization/segment_profiles.py:49-64`,
rendered at `module_a_population_segmentation/app/streamlit_dashboard.py:152`)
uses Plotly Express's default colorway, ignoring `SEG_COLORS` entirely — three
independent color systems for one taxonomy. Triage row AUD-XCUT-004
(`governance/ISSUE_TRIAGE_MASTER.yaml:169`) separately records
watermark/legend collisions across all modules, rooted in the same missing
figure-template problem.

## Evidence
- `reports/eda/generate_eda.py:45-52` — `SEG_COLORS` RED/GREEN collision.
- `reports/eda/generate_eda.py:277-324` (A2), `:422-458` (A5), `:817-843`
  (A12), `:849-899` (A13), `:680-759` (A10), `:1992-2094` (S2) — six charts
  consuming `SEG_COLORS`.
- `module_a_population_segmentation/src/population_segmentation/visualization/segment_profiles.py:49-64`
  — `segment_size_chart`, Plotly Express default colorway, no reference to
  `SEG_COLORS`.
- `module_a_population_segmentation/app/streamlit_dashboard.py:152` — dashboard
  render call for the unaligned chart.
- `governance/ISSUE_TRIAGE_MASTER.yaml:169` — AUD-XCUT-004,
  `root_cause: figure_template`.

## Acceptance criteria
1. A shared palette module exists with one canonical `segment_label → color`
   mapping, colorblind-safe (Okabe-Ito-class), replacing the local
   `SEG_COLORS` and `build_notebook.py` `COLOR` literals.
2. A shared figure-template helper exists (margins, watermark/source zone,
   legend placement, direct-labeling preference) and is imported by
   `generate_eda.py`, `build_notebook.py`, and the Module A dashboard's
   chart builders.
3. A CVD-simulation/contrast check (protanopia, deuteranopia, tritanopia)
   passes for all pairwise segment-color comparisons.
4. A10, A12, and S2 each carry a redundant non-color encoding in addition to
   the shared palette.
5. `segment_size_chart` uses the shared palette instead of Plotly Express's
   default colorway.

## Verification
- New static check (e.g. `scripts/check_palette_cvd_contrast.py`) simulating
  CVD and asserting pairwise distance thresholds; run as part of
  `make verify`.
- New static check (e.g. `scripts/check_no_local_color_literals.py`)
  grepping for `SEG_COLORS`-shaped or hex-literal color dicts outside the
  shared module.

## Spec
governance/improvement_plan/IMP-V01_visual-system.md

## Labels
type:visualization, skill:shared, effort:medium, priority:p1, status:claude-ready
```
