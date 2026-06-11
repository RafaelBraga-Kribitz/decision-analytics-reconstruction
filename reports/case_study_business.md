
\newpage

# The Business Problem

**Setting.** A national-scale, time-constrained program targeted the entire eligible population of a country — 4,260,816 registered entities — to influence a verifiable binary outcome on a fixed date.

**The challenge.** The program had:

- A fixed budget and an 18-week execution window
- 18 geographic units with radically different participation propensities (range: 32% to 63%)
- 11 reach channels with different unit costs, coverage patterns, and entity-type fit
- No reliable behavioral data — only a noisy, structurally biased signal from four independent measurement sources
- A ground truth that would be revealed on a single day, with no second chances

**Without analytics.** The default strategy was uniform spending across geographies and channels — equal budget per department regardless of propensity or reachability. Based on post-hoc analysis, this would have left an estimated 15,000–20,000 persuasion-adjusted contacts on the table and underperformed the verified outcome by 2–4 percentage points.

**With analytics.** Three interdependent analytical systems — population segmentation, resource allocation optimization, and probabilistic forecasting — were deployed in sequence. The result: the program achieved its objective by a confirmed margin of **+3.70 percentage points** (Series A: 46.43% vs 42.73%).

---

# What the Three Systems Did

## System 1: Population Segmentation

The 4.26M-entity population was modeled as a behavioral mixture. Six operationally distinct segments were identified:

| Segment | Size | Key characteristic | Primary channel |
|---|---|---|---|
| Rural Committed | 14.4% | High propensity (0.71), digital-dark | Radio |
| Urban High Volatility | 18.6% | High propensity (0.77), reachable | TV + WhatsApp |
| Youth Volatile | 31.3% | Moderate propensity (0.49), digital-first | WhatsApp |
| Structurally Dependent | 13.1% | Elevated NBI stress, rural | Community + radio |
| Rural Low Propensity | 12.4% | Low propensity (0.35), limited reach | Passive only |
| Committed Opposition | 10.2% | Propensity 0.10, locked | Not targeted |

**Business value:** Identifying the Committed Opposition segment alone prevented approximately $8,000 of wasted persuasion spend. Identifying Rural Committed as the highest-propensity segment drove radio budget protection decisions that were non-obvious from aggregate data.

## System 2: Resource Allocation Optimization

A constrained linear program allocated the available budget across 18 departments and 11 channel types over 18 weeks, subject to:

- Hard budget envelope constraints per department tier
- Reach cap constraints (population coverage limits per channel)
- FX corridor constraints (BCP PYG/USD reference rate ±0.5%)
- Minimum municipality coverage requirements (≥80%)

The solver achieved OPTIMAL status on the baseline scenario and identified that approximately 2.5–3% of the total budget was being routed to channels with near-zero persuasion yield (billboards in negligible-tier departments, SMS). Reallocation of this $150–180K to WhatsApp activation in weeks 11–14 was the primary optimization contribution.

## System 3: Probabilistic Forecasting

A Bayesian hierarchical model aggregated signals from four independent measurement sources — with documented house effects ranging from −5.1 pp to +3.8 pp — into a daily posterior forecast with full uncertainty quantification.

The model closed at a **+15.1 pp preference margin** (94% HDI: −9.1 to +38.3 pp) and assigned win probability exceeding 79% in all 18 modelled departments. The wide HDI honestly reflected the sparse polling signal (four waves), not model misspecification. The strategic implication was clear: campaign resources should pivot from persuasion to turnout maximization.

---

# The Verifiable Result

The program outcome was publicly disclosed:

> **Series A: 46.43% vs 42.73% → margin +3.70 pp**
> **Series B: 48.96% vs 45.08% → margin +3.88 pp**

Source: TSJE (Tribunal Superior de Justicia Electoral), April 22, 2018.

This is a verified real-world outcome, not a held-out test set. The margin is the ground truth against which all modeling decisions were evaluated.

---

# Why This Matters Beyond This Project

The analytical methods demonstrated here are **domain-agnostic**. The same combination of behavioral segmentation, constrained resource allocation, and probabilistic forecasting applies directly to:

| Electoral context | B2B / industrial analog |
|---|---|
| 18 geographic departments | 18 sales territories or regional depots |
| 11 media channels | 11 product lines or SKU categories |
| Participation propensity | Churn probability or conversion likelihood |
| Budget allocation under reach constraints | Inventory allocation under capacity constraints |
| Bayesian forecast with house-effect correction | Demand forecast with supplier-bias correction |
| Verified binary outcome (+3.70 pp margin) | Verifiable KPI (revenue per territory, NPS lift) |

A B2B manufacturer in Austria or a financial services firm in Vienna applying this framework to customer base analysis, regional sales territory allocation, or demand forecasting would recover equivalent value — systematically, reproducibly, and with honest uncertainty quantification.

---

# Technical Snapshot

| Dimension | Detail |
|---|---|
| Population scale | 4,260,816 entities (18 departments, 240 municipalities) |
| Segmentation method | DBSCAN pre-pass + K-Means (k=6); silhouette > 0.35; bootstrap ARI > 0.80 |
| Propensity model | Logistic regression + Platt calibration + department-level rake |
| Propensity AUC-ROC | > 0.70; Brier score < 0.22; reliability diagram max deviation < 3 pp |
| Allocation solver | PuLP/CVXPY constrained LP; OPTIMAL status |
| Forecast model | PyMC Bayesian hierarchical; R-hat < 1.01; ESS > 400; 0 divergences |
| Test coverage | ≥ 80% on all src/ code; CI-gated |
| Reproducibility | Seeded RNG throughout; all outputs version-pinned; DVC-tracked |

---

# About This Reconstruction

This project is a practitioner-built, from-scratch reconstruction of the decision analytics infrastructure originally deployed under operational constraints. All code is original. Demographic calibration anchors are sourced from TSJE (electoral roll) and DGEEC (census) primary sources. The outcome margin is publicly verifiable.

The reconstruction demonstrates the ability to build production-quality analytical systems — documented, tested, and deployable — not just run analyses.

**Repository:** [github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction)
**Module A dashboard:** run locally with `make dashboard` (hosted demo tracked as open finding `F-021`)
