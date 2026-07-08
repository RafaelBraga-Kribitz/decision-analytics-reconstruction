---
id: IMP-A04
title: "Cleaner & injector integrity: no silent sentinels, truthful flaw taxonomy"
absorbs: [A10, A11, A12, A13]
overlaps_triage: []
priority: P1
effort: medium
depends_on: []
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-A04 — Cleaner & Injector Integrity: No Silent Sentinels, Truthful Flaw Taxonomy

Four defects span `data/cleaner.py`, `data/raw_injector.py`, and their
validators, all of the same shape: a value or a claim is fabricated or
imputed silently, without a tracking flag, or a documented behavior does not
match what the code does.

1. **Flat-rate rural imputation ignores per-department urban share (A10).**
   `_ensure_rural_flag` (`data/cleaner.py:151-157`) falls back to
   `rng.random(len(df)) < rural_p` with `rural_p` read from
   `cleaner_synthetic_defaults.rural_flag_true_rate` (0.383, a single
   *national* constant, `generation.yaml:87-89`) whenever `rural_flag` is
   absent from the raw frame. But `generator.py:178-191`
   (`_sample_rural_flags`) sets rural status **per department** using
   `generation.yaml:41-59`'s `department_urban_share` dict (ranging from
   1.00 in Asuncion to 0.24 in Canindeyu) — a 76-point spread the cleaner's
   fallback path collapses to one national Bernoulli draw. Any entity that
   reaches the cleaner without a `rural_flag` column loses all
   department-level rural signal.
