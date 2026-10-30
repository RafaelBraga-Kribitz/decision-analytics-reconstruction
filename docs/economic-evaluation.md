# Economic evaluation: Decision Analytics Reconstruction — Paraguay 2018 Presidential Election

Pre-build scenario exercise · evaluation date 2026-05-06 · method v2.0 · cost basis v1.2 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

A national campaign team decides whether to plan its budget split, and its weekly re-plans, with a live system (voter segments, constrained budget allocation, Bayesian poll tracking) instead of department spreadsheets. Can it make a fixed budget more effective, and stop costly moves on misleading poll signals?

## Scale, baseline and horizon

- 18 departments, 11 channel types, 14 campaign weeks [sourced: `project_scope/scope_module_B_resource_allocation_engine.md`, commit 7b233e9].
- Budget: 4 to 5.5 million for the campaign, midpoint 4.75 million [assumption: owner's first-hand judgement of the 2018 campaign, recorded 2026-10-30; currency not recorded, taken as euros]. The repository's own figures, about $2M in the scope (ESTIMATED, 7b233e9) and a $6M reconstruction envelope (PRIOR), are unsourced and not used.
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

| Case | Hours | Total cost | Multiple at €4.75M (range €4.0–5.5M) |
|---|---|---|---|
| Central | 320 | €17,280 | 3.6× (3.0–4.1×) |
| 0.5× hours | 160 | €8,640 | 7.1× (6.0–8.3×) |
| 1.5× hours | 480 | €25,920 | 2.4× (2.0–2.8×) |

Expected gross value = 1.3 % × actionable budget: **€62k at the midpoint** (€52k to €72k), if the whole budget can still move.

## Verdict

**Fails financial hurdle**: 3.6× central against 4×; 2.8× at a rate 30 % higher (the inputs are floors). Only the top of the range passes (4.1×), and only if the whole budget can still move.

- Maximum affordable cost: €62k ÷ 4 = **€15.4k**, about 285 h at €54.
- Break-even driver, the actionable budget: €1.3M for 1×, €5.3M for 4×.

Reversing assumptions:

1. Budget in dollars: at 2018 rates ($1.18 per euro) the range is about €3.4–4.7M and the multiple 2.6–3.5×. Spend already committed before the first plan lowers it further.
2. At the midpoint, a build of about 285 h or less, or an expected improvement of about 1.46 % or more, passes.

## Recommendation

**Smaller version**: cap the build at about 285 h, for example by keeping poll tracking to the weekly re-plan the budget split needs, and deliver before the first plan. Measure: hours; decisions changed; verified waste avoided and delivery gained against the spreadsheet plan in held-out departments. Winning the election does not establish the system's contribution.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
