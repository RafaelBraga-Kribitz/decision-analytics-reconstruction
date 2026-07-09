---
id: IMP-V04
title: "Reliability-diagram standard: one implementation, 1:1 aspect, bin counts, interval bands, persistent disclaimer"
absorbs: [V6, A19]
overlaps_triage: [AUD-REL, AUD-PUB-003]
priority: P1
effort: medium
depends_on: [IMP-V01, IMP-V02]
soft_depends_on: [IMP-A01]
queue: issues
target_repo: decision-analytics-reconstruction
issue: 68
status: filed
---

# IMP-V04 — Reliability-Diagram Standard

The calibration/reliability diagram — the single chart whose entire
diagnostic value depends on reading a 45° diagonal — is implemented
independently in at least two live surfaces, and none enforces the geometry
or the statistics that make it readable:

1. **No 1:1 aspect anywhere (V6).**
   `module_a_population_segmentation/src/population_segmentation/visualization/calibration_curves.py:60-68`
   (Plotly `reliability_chart`, rendered live in the dashboard at
   `app/streamlit_dashboard.py:168`) and
   `scripts/generate_module_a_report_charts.py:44-54` (matplotlib static
   report) both plot predicted-vs-observed with default autoscaling: no
   `set_aspect('equal')`, no `xaxis.scaleanchor="y"`, no matched
   `xlim`/`ylim`. The "Perfect" reference line renders at whatever angle the
   figure box produces, so over/under-confidence is judged against a
   diagonal that isn't 45°.
2. **Equal visual weight for unequal bins (A19).**
   `calibration_curves.py:45-69` draws per-bin means as a plain line/marker
   series — no bin-count encoding, no binomial interval per bin. Given the
   propensity distribution's narrow effective range, sparse tail bins read
   with the same authority as dense central bins.
3. **Disclaimers stripped at export (AUD-REL / AUD-PUB-003).** The
   calibration caveat exists in some surfaces but does not travel with the
   PNG exports — the excerpted artifact loses the qualification.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- One shared reliability-diagram builder (inside the IMP-V02 canonical chart
  library, styled by the IMP-V01 template/palette) consumed by all
  surfaces: static report generator, dashboard, and any notebook rendering.
- Geometry: square plot region, identical `[0,1]` limits on both axes,
  enforced equal aspect so the reference diagonal is exactly 45° on every
  export size.
- Statistics: per-bin sample count encoded visually (marker area or an
  attached count strip/histogram) and a per-bin binomial interval
  (Wilson or Jeffreys) drawn as a band/whisker; bins below a documented
  minimum count rendered visibly de-emphasized.
- The calibration disclaimer (including the IMP-A01 circularity caveat while
  it applies) drawn **inside the figure canvas**, so every export format
  carries it.

**Out-of-Scope:**
- What the model's calibration actually is (IMP-A01 — soft dependency: an
  honestly drawn diagram of a circularly evaluated model still needs the
  caveat, which this chart renders but IMP-A01 defines).
- The dashboard's other parity issues (IMP-V06).
- Palette/template definition itself (IMP-V01).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Geometrically honest diagram (Happy Path)**
- **Given** any surface requesting a reliability diagram at any figure size,
- **When** the shared builder renders it,
- **Then** the plotted region is square with both axes spanning [0,1], the
  reference line's rendered slope is 1 (verifiable from the exported
  figure's axis metadata), and both the dashboard and the static PNG are
  produced by the same builder call.

**Scenario: Bin honesty (Happy Path)**
- **Given** binned predictions where bin 9 holds 12 observations and bin 5
  holds 4,800,
- **When** the diagram renders,
- **Then** bin 5's marker/interval visually dominates bin 9's (area ∝ n or
  count strip), bin 9 carries a wide binomial interval, and any bin under
  the documented minimum (e.g., n < 30) is drawn in the de-emphasized style.

**Scenario: Empty bin (Edge Case)**
- **Given** a probability bin containing zero observations,
- **When** the diagram renders,
- **Then** the bin is omitted (not interpolated across), and the count strip
  shows the gap — the line must never bridge empty bins as if data existed.

**Scenario: Disclaimer travels with the export (Edge Case)**
- **Given** the diagram exported as PNG, embedded in the Quarto report, or
  screenshotted from the dashboard,
- **When** the image is viewed without its surrounding page,
- **Then** the calibration caveat is legible inside the image itself.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing re-implementation drift**
- **Given** any new or existing surface that needs a reliability diagram,
- **When** it is built or modified,
- **Then** it must call the shared builder — a second bespoke
  predicted-vs-observed implementation anywhere in the repo is a
  verification failure (the V6 defect class, structurally re-blocked).

**Scenario: Preventing aspect-ratio regression**
- **Given** any future styling or layout change to the builder,
- **When** the figure regression check runs,
- **Then** a rendered fixture's axis ranges and aspect must still satisfy
  the 1:1 invariant — layout convenience never outranks the diagonal.

**Scenario: Preventing interval-free tails**
- **Given** any rendered bin marker,
- **When** the figure is produced,
- **Then** it must carry its interval; a point-only reliability curve (the
  current state) is not a permitted output mode of the builder.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** bin de-emphasis thresholds apply uniformly; no
  subgroup-specific styling. (Subgroup calibration panels, if added later,
  inherit this same builder.)
- **Performance & decay:** builder renders the canonical ~50k-row propensity
  artifact in < 3 s; dashboard reuse must not add a per-pageview model fit
  (consumes precomputed predictions).
- **Data integrity:** builder validates inputs — predictions in [0,1],
  outcomes binary, n per bin ≥ 0 — and aborts on NaN predictions rather
  than silently dropping rows; dropped-row counts (if any upstream) are
  displayed in the count strip's caption.
- **Reproducibility:** identical inputs produce pixel-identical exports on
  the same platform (fixed fonts/DPI via the IMP-V01 template); bin edges
  are fixed and documented (e.g., 10 uniform bins), not data-dependent.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Shared reliability-diagram builder: 1:1 aspect, bin counts, binomial intervals, in-canvas disclaimer (IMP-V04)
>
> **Problem.** Reliability diagrams are independently implemented in
> `visualization/calibration_curves.py:60-68` (dashboard) and
> `scripts/generate_module_a_report_charts.py:44-54` (static report); none
> enforces equal aspect (the 45° reference renders at arbitrary angle), none
> encodes per-bin n or intervals (`calibration_curves.py:45-69`), and the
> calibration disclaimer does not travel with PNG exports (AUD-REL,
> AUD-PUB-003).
>
> **Acceptance criteria.**
> 1. One shared builder in the canonical chart library (IMP-V02), styled by
>    the shared template (IMP-V01); both dashboard and static report consume
>    it; no other predicted-vs-observed implementation remains (grep-clean).
> 2. Square [0,1]×[0,1] axes with enforced equal aspect on all export sizes.
> 3. Per-bin count encoding + Wilson/Jeffreys interval bands; sub-minimum
>    bins de-emphasized; empty bins omitted, never interpolated.
> 4. Disclaimer (incl. IMP-A01 circularity caveat while applicable) rendered
>    inside the figure canvas on every export surface.
> 5. Figure regression fixture asserting the aspect/limits invariant.
>
> **Blocked by:** IMP-V01, IMP-V02 — label `status:blocked` until both
> close.
>
> **Spec:** `governance/improvement_plan/IMP-V04_reliability-standard.md`

**Labels:** `type:visualization`, `skill:module-a`, `effort:medium`,
`priority:p1`, `status:blocked`
