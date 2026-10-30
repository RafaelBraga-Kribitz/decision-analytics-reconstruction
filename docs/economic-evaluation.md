# Economic evaluation: Decision Analytics Reconstruction — Paraguay 2018 Presidential Election

Pre-build scenario exercise · evaluation date 2026-05-06 · method v2.0 · cost basis v1.2 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

A national campaign team decides whether to plan its budget split, and its weekly re-plans, with a live system (voter segments, constrained budget allocation, Bayesian poll tracking) instead of department spreadsheets. Can it make a fixed budget more effective, and stop costly moves on misleading poll signals?

## Scale, baseline and horizon

- 18 departments, 11 channel types, 14 campaign weeks [sourced: `project_scope/scope_module_B_resource_allocation_engine.md`, commit 7b233e9].
- Budget: no sourced figure. The scope estimates about $2M and marks it ESTIMATED (7b233e9); the build later uses a $6M "reconstruction envelope" of PRIOR provenance (`module_b_resource_allocation/config/budget_envelope.yaml`). $1 ≈ €1 [assumption].
- What matters is the **actionable budget**: what can still move before each decision.
- Baseline: department spreadsheets, agency recommendations and meetings [sourced: scope, same commit].
- Horizon: one campaign; benefit is useful delivery gained or waste avoided, valued at its purchase cost, net of operational implementation.

## Scenarios

Outcomes of using the system, including adoption and late delivery.

| Outcome | Change against existing planning | Probability |
|---|---|---|
| Reveals substantial avoidable waste | +4 % of the actionable budget | 0.20 [assumption: owner's structured judgement] |
| Modest, actionable improvements | +2 % | 0.40 [assumption] |
| Adds information but changes no useful decision | 0 % | 0.25 [assumption] |
| Adverse: poll noise read as real change triggers costly moves | −2 % | 0.15 [assumption: few public polls] |

Expected improvement = 0.20 × 4 % + 0.40 × 2 % − 0.15 × 2 % = **1.3 % of the actionable budget**.

## Expected value and cost

Rate: €54 per active hour, the market cost of the role this work needs (data science · senior, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence), €51 loaded plus €3 AI and equipment. Hours: owner scope estimate, 320 h, including integration and campaign-period support [estimate]; no maintenance beyond the campaign. Hosting €0.

| Case | Hours | Total cost | Multiple at $2M | Multiple at $6M |
|---|---|---|---|---|
| Central | 320 | €17,280 | 1.5× | 4.5× |
| 0.5× hours | 160 | €8,640 | 3.0× | 9.0× |
| 1.5× hours | 480 | €25,920 | 1.0× | 3.0× |

Expected gross value = 1.3 % × actionable budget: **€26k at $2M, €78k at $6M**.

## Verdict

**Insufficient evidence.** The result turns on a budget figure that the repository estimates in two incompatible ways and never sources. At the central cost:

- Break-even driver, the actionable budget: **€1.3M for 1×, €5.3M for 4×** (€6.8M at a rate 30 % higher; the inputs are floors).
- Maximum affordable cost: 1.3 % × actionable budget ÷ 4: €6.5k at $2M, €19.5k at $6M.

Reversing assumptions:

1. The actionable budget. Spend already committed before the first plan does not count, so the headline budget overstates it.
2. At $6M, an expected improvement below about 1.15 % fails 4×, and below 0.29 % fails 1×; for example if poll noise drives more moves than the scenarios allow.

## Recommendation

**Defer** until the campaign's actionable budget is sourced. Build if it is at least about €5.3M and the system can deliver before the first plan; reject below about €1.3M. Measure: hours; decisions changed; verified waste avoided and delivery gained against the spreadsheet plan in held-out departments. Winning the election does not establish the system's contribution.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
