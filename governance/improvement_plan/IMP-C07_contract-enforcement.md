---
id: IMP-C07
title: "Contract validator full-spec enforcement: every declared constraint checked at runtime"
absorbs: [C11]
overlaps_triage: []
priority: P1
effort: medium
depends_on: []
soft_depends_on: []
queue: issues
target_repo: decision-analytics-reconstruction
issue: 64
status: filed
---

# IMP-C07 — Contract Validator Full-Spec Enforcement

The cross-module schema contracts in `schema_contracts/` declare rich
constraints, but the generic validator enforces almost none of them:

- `module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/data/contract_validate.py:22-34`
  (`validate_dataframe_contract`) checks only (a) required columns present
  and (b) no duplicate `unique_key`.
- The contracts it validates declare much more:
  `schema_contracts/daily_posterior_forecast.yaml` declares
  `allowed_values: [A, B]` for `calibration_series` and `nullable: false`
  on every field; `schema_contracts/allocation_output.yaml` declares
  `min`/`max` bounds, `pattern` regexes, and `row_count.exact`. None of
  `nullable`, `allowed_values`, `min`, `max`, `pattern`, or `row_count` is
  checked — a NULL date, an out-of-range HDI, or a non-canonical
  `calibration_series` value passes the gate silently.
- Module B's bespoke `utils/allocation_output_gate.py:34-115` is stronger
  for its one contract (canonical labels, row count, budget envelope,
  coverage floor) but inconsistent with the generic path, and neither
  enforces `tc_rate_pyg_per_usd`'s declared `[4500, 7000]` bound or
  `reach_utilization`'s declared `max: 1.5` at runtime.

The effect: the schema contracts function as documentation, not guardrails.
Every "abort on schema drift" NFR in the other IMP documents presumes this
validator actually enforces what the YAML declares — which is why this
change belongs to Phase 1.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `validate_dataframe_contract` (or a successor shared validation core)
  enforcing every constraint key the contract YAMLs declare: required
  columns, `dtype`, `nullable`, `allowed_values`, `min`/`max`, `pattern`,
  `unique_key`, `row_count` (`exact`/`min`/`max`).
- A conformance matrix artifact: constraint key × contract file → enforced
  (yes/no/not-declared), regenerated with the validator so coverage
  regressions are visible.
- Module B's `allocation_output_gate` reconciled to call the shared core for
  the declared-constraint portion, keeping its bespoke domain checks (budget
  envelope, coverage floor) layered on top.
- Failure semantics: abort with a structured error naming contract, field,
  constraint, and offending row indices (bounded sample, not the full dump).
- Every producer that writes a contracted artifact calls the validator
  before write (Module A exports, Module B allocation output, Module C
  posterior/geo/MC artifacts).

**Out-of-Scope:**
- Adding new constraints to contracts (e.g., IMP-C05's HDI-ordering bound
  lands in that document's PR; this document makes whatever is declared
  enforceable).
- The B→C handshake Pydantic bound fix (IMP-B03 owns `week_index le=60`).
- DVC pipeline wiring.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Declared bound enforced (Happy Path)**
- **Given** `allocation_output.yaml` declaring
  `tc_rate_pyg_per_usd: {min: 4500, max: 7000}`,
- **When** an allocation output row carries `tc_rate_pyg_per_usd: 7200`,
- **Then** validation aborts before the artifact is written, and the error
  names the contract, the field, the violated bound, and the row index.

**Scenario: Allowed-values enforcement (Happy Path)**
- **Given** `daily_posterior_forecast.yaml` declaring
  `calibration_series: {allowed_values: [A, B]}`,
- **When** a frame contains `calibration_series: "C"` in any row,
- **Then** validation fails with the offending value and count — it must not
  pass because the column merely exists.

**Scenario: NULL in a non-nullable field (Edge Case)**
- **Given** any contract field declared `nullable: false`,
- **When** the produced frame contains one NaN/None in that column,
- **Then** validation aborts; partial-null columns are never truncated,
  imputed, or passed through by the validator itself (imputation is the
  producer's documented job, upstream — the gate only refuses).

**Scenario: Contract with unknown constraint key (Edge Case)**
- **Given** a contract YAML containing a constraint key the validator does
  not implement (typo or future extension),
- **When** the validator loads the contract,
- **Then** it fails loudly at load time ("unknown constraint key X in
  contract Y") — silently skipping unrecognized constraints would recreate
  today's decorative-schema problem one key at a time.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing partial enforcement without disclosure**
- **Given** the shared validator at any future revision,
- **When** the conformance matrix is regenerated,
- **Then** any declared-but-unenforced constraint key appears as an explicit
  `no` row; a mismatch between the matrix and the validator's actual
  behavior (verified by mutation fixtures) is a failing state.

**Scenario: Preventing gate bypass by producers**
- **Given** any pipeline stage that writes a `schema_contracts/`-governed
  artifact,
- **When** it writes,
- **Then** the write path must pass through the validator; a producer
  writing the parquet/CSV directly without the gate call is a verification
  failure (checkable statically by call-site inventory).

**Scenario: Preventing error-message data leaks**
- **Given** a validation failure on a large frame,
- **When** the structured error is emitted,
- **Then** it includes at most a bounded sample of offending values (≤ 5)
  and row indices — never the full frame dump into logs/CI output.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A — data plumbing; no estimand changes.
- **Performance & decay:** full-constraint validation of the largest
  contracted artifact (Module A's ~50k-row canonical parquet) must complete
  in < 10 s; vectorized checks only (no per-row Python loops).
- **Data integrity:** this document IS the data-integrity enforcement layer;
  its own abort conditions are the scenarios above. The conformance matrix
  is committed and diffs reviewable.
- **Reproducibility:** validation outcome is a pure function of
  (frame, contract); mutation fixtures (one deliberately violating frame per
  constraint key) run in CI to prove each check can actually fail.

## 5. Queue Stub (ready to file)

**GitHub issue body:**

> **Title:** Shared contract validator: enforce every declared constraint (nullable, allowed_values, min/max, pattern, row_count) (IMP-C07)
>
> **Problem.** `data/contract_validate.py:22-34` checks only column presence
> and unique-key duplicates, while `schema_contracts/*.yaml` declare
> `nullable`, `allowed_values`, `min`/`max`, `pattern`, and `row_count` —
> none enforced. A NULL date, an out-of-range HDI, or `calibration_series:
> "C"` passes the gate silently. Module B's bespoke gate
> (`utils/allocation_output_gate.py:34-115`) is stronger but inconsistent,
> and neither enforces `tc_rate_pyg_per_usd` `[4500,7000]` or
> `reach_utilization` `max: 1.5` at runtime.
>
> **Acceptance criteria.**
> 1. Shared validation core enforces all declared constraint keys; unknown
>    keys abort at contract load.
> 2. Mutation fixtures prove each constraint can fail (one violating frame
>    per key, asserted in tests).
> 3. Conformance matrix artifact (constraint × contract → enforced)
>    committed and regenerated with the validator.
> 4. All producers of contracted artifacts route writes through the gate
>    (call-site inventory in the PR description).
> 5. Module B's gate layered on the shared core; behavior for its bespoke
>    checks unchanged.
> 6. Largest artifact validates in < 10 s (vectorized).
>
> **Verification.** Run the pipeline on fixtures; inject each mutation
> fixture and observe the named abort; confirm `make verify` and existing
> module tests stay green.
>
> **Spec:** `governance/improvement_plan/IMP-C07_contract-enforcement.md`

**Labels:** `type:data`, `skill:shared`, `effort:medium`, `priority:p1`,
`status:claude-ready`
