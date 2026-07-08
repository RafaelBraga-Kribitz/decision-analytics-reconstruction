---
id: IMP-B04
title: "Silent-substitution elimination in the Module B data layer"
absorbs: [B7, B8]
overlaps_triage: []
priority: P1
effort: low
depends_on: []
soft_depends_on: []
queue: findings
target_repo: decision-analytics-reconstruction
issue: null
status: draft
---

# IMP-B04 — Silent-Substitution Elimination in the Module B Data Layer

Two data-layer fallbacks, both silent, both feeding a ~$6M allocation
objective without leaving a trace:

**B7 — FX spread fallback.** `fx/spread_model.py:22` defines
`DEFAULT_SPREAD_PYG_PER_USD: Final[float] = 50.0`. `apply_retail_spread`'s
inner `_spread_for_row` (`fx/spread_model.py:92-99`) looks up each week's
percentage spread from `spread_cfg["series_b_weekly"]`; when a week's key is
absent, it falls back to `DEFAULT_SPREAD_PYG_PER_USD / float(row["tc_ref"])`
(line 99) — no basis documented for `50.0`, no warning logged, no record of
*which* weeks fell back. Because the fallback is silent, a config file
missing an entire week (or missing the whole `series_b_weekly` block) would
produce a plausible-looking `tc_retail` column with no signal that any of it
came from a guessed constant instead of `config/fx_retail_spread_prior.yaml`.

**B8 — cleaning-layer row drops.** `data/cleaner.py` has three near-identical
gates, each of which silently discards rows failing a `valid_mask`:
`clean_budget_lines` (`:198-221`), `clean_volunteer_logs` (`:261-283`), and
`clean_media_buy_sheet` (`:328-337`). Each `valid_mask` rejects rows with
unrecognized currency (`_canonical_currency` returns `None`), unparsable
amounts (`_parse_locale_number` returns `None`), non-canonical channel/
department labels (`_canonical_channel`/`_canonical_department` return
`None`), or non-positive amounts/contacts/impressions. None of the three
functions counts how many rows were dropped, logs a reason, or emits a
rejection artifact — the caller (`clean_directory`, `:358-383`) receives only
the surviving rows. For financial inputs anchoring the campaign's total
spend envelope, a vendor extract that is 30% garbled currency codes and a
vendor extract that is perfectly clean produce indistinguishable downstream
frames.

## 1. Define the Scope (The Data Guardrails)

**In-Scope:**
- `apply_retail_spread` / `_spread_for_row`
  (`fx/spread_model.py:46-105`, fallback path at `:98-99`): every fallback
  application must emit a structured record (week, `tc_ref` used, computed
  fallback percentage) to a rejection/fallback report, and the aggregate
  fallback rate (weeks-on-fallback ÷ total weeks in the run) is checked
  against a zero-tolerance gate.
- `clean_budget_lines`, `clean_volunteer_logs`, `clean_media_buy_sheet`
  (`data/cleaner.py:160-355`) and their shared caller `clean_directory`
  (`:358-383`): every dropped row must be recorded with its `row_id` and the
  specific failing predicate (bad currency, unparsable amount, non-canonical
  channel, non-canonical department, non-canonical week, non-positive
  amount), aggregated into counts by reason per source file.
- A published rejection-report artifact (e.g.
  `reports/module_b/data_rejection_report.csv` for cleaning drops and
  `reports/module_b/fx_fallback_report.csv` for FX fallback weeks) referenced
  from the pipeline run summary.
- Gate thresholds: **any** week on FX fallback (>0%) fails the gate for that
  run; **more than 2%** of rows dropped for a given source file
  (`budget_lines_raw.csv`, `volunteer_logs_raw.csv`,
  `media_buy_sheet_raw.csv`) fails the gate.

**Out-of-Scope:**
- Objective-coefficient provenance (`IMP-B01`).
- Module A input uncertainty (`IMP-B02`).
- MILP degenerate-case handling and the handshake `week_index` bound
  (`IMP-B03`).
