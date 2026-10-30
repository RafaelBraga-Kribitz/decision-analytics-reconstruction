# Lessons learned: Decision Analytics Reconstruction — Paraguay 2018 Presidential Election

Evaluation: [economic-evaluation.md](economic-evaluation.md).

## Expectations against actuals (as of 2026-10-30)

| Item | Expected (evaluation) | Actual | Evidence |
|---|---|---|---|
| Effort | 320 h central (160 to 480 h), owner scope estimate | Unmeasured; no time log. Commits fall on 38 days from 2026-05-07 to 2026-10-29 (144 h by commit days × 4 h) | `git log origin/main`; cost basis v1.2 |
| Total cost | €17,280 central | Unmeasured; no campaign loaded real data | same |
| Technical performance | Re-plans that improve the split without chasing poll noise | Week-8 replay moves $766k and adds 1.20 % persuasion-weighted contacts on synthetic voters (ILLUSTRATIVE); 3 of 6 held-out polls inside the 95 % band | `reports/CASE_STUDY.md`, `README.md` |
| Adoption | Inside the scenario probabilities | No campaign use recorded | `README.md` (illustrative replay) |
| Operational outcome | 1.3 % of the actionable budget, as delivery gained or waste avoided | Unmeasured | none |
| Attributable value | €26k at $2M, €78k at $6M; budget unsourced | Unmeasured; technical validation is not realised return | none |

## Lessons

**L-DAR-1. A reconstruction of a closed decision has nobody who can act on it.** Scope: projects that rebuild a past decision. Name the next real decision the work would serve, and its owner, before the first commit; otherwise the company value is the adoption scenario alone. Evidence: the 2018 framing in `project_scope/scope_master_reconstruction_project.md` (commit 7b233e9) against the replay label in `README.md`. Date: 2026-10-30.

**L-DAR-2. The scale input moved during the build.** Scope: any evaluation whose value scales with a budget. The scope estimated a $2M budget (commit 7b233e9); the build uses a $6M envelope (`module_b_resource_allocation/config/budget_envelope.yaml`). Freeze scale inputs with the evaluation, and re-run it when they change. Date: 2026-10-30.