2. **Documented 13th flaw type is never injected (A11).**
   `generation.yaml:193` documents `rural_flag_missing_rate: 1.00  # NUL:
   always absent in raw (always derived)`, and `raw_injector.py:244` lists
   `"NUL_rural_flag"` in `df.attrs["flaw_types_injected"]` as the 13th of
   "all 13 flaw types" the module docstring (`raw_injector.py:3-9`)
   promises. But `inject_flaws` (`raw_injector.py:168-247`) never touches
   `rural_flag` or drops the column — there is no `_inject_rural_flag_null`
   call anywhere in the function body. The flaw is recorded as injected in
   the manifest without ever running, which means the `_ensure_rural_flag`
   imputation path in the cleaner is (by the injector's own accounting)
   *always* exercised, and the claim "13 flaw types injected" is false for
   this one.
3. **Malformed DOB imputed to a literal sentinel date, untracked (A12).**
   `_normalize_dob` (`data/cleaner.py:244-272`) replaces any DOB string that
   fails to split into exactly three `/`-separated parts, fails integer
   parsing, or has an out-of-range year (`< 1900` or `> 2025`) with the
   literal string `"01/01/1980"` (three separate `out.append("01/01/1980")`
   call sites: lines 250, 259, 263). This produces an artificial age-38
   spike in `age_on_event_date` (event date 2018-04-22 minus 1980-01-01 ≈
   38.3 years) for every malformed record, and — unlike `dob_ambiguous`
   (line 125, set from `dob_parsed.isna()`) — there is no flag distinguishing
   "DOB was malformed and imputed" from "DOB parsed cleanly to 1980-01-01."
4. **Age clamp validated by the same bound that created it (A13).**
   `_derive_age_from_dob` (`data/cleaner.py:118-129`) clamps
   `age_on_event_date` to `[18, 115]` (lines 127-128:
   `df.loc[df["age_on_event_date"] < 18, "age_on_event_date"] = 18`, and the
   symmetric line for 115) after computing `age_out_of_range` — but then
   `data/validator.py:63-64` (`_validate_gender_and_age`) asserts
   `df["age_on_event_date"].between(18, 115).all()`, and
   `evaluation/schema_validator.py:63-68`'s Pandera `Check.greater_than_or_equal_to(18)`
   / `Check.less_than_or_equal_to(115)` assert the identical bound. Both
   "validators" can only ever pass, because the value they check was forced
   into that range one line earlier by the same pipeline stage — this is
   tautological validation, not an independent quality gate.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `data/cleaner.py`: `_ensure_rural_flag` (151-157), `_normalize_dob`
  (244-272), `_derive_age_from_dob` (118-129).
- `data/raw_injector.py`: `inject_flaws` (168-247) and its
  `flaw_types_injected` manifest (231-245).
- `config/generation.yaml`: `cleaner_synthetic_defaults.rural_flag_true_rate`
  (line 89) and `flaw_injection.rural_flag_missing_rate` (line 193).
- `data/validator.py:63-64` and `evaluation/schema_validator.py:63-68` (the
  age-bound tautology).

**Out-of-Scope:**
- The fixed-reference-scaling problems in `features/reachability.py` and
  `features/behavioral.py` — `IMP-A05` (those operate downstream of
  cleaning, on already-clean columns).
- Config-to-runtime wiring generally (the `model_params.yaml` "not yet
  wired" header pattern) — `IMP-A06`; this finding's `rural_flag_true_rate`
  reference is already wired (the cleaner does read it), the defect is that
  the *value* is nationally flat, not that it's unwired.
- Department name/typo normalization (`_DEPT_NORMALIZE`,
  `_normalize_departments_and_dedupe`) — not implicated by this finding.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Rural imputation respects department-level urban share (Happy Path)**
- **Given** a raw frame missing the `rural_flag` column entirely, with a
  `department` column populated from `CANONICAL_DEPARTMENTS`,
- **When** `_ensure_rural_flag` (or its replacement) runs,
- **Then** each entity's imputed `rural_flag` is drawn as
  `rng.random() > department_urban_share.get(dept, national_fallback)` —
  the same per-department lookup `generator.py:178-191` uses — not a single
  national Bernoulli(0.383), and the resulting rural share by department in
  the cleaned frame is within a documented tolerance (e.g. ±3 pp) of
  `generation.yaml`'s `department_urban_share` for departments present in
  the imputed subset.

**Scenario: Every documented flaw type is actually injected (Happy Path)**
- **Given** `raw_injector.inject_flaws` runs against a clean frame with
  `config["flaw_injection"]["rural_flag_missing_rate"] = 1.00`,
- **When** the function returns,
- **Then** either (a) `rural_flag` is absent from the returned frame (making
  the cleaner's imputation path the intended, honestly-documented behavior),
  or (b) `"NUL_rural_flag"` is removed from `flaw_types_injected` and the
  docstring's "13 flaw types" claim is corrected to 12 plus a documented
  always-derived column. The verification script asserts that every string
  in `flaw_types_injected` corresponds to an operation the function body
  actually performs on that run.

**Scenario: Malformed DOB imputation is flagged (Edge Case)**
- **Given** a DOB value that fails the three-part split, integer parse, or
  year-range check in `_normalize_dob`,
- **When** cleaning runs,
- **Then** the output frame carries a `dob_imputed_sentinel` (or similarly
  named) boolean column, `True` for every row whose DOB was replaced by the
  fallback rather than parsed, distinguishable from `dob_ambiguous`
  (`cleaner.py:125`, which only tracks post-normalization parse failure, not
  pre-normalization malformation) — and the QA report
  (`_write_qa_report`, cleaner.py:275-289) states the count and resulting
  shift in the age distribution's mode.

**Scenario: Age clamping is counted, not just silently re-asserted (Edge Case)**
- **Given** the `age_out_of_range` flag already computed at
  `cleaner.py:126` before clamping,
- **When** `clean_population` returns,
- **Then** the count of clamped rows (`df["age_out_of_range"].sum()`) is
  surfaced in the QA report and/or an export manifest, and
  `data/validator.py`/`evaluation/schema_validator.py`'s `[18, 115]` checks
  are documented explicitly as **schema-contract** assertions (verifying the
  clamp executed, not independent age-plausibility validation) rather than
  presented as a data-quality gate.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing sentinel imputation from hiding in the distribution**
- **Given** any future imputation added to `cleaner.py` that replaces a
  missing or malformed value with a fixed literal (date, numeric constant,
  or category),
- **When** the imputation runs,
- **Then** it must either (a) sample from a distribution-aware source (the
  relevant per-department/per-stratum prior, as in the rural-flag fix
  above), or (b) set a dedicated `<column>_imputed` boolean flag — a bare
  fixed-literal fallback with no flag is a failing state for this finding's
  verification script.

**Scenario: Preventing a flaw taxonomy claim from outliving its implementation**
- **Given** `raw_injector.py`'s module docstring claim ("Injects all 13 flaw
  types from scope §4.2") and the `flaw_types_injected` list,
- **When** the verification script statically checks each named flaw type
  against a corresponding function call or inline operation in
  `inject_flaws`,
- **Then** any flaw type present in the manifest list but absent from the
  function body is a failing state — this generalizes A11 into a permanent
  regression check, not a one-time fix.

**Scenario: Preventing a validator from checking its own transformation's output**
- **Given** any Pandera check or `QAGateFailure` assertion in
  `validator.py`/`schema_validator.py`,
- **When** the bound it checks is identical to a clamp/normalization bound
  applied earlier in the same pipeline run on the same column,
- **Then** the check must be documented as a **schema-contract** assertion
  (post-condition of the transformation) rather than an independent
  data-quality signal, and the QA report must separately surface the
  pre-clamp `age_out_of_range` rate so a reader can see how much clamping
  actually happened.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** the rural-flag fix directly affects
  `rural_flag`, which feeds `metro_flag`, segmentation's `FEATURE_COLUMNS`,
  and the propensity model's department-adjacent features; re-validate that
  the corrected per-department imputation does not shift national rural
  share by more than the ~1pp expected from sampling noise at whatever `n`
  triggers the fallback path (the fallback should be rare in practice since
  `generator.py` populates `rural_flag` upstream — confirm the fallback path
  is actually reachable only via `raw_injector`'s `NUL_rural_flag` gap, and
  fix or remove that gap per Scenario 2 above).
- **Performance & decay:** no runtime-sensitive change; imputation remains a
  single vectorized pass per column.
- **Data integrity:** `evaluation/schema_validator.py` must gain (or the QA
  report must surface) counts for: `dob_imputed_sentinel` rate,
  `age_out_of_range` (pre-clamp) rate, and per-department imputed
  `rural_flag` rate — each as an observable metric, not just a boolean
  pass/fail on the post-transformation bound.
- **Reproducibility:** all new sampling (department-aware rural imputation)
  must draw from the `rng` already threaded through `clean_population`
  (`make_rng(seed)`, cleaner.py:222), preserving exact reproducibility for a
  fixed seed.

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Cleaner rural-flag fallback ignores department urban share; documented 13th flaw type never injected; DOB imputation and age clamp untracked"
category: fake_completion
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 0
evidence: |
  cleaner.py:151-157 _ensure_rural_flag falls back to a flat national
  Bernoulli(0.383) (generation.yaml:89) ignoring department_urban_share
  (generation.yaml:41-59) that generator.py:178-191 _sample_rural_flags uses
  upstream (spread from 1.00 Asuncion to 0.24 Canindeyu).
  generation.yaml:193 documents rural_flag_missing_rate: 1.00 "NUL: always
  absent in raw"; raw_injector.py:244 lists "NUL_rural_flag" in
  flaw_types_injected; but inject_flaws (raw_injector.py:168-247) never
  operates on rural_flag — the 13th documented flaw type is never actually
  injected, making the "13 flaw types" claim (module docstring, lines 3-9)
  false and leaving the cleaner's fallback path as the only path exercised.
  cleaner.py:244-272 _normalize_dob replaces malformed DOB with the literal
  "01/01/1980" (3 call sites: lines 250, 259, 263) with no tracking flag,
  producing an untracked age-38 spike distinct from dob_ambiguous
  (line 125).
  cleaner.py:126-128 clamps age to [18,115]; validator.py:63-64 and
  evaluation/schema_validator.py:63-68 assert the identical bound
  post-clamp — tautological validation.
verification_script: scripts/check_cleaner_injector_integrity.py
notes: |
  Proposed script behavior: (1) statically parse raw_injector.inject_flaws
  and confirm every string in the hardcoded flaw_types_injected list
  corresponds to a function call/inline op touching a distinct column —
  fail if a listed flaw type (e.g. NUL_rural_flag) has no corresponding
  operation; (2) confirm _ensure_rural_flag's fallback path references
  department_urban_share (or an equivalent per-department dict), not a
  single scalar constant; (3) confirm a dob-imputation tracking column
  exists and is set wherever _normalize_dob's literal-fallback branches
  fire; (4) confirm the QA report or an export manifest surfaces
  age_out_of_range and the new dob-imputed rate as counted metrics, not only
  the post-clamp assertion.
  Spec: governance/improvement_plan/IMP-A04_cleaner-injector-integrity.md
```
