---
id: IMP-C06
title: "Small-sample honesty: walk-forward power limits and exit-model reliability gating"
absorbs: [C10, C12]
overlaps_triage: [AUD-C7, AUD-PPC]
priority: P1
effort: medium
depends_on: [IMP-C01]
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-C06 — Small-Sample Honesty

Two Module C validation surfaces present statistically underpowered checks as
meaningful evidence:

1. **Walk-forward "proof" without power (C10).**
   `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/validation/walk_forward.py:14-24`
   documents eight tracking polls and six holdouts; `coverage_80pct` /
   `coverage_95pct` (`walk_forward.py:257-258`) can only take values k/6. A
   nominal 95% interval evaluated on 6 trials has essentially no power to
   detect miscalibration (the exact binomial 95% CI on observed coverage
   6/6 spans roughly [0.54, 1.0]). The test suite encodes an even weaker
   bar — `tests/test_walk_forward.py:81` asserts `coverage_95pct >= 2/3` on
   **three** synthetic holdouts — and
   `reports/C_research_proof_table.md:18-19` presents exactly that bar as a
   "proof" gate. A smoke test is being marketed as evidence.
2. **Exit model runs below its own reliability floor, unflagged (C12).**
   `METHODOLOGY.md:194` states the exit quick-count "requires ≥ 2
   observations; typically unreliable with < 5 waves," but
   `models/exit/exit_model.py:48-61` (`fit_exit_quickcount`) stubs only at
   `shape[0] < 2` and otherwise runs full NUTS with 2–4 rows, emitting
   posterior means/HDIs with no caveat attached to the output rows. The
   committed fixture (`tests/fixtures/polls_raw_fixture.csv`) has exactly 4
   exit rows — production example data sits inside the self-documented
   unreliable band with no flag. Triage rows AUD-C7 (exit-model null
   coefficients unlabeled) and AUD-PPC (PPC promoted on n=4 with firm
   labels) are presentation symptoms of the same small-n overclaim.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- Every published coverage claim from walk-forward validation accompanied by
  its exact binomial confidence interval and holdout count n — in the
  metrics artifact, the proof table, and any caption quoting it.
- `C_research_proof_table.md` (and any surface using "proof" language for
  these checks) reworded to smoke-test / plumbing-check language, with the
  power limitation stated in the same row.
- A machine-readable `low_n` (or `reliability_band`) flag column on exit
  quick-count outputs whenever the observation count is below the documented
  ≥5-wave threshold; on-report captions render the flag.
- Null/indistinguishable-from-zero exit-model coefficients labeled as such
  in exports (AUD-C7 slice).
- A recurrence invariant verifying (a) proof-table language and CI
  disclosure, (b) presence and correctness of the exit-model flag.

**Out-of-Scope:**
- Increasing the number of holdouts or polls (data acquisition is not in this
  repo's control; the fix is honest framing, not fabricated n).
- The convergence of the samplers themselves (IMP-C01; this document assumes
  a valid posterior — hence the dependency, since re-stating coverage on a
  non-converged model would be re-litigating C1's output).
- PPC chart band encodings (IMP-V05).

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Coverage claim with its uncertainty (Happy Path)**
- **Given** a completed walk-forward run with n holdouts,
- **When** the metrics artifact is written,
- **Then** each coverage figure appears as `k/n` with its exact binomial 95%
  CI (e.g., "95%-interval coverage: 6/6 [0.54, 1.00]"), and any surface
  quoting the number quotes the interval with it.

**Scenario: Exit model in the unreliable band (Edge Case)**
- **Given** an exit dataset with 2 ≤ rows < 5,
- **When** `fit_exit_quickcount` produces output rows,
- **Then** every output row carries `low_n: true` (and the wave count), the
  Quarto/report rendering of those rows displays the unreliability caveat,
  and the run summary counts low-n exit fits — the model may run, but it may
  not publish unflagged results from inside its own documented unreliable
  regime.

**Scenario: Exit model at or above the floor (Happy Path)**
- **Given** an exit dataset with ≥ 5 waves,
- **When** the model fits,
- **Then** `low_n: false` and no caveat is injected — the flag is
  informative, not decorative noise on every row.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing "proof" language on powerless checks**
- **Given** any committed artifact describing walk-forward or exit-model
  validation,
- **When** the check's design cannot reject a meaningfully miscalibrated
  model (e.g., binomial CI width > 0.3 on the coverage estimate),
- **Then** the artifact must not use the words "proof", "validated", or
  "calibrated" for that check without the power qualifier in the same
  sentence — evidentiary language is bound to evidentiary power.

**Scenario: Preventing threshold drift between doc and gate**
- **Given** METHODOLOGY.md's documented reliability threshold (≥ 5 waves),
- **When** the exit model's flagging logic evaluates an input,
- **Then** the threshold used must be read from a single shared constant/
  config also cited by METHODOLOGY.md — the doc saying 5 while the code
  gates at 2 (the current state) must be structurally impossible, not just
  currently fixed.

**Scenario: Preventing flag stripping downstream**
- **Given** a `low_n: true` exit output row,
- **When** any downstream table, chart, or dashboard consumes it,
- **Then** the consuming surface must render the caveat or exclude the row —
  dropping the flag column while keeping the estimate is a verification
  failure.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — no estimand changes; this document
  changes disclosure and gating only.
- **Performance & decay:** binomial CI computation is negligible; the
  recurrence-invariant script is static (grep + fixture-run of the flag
  logic) and must complete in < 10 s within `make verify`.
- **Data integrity:** exit output schema gains the `low_n` boolean and
  `n_waves` integer columns (nullable: false); the contract validator
  (IMP-C07 when available) enforces their presence.
- **Reproducibility:** flags are pure functions of input row counts;
  identical fixtures produce identical flags.

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Underpowered validation presented as proof; exit model publishes unflagged results below its documented reliability floor"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: <filing date>
closed_at: null
recurrence_count: 0
evidence: |
  validation/walk_forward.py:14-24,257-258 — coverage on 6 holdouts (test
  suite asserts >= 2/3 on THREE holdouts, tests/test_walk_forward.py:81) is
  presented by reports/C_research_proof_table.md:18-19 as a "proof" gate
  despite having no power to detect miscalibration. METHODOLOGY.md:194
  documents the exit quick-count as "typically unreliable with < 5 waves,"
  but models/exit/exit_model.py:48-61 runs full NUTS from 2 rows and emits
  posterior means/HDIs with no output flag; the committed fixture has
  exactly 4 exit rows.
verification_script: scripts/check_small_sample_honesty.py
notes: |
  Proposed script behavior: (1) parse the walk-forward metrics artifact and
  require each coverage figure to carry k/n and a binomial CI; (2) grep
  C_research_proof_table.md (and successors) — the walk-forward row must not
  contain proof/validated language without the power qualifier; (3) run
  fit_exit_quickcount on a 4-row fixture and assert every output row carries
  low_n: true and n_waves: 4, and on a 6-row fixture low_n: false; (4)
  assert the reliability threshold is a single shared constant cited by both
  METHODOLOGY.md and the flag logic.
  Spec: governance/improvement_plan/IMP-C06_small-sample-honesty.md
  Depends on IMP-C01: coverage statements are re-generated on the converged
  model before this finding's language checks are finalized.
```
