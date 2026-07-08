---
id: IMP-V06
title: "Streamlit dashboard parity and defects: same builders as the static report; deterministic SHAP tab"
absorbs: [V8, V9]
overlaps_triage: []
priority: P2
effort: low
depends_on: [IMP-V01]
soft_depends_on: [IMP-V02]
queue: issues
target_repo: decision-analytics-reconstruction
issue: 70
status: filed
---

# IMP-V06 — Dashboard Parity & Defects

The Module A Streamlit dashboard presents the same metrics as the static
portfolio report but through independent, unstyled implementations:

1. **Segment-size chart inconsistency (V8).**
   `module_a_population_segmentation/src/population_segmentation/visualization/segment_profiles.py:49-64`
   (`segment_size_chart`, rendered at `app/streamlit_dashboard.py:152`) is a
   bare `px.bar` with no explicit sort (inherits groupby order), Plotly's
   default colorway, and no value labels. The identical quantity in the
   static report (`A1_segment_sizes.png`,
   `reports/eda/generate_eda.py:245-271`) is `SEG_ORDER`-sorted,
   `SEG_COLORS`-colored, horizontal, and direct-labeled with count and
   percentage. A reader moving between surfaces sees two orderings and two
   color systems for one metric.
2. **`st.pyplot(None)` risk in the SHAP tab (V9, verification owed).**
   `app/streamlit_dashboard.py:222-225` passes the return value of
   `shap.summary_plot(..., show=False)` — `None` in most shap versions —
   into `st.pyplot(fig, ...)`. Depending on installed shap/streamlit
   versions this silently falls back to `plt.gcf()` or breaks. The audit
   marked this **Inferred (verification owed)**: the fix work starts by
   confirming the behavior on the pinned versions.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- Dashboard charts for metrics that also exist in the static report
  (segment sizes first; any others found by inventory) consume the same
  ordering (`SEG_ORDER`), the same palette (IMP-V01 shared palette — hard
  dependency), the same direct-labeling convention, and, once IMP-V02
  lands, the same canonical builder functions (soft dependency: parity by
  convention now, parity by construction after V02).
- A parity assertion: for each shared metric, the dashboard's plotted
  values, ordering, and category-color assignments match the static
  artifact's (testable against the canonical parquet without launching a
  browser).
- SHAP tab determinism: capture the current figure explicitly
  (`plt.gcf()`-equivalent) rather than passing the plot call's return
  value; behavior verified on the pinned shap/streamlit versions; the tab
  renders the same figure for the same inputs on every load.

**Out-of-Scope:**
- Which SHAP artifact is canonical and its data provenance (IMP-V03 —
  already covers the generator collision).
- Reliability tab geometry/statistics (IMP-V04).
- Dashboard vs canonical population size (AUD-XCUT-003 — bound to open
  finding F-050, not re-opened here).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: One metric, one visual identity (Happy Path)**
- **Given** the canonical segment-profile artifact,
- **When** the dashboard's Segment Explorer tab and the static A1 chart both
  render,
- **Then** both show segments in `SEG_ORDER`, both map each segment to the
  same shared-palette color, and both direct-label count + percentage — a
  segment's identity never changes color or rank between surfaces.

**Scenario: Parity check without a browser (Happy Path)**
- **Given** the chart-building functions and the canonical artifact,
- **When** the parity test runs in CI,
- **Then** it compares the dashboard builder's figure spec (categories,
  values, order, colors) against the static builder's for each shared
  metric and fails on any mismatch — parity is asserted on figure data
  structures, not screenshots.

**Scenario: SHAP tab render (Edge Case)**
- **Given** the pinned shap and streamlit versions and a computed SHAP
  values fixture,
- **When** the SHAP tab renders twice for the same inputs,
- **Then** both renders succeed with an identical figure (no dependence on
  matplotlib's implicit current-figure state left by unrelated tabs), and
  the render path never passes `None` to `st.pyplot`.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing default-styling drift on shared metrics**
- **Given** any dashboard chart of a metric that exists in the published
  static set,
- **When** it is added or modified,
- **Then** it must not use library-default category ordering or colorway —
  unstyled defaults on shared metrics are a parity failure even if "close
  enough" visually.

**Scenario: Preventing implicit-figure-state rendering**
- **Given** any matplotlib-backed rendering in the dashboard,
- **When** a figure is displayed,
- **Then** the figure object passed to `st.pyplot` must be an explicit,
  non-None `Figure` owned by that render block — relying on the plotting
  call's return value or ambient `gcf()` state across tabs is prohibited.

**Scenario: Preventing silent divergence after upstream changes**
- **Given** a change to `SEG_ORDER`, the shared palette, or the segment
  vocabulary,
- **When** CI runs,
- **Then** the parity test re-derives both surfaces from the shared
  constants — a change that updates the static chart but strands the
  dashboard (or vice versa) fails.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — presentation layer.
- **Performance & decay:** dashboard tab render adds no per-pageview model
  computation (consumes precomputed artifacts); parity test runs in < 10 s
  in CI without Streamlit runtime (pure builder-level comparison).
- **Data integrity:** dashboard builders read the same manifest-registered
  artifacts as the static pipeline (no live re-derivation of shared metrics
  from raw data).
- **Reproducibility:** same artifact + same builders ⇒ same figure spec on
  every load; SHAP tab output stable across reloads for fixed inputs.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Dashboard parity with the static report; deterministic SHAP tab rendering (IMP-V06)
>
> **Problem.** The dashboard's segment-size chart
> (`visualization/segment_profiles.py:49-64`, rendered at
> `streamlit_dashboard.py:152`) uses no sort, default colors, and no value
> labels, while the static A1 chart (`generate_eda.py:245-271`) is
> SEG_ORDER-sorted, SEG_COLORS-colored, and direct-labeled — one metric,
> two visual identities. The SHAP tab (`streamlit_dashboard.py:222-225`)
> passes `shap.summary_plot(...)`'s return value (typically `None`) to
> `st.pyplot`, a version-dependent silent fallback or crash (verification
> owed on pinned versions).
>
> **Acceptance criteria.**
> 1. Shared metrics render with shared ordering, palette (IMP-V01), and
>    labeling on both surfaces; after IMP-V02, via the same builder calls.
> 2. CI parity test compares builder-level figure specs (categories,
>    values, order, colors) for each shared metric — no browser needed.
> 3. SHAP tab: explicit Figure capture, verified against pinned
>    shap/streamlit versions; two renders of the same inputs are identical;
>    `None` can never reach `st.pyplot`.
>
> **Blocked by:** IMP-V01 (shared palette) — label `status:blocked` until
> it closes.
>
> **Spec:** `governance/improvement_plan/IMP-V06_dashboard-parity.md`

**Labels:** `type:visualization`, `skill:module-a`, `effort:low`,
`priority:p2`, `status:blocked`