- Changing `_canonical_channel`/`_canonical_department`/`_parse_locale_number`
  parsing logic itself (their *matching* behavior is out of scope; only the
  *silence* of their rejection path is in scope).
- Deciding what the "right" FX spread basis should be (a data-sourcing
  question) — this IMP only requires that the fallback, wherever triggered,
  is visible and gated, not that `DEFAULT_SPREAD_PYG_PER_USD` be replaced
  with a better-justified number.

## 2. Data-Driven "Given-When-Then" Scenarios

**Scenario: Complete FX config produces zero fallback weeks (Happy Path)**
- **Given** `config/fx_retail_spread_prior.yaml`'s `series_b_weekly` block
  has an entry for all 14 weeks in `WEEK_LABELS` (`constants.py:117`,
  `2018-W01` … `2018-W14`),
- **When** `apply_retail_spread` runs over the daily series,
- **Then** `reports/module_b/fx_fallback_report.csv` is emitted with zero
  rows (no week used `DEFAULT_SPREAD_PYG_PER_USD`), and the run's gate check
  passes.

**Scenario: A missing week triggers a visible, gated fallback (Edge Case)**
- **Given** `config/fx_retail_spread_prior.yaml`'s `series_b_weekly` block is
  missing the key `"2018-W07"`,
- **When** `apply_retail_spread` processes rows for that week,
- **Then** `_spread_for_row` still returns
  `DEFAULT_SPREAD_PYG_PER_USD / tc_ref` (unchanged runtime behavior), but
  `reports/module_b/fx_fallback_report.csv` gains one row for
  `iso_week="2018-W07"` recording the fallback percentage used, and the gate
  (`>0% weeks on fallback fails`) marks that run's FX layer as
  `gate_status: FAIL` rather than silently succeeding.

**Scenario: Dirty vendor extract produces a rejection report with reason counts (Edge Case)**
- **Given** `budget_lines_raw.csv` has 500 rows, of which 40 have a
  currency token outside `{usd, us$, $, pyg, gs., gs, ₲}` and 15 have
  `amount_text` that fails `_parse_locale_number`,
- **When** `clean_budget_lines` runs,
- **Then** `reports/module_b/data_rejection_report.csv` gains 55 rows (or one
  aggregated row per reason with `count=40` for
  `reason="unrecognized_currency"` and `count=15` for
  `reason="unparsable_amount"`), the returned `BudgetLineFrame` has 445 rows,
  and because `55/500 = 11% > 2%`, the source's gate check reports
  `gate_status: FAIL` for `budget_lines_raw.csv`.

## 3. Specify Undesirable Behaviors (Negative Constraints)

**Scenario: Preventing unlogged FX fallback**
- **Given** any week processed by `apply_retail_spread` without a matching
  `series_b_weekly` key,
- **When** the fallback branch (`fx/spread_model.py:98-99`) executes,
- **Then** the absence of a corresponding row in `fx_fallback_report.csv` for
  that week is itself a test failure — the fallback must never execute
  without a matching disclosure record.

**Scenario: Preventing unlogged row drops**
- **Given** any row excluded by a `valid_mask` in `clean_budget_lines`,
  `clean_volunteer_logs`, or `clean_media_buy_sheet`,
- **When** `clean_directory` completes,
- **Then** `sum(reason counts in data_rejection_report.csv for that source)`
  must equal `len(raw) - len(cleaned)` exactly — a drop with no matching
  reason count is a contract violation, not an acceptable rounding gap.

**Scenario: Preventing the rejection-report artifact from silently disappearing**
- **Given** a Module B pipeline run that invokes `clean_directory` and/or
  `apply_retail_spread`,
