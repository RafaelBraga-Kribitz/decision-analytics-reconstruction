# Session End — 2026-10-11 (improvement-plan closure F-083..F-090, status flip)

## Context

Session start found the governance queue empty (62 findings, 0 open) but the
README status at "Functional": the 2026-07-08 statistical improvement plan still
had eight specs unshipped or partial, and the register in
`governance/improvement_plan/INDEX.md` lagged the code. Each remaining spec was
filed as a finding, given its `verification_script`, fixed and closed in its
own PR (#199–#206). PR #198 refreshed state and marked the 16 already-shipped
specs done.

## Findings touched (all new, all closed)

- **F-083 (IMP-C01, #199):** the full-NUTS MCMC gates were hard asserts but
  marked `slow`, and CI ran only `-m "not slow"`. New CI job
  `module-c-slow-nuts`; gate `scripts/check_mcmc_convergence_gates_hard.py`.
- **F-084 (IMP-C03, #200):** `post_mortem.qmd` hard-coded v0.3 diagnostics and
  labelled 94% intervals "95% HDI". The fit now exports
  `mcmc_diagnostics_summary.json` and the report renders from it; gate
  `scripts/check_report_computed_integrity.py`.
- **F-085 (IMP-C06, #201):** small-sample honesty — `low_n` flag below 5 waves,
  Clopper–Pearson intervals on walk-forward coverage, "proof" wording removed
  (`C_research_evidence_table.md`); gate `scripts/check_small_sample_honesty.py`.
- **F-086 (IMP-B04, #202):** Module B dropped 100% of volunteer-log rows
  silently (numeric-dtype read of string IDs). Rejection and FX-fallback reports
  under `reports/module_b/`; gate `scripts/check_module_b_silent_substitution.py`.
- **F-087 (IMP-A04, #203):** department-aware rural imputation, `dob_imputed`
  flag replacing the `01/01/1980` sentinel, injector manifest reduced to the 12
  implemented flaw types; gate `scripts/check_cleaner_injector_integrity.py`.
- **F-088 (IMP-A06, #204):** `model_params.yaml` values now reach the runtime
  (`utils/model_params.py`), dead README links fixed; gate
  `scripts/check_module_a_config_doc_parity.py`.
- **F-089 (IMP-A03, #205):** the 50k clustering gates are enforced against the
  production manifest; gate `scripts/check_clustering_gate_consistency.py`.
- **F-090 (IMP-V03, #206):** orphan SHAP generator (random-data fit writing the
  published path) deleted; gate `scripts/check_shap_artifact_provenance.py`.

## Cross-repo

- **IMP-F01..F04** (Chart_Audit_Framework PR #13): rule engine, CLI and
  coverage-matrix gate shipped. F04's zero-duplicate invariant is not met —
  187 byte-identical groups remain inside the scraped site mirrors; the
  maintainer decides between rewriting mirror links, amending the spec, or
  dropping the mirrors.

## Noted, not changed

- `battleground_sigma_idio.yaml` has its hash rewritten whenever the pipeline
  runs (pre-existing).
- `test_segmentation.py` comments a 15k silhouette of ≈0.197; a single-threaded
  run measured 0.2689.
- The Module A SHAP chart's x-axis label is clipped.
- 79 `open_unfiled` rows in `ISSUE_TRIAGE_MASTER.yaml` predate the improvement
  plan and were out of this session's scope; many name a spec that is now done
  and can likely be re-graded `superseded`.

## Next session

Run `make session-start`. With the queue empty, follow the Phase 6 feature
workflow in `CLAUDE.md` (`scripts/generate_agent_queue.py`).
