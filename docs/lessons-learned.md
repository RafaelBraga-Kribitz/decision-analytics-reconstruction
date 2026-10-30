# Lessons learned: Decision Analytics Reconstruction — Paraguay 2018 Presidential Election

Evaluation: [economic-evaluation.md](economic-evaluation.md).

## Expectations against actuals (as of 2026-10-30)

| Item | Expected (evaluation) | Actual | Evidence |
|---|---|---|---|
| Effort | 144 h central (72 to 216 h) | Unmeasured; no time log. Commits fall on 38 days from 2026-05-07 to 2026-10-29 | `git log origin/main` |
| Total cost | €9,850 central, including 24 h of data loading | Unmeasured; no campaign loaded real data | `git log origin/main` |
| Technical performance | Re-plan recovers 30 % of a 4 % allocation gap | Week-8 replay moves $766k and adds 1.20 % persuasion-weighted contacts on synthetic voters (ILLUSTRATIVE); 3 of 6 held-out polls inside the 95 % band | `reports/CASE_STUDY.md`, `README.md` |
| Adoption | Used in 60 % of scenarios | No campaign use recorded | `README.md` (illustrative replay) |
| Operational outcome | Better split for one campaign | Unmeasured | none |
| Attributable value | €5.6k expected | Unmeasured; technical validation is not realised return | none |

## Lessons

**L-DAR-1. A reconstruction of a closed decision has nobody who can act on it.** Scope: projects that rebuild a past decision. Name the next real decision the work would serve, and its owner, before the first commit; otherwise the company value is the adoption scenario alone. Evidence: the 2018 framing in `project_scope/scope_master_reconstruction_project.md` (commit 7b233e9) against the replay label in `README.md`. Date: 2026-10-30.

**L-DAR-2. The scale input moved during the build.** Scope: any evaluation whose value scales with a budget. The scope estimated a $2M budget (commit 7b233e9); the build uses a $6M envelope (`module_b_resource_allocation/config/budget_envelope.yaml`). Freeze scale inputs with the evaluation, and re-run it when they change. Date: 2026-10-30.