- **When** the run completes,
- **Then** the recurrence-invariant verification script (below) fails if
  `reports/module_b/data_rejection_report.csv` and/or
  `reports/module_b/fx_fallback_report.csv` are absent for that run, or if a
  pipeline change silently removes the code path that writes them.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** N/A for the FX fallback (currency conversion is
  channel/department-agnostic). For cleaning drops: the rejection report must
  break counts down by `department`/`channel` where available (not just
  aggregate reason counts), so a systematic drop pattern concentrated in one
  department (e.g. non-canonical department labels specific to Chaco-region
  field offices) is visible rather than averaged away.
- **Performance & decay:** computing rejection counts is an O(rows) pass
  already implicit in the existing `valid_mask` boolean series; the added
  reporting must not meaningfully change `clean_directory`'s runtime (target:
  <5% overhead versus the current implementation, since it reuses the
  already-computed mask rather than re-scanning).
- **Data integrity:** the rejection-report schema requires `source_file`,
  `row_id` (or `reason` + `count` if aggregated), `reason`, and — for
  cleaning drops — `department`/`channel` when resolvable; the FX
  fallback-report schema requires `iso_week`, `tc_ref`, and
  `fallback_pct_applied`. Both are new artifacts and must be added to
  `governance/FIGURE_MANIFEST.yaml` or an equivalent artifact registry if one
  exists for non-figure outputs, so their presence is checkable the same way
  figure provenance is checked in `IMP-V03`.
- **Reproducibility:** given the same raw CSV inputs and the same
  `config/fx_retail_spread_prior.yaml`, both reports must be byte-identical
  across runs — no timestamp or non-deterministic ordering in the emitted
  CSVs (sort by `source_file`/`reason` or `iso_week`).

## 5. Queue Stub (ready to file)

```yaml
id: F-XXX            # assigned at filing time
title: "Silent FX-spread fallback and unlogged data-cleaning drops mask input-quality gaps in Module B"
category: silent_fallback
kind: recurrence_invariant
status: open
opened_at: 2026-07-08
closed_at: null
recurrence_count: 0
evidence: |
  fx/spread_model.py:22 defines DEFAULT_SPREAD_PYG_PER_USD = 50.0; the
  fallback branch at fx/spread_model.py:98-99 (inside _spread_for_row,
  called from apply_retail_spread:101-103) silently substitutes this
  constant whenever a week's key is absent from
  config/fx_retail_spread_prior.yaml's series_b_weekly block — no warning,
  no record of which weeks fell back, no basis documented for the 50.0
  PYG/USD figure.

  data/cleaner.py's three cleaning gates — clean_budget_lines (valid_mask at
  :198-205, row filter :206-218), clean_volunteer_logs (valid_mask :261-270,
  filter :271-283), clean_media_buy_sheet (valid_mask :328-337, filter
  :338-351) — silently drop rows failing currency/amount/channel/department/
  positivity checks. clean_directory (:358-383) returns only the surviving
  frames; no count, no reason, no rejection report exists anywhere in the
  cleaning path, for financial inputs anchoring a ~$6,000,000
  (CAMPAIGN_BUDGET_USD, constants.py:142) allocation objective.
verification_script: scripts/check_silent_fallback_disclosure.py
notes: |
  Proposed script behavior: (1) run apply_retail_spread against a fixture FX
  config with one week deliberately missing from series_b_weekly and assert
  a corresponding row appears in the emitted fx_fallback_report.csv fixture
  output; (2) run clean_budget_lines / clean_volunteer_logs /
  clean_media_buy_sheet against fixture raw CSVs with a known number of
  deliberately-dirty rows per reason (bad currency, unparsable amount,
  non-canonical label, non-positive amount) and assert
  data_rejection_report.csv's reason counts sum to exactly
  len(raw) - len(cleaned) for each cleaner; (3) statically grep
  fx/spread_model.py and data/cleaner.py to confirm the reporting call sites
  are still present (regresses if a future refactor drops the disclosure
  call without removing the fallback/drop behavior itself).
  Spec: governance/improvement_plan/IMP-B04_silent-substitution.md
```
