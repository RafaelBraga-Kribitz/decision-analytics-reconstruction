---
id: IMP-V02
title: "Chart single-sourcing: subordinate the notebook pipeline; 100% manifest lineage coverage"
absorbs: [V4]
overlaps_triage: [AUD-XCUT-007, AUD-PUB-002]
priority: P1
effort: high
depends_on: []
soft_depends_on: []
queue: dual
target_repo: decision-analytics-reconstruction
issue: 67
status: draft
---

# IMP-V02 — Chart Single-Sourcing

Two independent pipelines produce "the same" EDA charts:

- `reports/eda/generate_eda.py` (3,062 lines) — the canonical figure factory,
  and the only generator `governance/FIGURE_MANIFEST.yaml` knows about (every
  `figures:` entry at `FIGURE_MANIFEST.yaml:7-130` names
  `generator: reports/eda/generate_eda.py`);
- `reports/eda/build_notebook.py` (1,952 lines) — a second, independent
  re-implementation of the same chart IDs (A-series, B-series, C-series,
  S-series) as notebook code cells. It appears **zero** times in the
  manifest: the notebook pipeline is invisible to lineage.

The duplication has already produced divergence. The notebook's B8 cell
(`build_notebook.py:1101-1129`) draws horizontal bars of `reach_cap` with a
twinx line of `expected_contacts` — while canonical B8
(`generate_eda.py:1268-1330`) draws vertical grouped bars of `reach_cap` vs
`expected_contacts` with a twinx line of `total_budget`. Different chart
form, different metric pairing, same chart ID. F-049
(`governance/findings/F-049-eda-notebook-chart-parity.yaml`) caught and fixed
an earlier instance of exactly this class (notebook C2 plotting the wrong
estimand under the canonical C2 title) and installed
`scripts/check_eda_notebook_chart_parity.py` — but the structural root cause
remains: two codebases, one chart vocabulary, drift guaranteed.

