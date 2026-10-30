# Economic evaluation: Decision Analytics Reconstruction — Paraguay 2018 Presidential Election

Pre-build scenario exercise · evaluation date 2026-05-06 · method v2.0 · cost basis v1.1 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision and value mechanism

A national campaign team decides whether to plan its budget split, and its mid-campaign re-plan, with a three-part pipeline (voter segments, budget optimisation, Bayesian poll tracking) instead of a spreadsheet. The value is the information this adds to the split.

## Scale, baseline and horizon

- Perspective: the campaign team the scope names; the campaign manager decides. The 2018 decision is closed, so the case is the team's next comparable campaign. Hiring value is not counted.
- Budget B ≈ $2.0M over 14 weeks, 18 departments and 11 channel types [sourced: `project_scope/scope_module_B_resource_allocation_engine.md`, commit 7b233e9; the scope marks the budget ESTIMATED]. $1 ≈ €1 [assumption].
- Baseline and best realistic alternative: department spreadsheets and judgement in meetings [sourced: same file].
- Cost of not knowing: a judgement split leaves 4 % of B, €80k of budget-equivalent reach, below the best split [assumption: the scope's own claim that naive splits misdirect money; no benchmark]. This is the perfect-information upper bound per campaign.
- Recovery when the tool is used and right: 30 % of that bound, €24k [assumption, sensitivity parameter].
- Horizon: one campaign within one year; no discounting.
- No effort or value forecast was committed before the build.

## Scenarios

Outcomes include adoption: whether the manager actually uses the re-plan.

| Scenario | Operational outcome | Value per campaign | Probability |
|---|---|---|---|
| Used, re-plan helps | 30 % of the €80k gap recovered | +€24k | 0.30 [assumption: allocation models are standard; reach and unit costs are hand-set] |
| Used, confirms the plan | Split unchanged | €0 | 0.20 [assumption: judgement splits are often close] |
| Not used | Late for the first plan, or synthetic voters not trusted | €0 | 0.40 [assumption: large build, real data still needed] |
| Used, misleads | Few public polls and assumed unit costs move money the wrong way | −€16k (20 % of the gap) | 0.10 [assumption: thin poll data] |

## Expected value and cost

Expected gross value = 0.30 × €24k − 0.10 × €16k = **€5.6k** [estimate].

Rate: the market cost of the role this work needs (data science · senior, advertised minimum, ADJMI snapshot 2026-10-18), €51 loaded and €54 per active hour all-in. Total cost = build hours + maintenance (10 % of build hours for one year) + 24 h to load the team's real data [estimate, fixed in every row]. Hosting €0.

| Case | Build hours | Total cost | Multiple |
|---|---|---|---|
| Central | 144 | €9,850 | 0.57× |
| 0.5× hours | 72 | €5,573 | 1.0× |
| 1.5× hours | 216 | €14,126 | 0.40× |

## Hurdle result

- Central multiple 0.57×: **fails financial hurdle** (threshold 4×). Every row fails.
- Rate check: at a rate 30 % higher (€69 all-in; the inputs are floors) the central multiple is 0.44×.
- Maximum affordable cost: €5.6k / 4 = **€1,400**, about 26 hours in all, fewer than the data loading alone needs. A smaller version cannot fit that budget either.
- Break-even driver, the value of the helpful scenario: €38k (1.9 % of B) for 1×; €140k (6.8 % of B) for 4×. The 4× level is above the whole assumed €80k gap.
- Reversal: at the same shares, a budget of about $14M (seven times the scope estimate) reaches 4×; about $3.5M reaches 1×.

## Recommendation and measures

**Reject** as a company decision tool. If built for other reasons, it keeps this verdict. Measure: active hours; whether a campaign manager uses the re-plan in a real decision; the difference in contacts against the spreadsheet plan in held-out departments; maintenance hours.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