Two open triage rows share this root cause: `AUD-XCUT-007` (chart cull to ~5
Module C + 6 Module B keepers — impossible to execute confidently while a
shadow pipeline regenerates culled charts) and `AUD-PUB-002` (GitHub Pages
report renders a useless 280px capture — a publication surface consuming
figures outside the manifest's lineage guarantees).

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- One chart library both surfaces consume: the canonical chart functions
  (currently the `chart_*` bodies in `generate_eda.py`) factored so that
  notebook cells **call** them and never re-implement them. A notebook cell
  for chart X becomes an invocation + rendered output of the canonical
  function for X, not a second drawing of X.
- `governance/FIGURE_MANIFEST.yaml` coverage raised to 100% of produced
  figures: every figure emitted by any pipeline (static PNG factory,
  notebook build, and any publication surface that captures figures) has
  exactly one manifest entry naming exactly one generator.
- A manifest-coverage recurrence invariant (verification script) that fails
  when (a) a figure file exists under `reports/` with no manifest entry,
  (b) a manifest entry's generator does not exist, or (c) two generators
  claim one figure path.
- Retiring or subordinating `build_notebook.py`'s chart-drawing code: the
  file may keep its cell-assembly and markdown-narrative role, but its
  `code(...)` cells must not contain independent plotting logic for
  manifest-registered chart IDs.

**Out-of-Scope:**
- Which colors and template the single library uses (`IMP-V01`; the two IMPs
  are independent — this one is about *how many* implementations exist,
  that one about what they share).
- The actual chart cull decision for AUD-XCUT-007 (which keepers survive) —
  this IMP makes the cull executable by guaranteeing a culled chart has no
  shadow generator; the cull itself is separate triage work.
- Fixing individual chart encodings (`IMP-V05`) or the reliability diagram
  (`IMP-V04`); those land *in* the single library this IMP creates, hence
  their `depends_on` pointing here.
- The single-writer guarantee for `reports/module_a/shap_summary.png`
  specifically (`IMP-V03`, already specified; this IMP generalizes the same
  invariant to all figures).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Notebook cell renders the canonical chart (Happy Path)**
- **Given** the refactored chart library exposes the canonical B8 function
  (today `chart_b8` at `generate_eda.py:1268-1330`),
- **When** `build_notebook.py` assembles the notebook and the notebook is
  executed,
- **Then** the B8 cell's output figure is produced by calling that canonical
  function — the cell source contains an import + call, not `ax1.barh`/
  `ax2.plot` re-implementations — and the rendered figure shows the same
  chart form and metric pairing (`reach_cap` vs `expected_contacts` grouped
  bars + `total_budget` line) as `B8_reach_caps_vs_contacts.png`.

**Scenario: New figure without manifest entry (Edge Case)**
- **Given** a PR adds a new chart function that writes
  `reports/eda/A14_new_chart.png` but does not add a
  `governance/FIGURE_MANIFEST.yaml` entry,
- **When** the manifest-coverage invariant runs (locally via `make verify`
  or in the Adversary CI job),
- **Then** it exits non-zero, naming `reports/eda/A14_new_chart.png` as an
  unregistered figure, before the PR can merge.

**Scenario: Second generator claims an existing figure path (Edge Case)**
- **Given** any script or notebook cell other than the manifest-registered
  generator writes to a path listed in `FIGURE_MANIFEST.yaml`,
- **When** the invariant runs,
- **Then** it exits non-zero, naming both claimed generators and the
  contested path — one figure, one generator, no exceptions.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing re-implementation drift (the B8/C2 recurrence class)**
- **Given** a notebook cell whose markdown or title claims a canonical chart
  ID (A1–A13, B1–B8, C-series, S1–S5),
- **When** the parity/lineage check inspects the cell source,
- **Then** the check fails if the cell contains matplotlib/plotly drawing
  calls instead of an invocation of the canonical library function for that
  ID — the F-049 failure mode (same ID, different estimand) must be
  structurally impossible, not just currently absent.

**Scenario: Preventing publication surfaces from bypassing lineage**
- **Given** a publication surface (GitHub Pages workflow, Quarto document,
  README) that embeds a figure,
- **When** the figure it embeds is checked against the manifest,
- **Then** every embedded figure path must resolve to a manifest entry; a
  surface that screenshots or re-captures charts outside the manifest (the
  AUD-PUB-002 280px capture) is a failing state — publication must consume
  manifest-registered artifacts directly.

**Scenario: Preventing silent manifest rot**
- **Given** a manifest entry whose `generator` file has been deleted or
  renamed,
- **When** the invariant runs,
- **Then** it fails, naming the dangling entry — the manifest may never
  drift into describing generators that no longer exist.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — no model behavior changes; this is a
  chart-lineage and code-deduplication guarantee.
- **Performance & decay:** the manifest-coverage invariant is static
  (filesystem walk + YAML parse + source grep, no chart rendering) and must
  complete in under 10s. The notebook build may become slower if cells now
  execute canonical functions; the full notebook execution must stay under
  the existing CI time budget for the EDA job, or the notebook is built with
  pre-rendered figure outputs from the canonical factory run.
- **Data integrity:** both surfaces must consume the same canonical data
  inputs (`data/processed/` parquet artifacts named in
  `data/processed/model_run_manifest.json`); the refactor must not introduce
  a notebook-local data-loading path that could diverge from the factory's
  (`FIGURE_MANIFEST.yaml:4-5` binds figures to
  `canonical_sample_size: 50000` and a `run_id` — that binding must hold for
  notebook-rendered figures too).
- **Reproducibility:** rendering the same chart ID via the factory and via
  the notebook against the same pipeline run must produce visually
  identical figures (same function, same data, same seed); any intentional
  surface-specific difference (e.g. interactive vs static) must be a
  parameter of the one canonical function, not a fork.

## 5. Queue Stub (ready to file)

`queue: dual` — the **finding** owns the manifest-coverage recurrence
invariant (governance: write the verification script, wire it into
`make verify`/Adversary, close per AUDIT_PROCEDURE.md); the **issue** owns
the refactor that makes the invariant pass (subordinating
`build_notebook.py`'s chart cells to the canonical library).

### Finding stub (governance queue)

```yaml
id: F-XXX            # assigned at filing time
title: "Notebook chart pipeline invisible to figure manifest; duplicate generators drift (B8)"
category: fragmented_standards
kind: recurrence_invariant
status: open
opened_at: <filing date>
closed_at: null
recurrence_count: 1  # F-049 previously caught the same class (notebook C2 estimand drift)
evidence: |
  governance/FIGURE_MANIFEST.yaml:7-130 — every figures: entry names
  reports/eda/generate_eda.py as generator; reports/eda/build_notebook.py
  (1,952 lines, re-implementing the same chart IDs) appears zero times, so
  the notebook pipeline has no lineage.
  reports/eda/build_notebook.py:1101-1129 — notebook B8 draws horizontal
  reach_cap bars + twinx expected_contacts line.
  reports/eda/generate_eda.py:1268-1330 — canonical B8 draws vertical grouped
  reach_cap/expected_contacts bars + twinx total_budget line. Same ID,
  different chart form, different metric pairing.
  governance/findings/F-049-eda-notebook-chart-parity.yaml — prior instance
  of the identical drift class (notebook C2), fixed point-wise; the
  structural duplication that produced it was left in place.
verification_script: scripts/check_figure_manifest_coverage.py
notes: |
  Proposed script behavior: (1) walk reports/**/ for figure files (png/svg/
  html) and assert each has exactly one FIGURE_MANIFEST.yaml entry; (2)
  assert each manifest entry's generator path exists; (3) assert no figure
  path is claimed by two generators; (4) scan build_notebook.py code cells
  for matplotlib/plotly drawing calls inside cells titled with a canonical
  chart ID and fail on a match (re-implementation guard, generalizing
  scripts/check_eda_notebook_chart_parity.py from per-chart parity to
  structural single-sourcing).
  Spec: governance/improvement_plan/IMP-V02_chart-single-sourcing.md
```

### Issue stub (feature queue)

```
Title: Single-source all EDA charts: notebook cells call the canonical chart library; retire duplicate drawing code

## Problem
reports/eda/build_notebook.py (1,952 lines) independently re-implements the
chart IDs that reports/eda/generate_eda.py (3,062 lines, the canonical
factory) already produces. governance/FIGURE_MANIFEST.yaml lists only
generate_eda.py as a generator, so the notebook pipeline is invisible to
lineage. The pipelines have already diverged: notebook B8
(build_notebook.py:1101-1129) plots horizontal reach_cap bars with a twinx
expected_contacts line, while canonical B8 (generate_eda.py:1268-1330) plots
grouped reach_cap/expected_contacts bars with a twinx total_budget line —
same ID, different chart, different metrics. F-049 fixed the same drift
class for C2 point-wise; the structural duplication remains and will keep
regenerating instances. Open triage rows AUD-XCUT-007 (chart cull) and
AUD-PUB-002 (Pages 280px capture) share this single-sourcing root cause.

## Evidence
- reports/eda/build_notebook.py:1101-1129 — divergent notebook B8.
- reports/eda/generate_eda.py:1268-1330 — canonical B8.
- governance/FIGURE_MANIFEST.yaml:7-130 — generator field never names
  build_notebook.py.
- governance/findings/F-049-eda-notebook-chart-parity.yaml — prior drift
  instance, same class.
- governance/ISSUE_TRIAGE_MASTER.yaml:172,218 — AUD-XCUT-007, AUD-PUB-002.

## Acceptance criteria
1. Canonical chart functions are importable as a library (factored out of or
   exposed by generate_eda.py).
2. Every build_notebook.py chart cell for a canonical ID calls the library
   function; no independent matplotlib/plotly drawing code remains in cells
   claiming canonical chart IDs.
3. FIGURE_MANIFEST.yaml covers 100% of figures produced under reports/, one
   generator per figure.
4. scripts/check_figure_manifest_coverage.py (from the paired finding)
   passes; scripts/check_eda_notebook_chart_parity.py still passes.
5. Publication surfaces (GitHub Pages, Quarto) embed manifest-registered
   figure paths only.

## Verification
- Run scripts/check_figure_manifest_coverage.py — exits 0 with [PASS].
- Execute the built notebook end-to-end; B8 output matches
  B8_reach_caps_vs_contacts.png in form and metric pairing.
- make verify green.

## Spec
governance/improvement_plan/IMP-V02_chart-single-sourcing.md

## Labels
type:refactor, skill:shared, effort:high, priority:p1, status:claude-ready
```
