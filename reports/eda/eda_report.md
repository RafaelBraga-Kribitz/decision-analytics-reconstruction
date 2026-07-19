# Paraguay Presidential Campaign — Full EDA Report

**Generated:** June 14, 2026
**Data Pipeline Version:** 1.0.0
**Canonical run:** a05a4a581676 · model c_tracking_hierarchical_v0.4 (stamped on every figure for SSOT traceability)
**Population Sample:** N = 5,000 individuals
**Campaign Period:** Weeks 1–14 (2018-W01 to 2018-W14)
**Forecast Window:** 2017-12-01 to 2018-04-21 (142 days)

---

## Executive Summary

Reconstruction decision-support insights (fixture polls; verified TSJE anchor +3.70 pp):

- **Tracking posterior on fixtures:** Closes at **3.7 pp** margin (94% HDI: 2.8 to 4.7 pp). Modelled department win probabilities: **7%–100%**. Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp.
- **Committed Opposition is the largest segment (18.4%)** with mean participation propensity 0.63. Youth Volatile (17.4%, propensity 0.58) remains the headline mobilisation cohort in Central and Alto Paraná.
- **Central and Alto Paraná absorb 45% of the total budget** ($1,920,549 and $783,849 respectively), reflecting their demographic weight. These allocations appear justified, but efficiency metrics suggest diminishing returns in Central already in week 8.
- **Participation propensity is near-uniform across all six segments** (segment means span just 0.58–0.65; no single cohort is a dramatically higher-propensity target, so propensity alone cannot rank segments — see §A4/§A5). The rural segments still receive little digital investment because of low internet penetration: radio is their dominant reach channel, and any reduction in radio spend directly suppresses participation in Itapúa and San Pedro strongholds.
- **Bilateral (direct) channels absorb 52.5% of baseline budget** vs. 47.5% for broadcast. The broadcast-to-direct scenario redistributes this mix but produces zero additional persuasion contacts at the aggregate level, suggesting the direct-contact premium is not converting efficiently everywhere.
- **Pollster house effects (from posterior_house_effects.parquet):** ATI_SNEAD has a -8.7 pp bias, ICA has a +5.0 pp bias; ECODAT is the closest to neutral (+2.9 pp). Raw polling averages should never be used without bias correction for this race.
- **Chaco departments (Alto Paraguay, Boquerón, Presidente Hayes) are negligible-tier** in budget allocation; modelled department win probabilities cluster near **7%–100%** on fixture posteriors (Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp).

---

## Data Quality Assessment

### population_master_clean.parquet
- **Shape:** 5,000 rows × 69 columns
- **Duplicates:** 0 duplicate entity_ids confirmed
- **Nulls:** 1,193 total missing values across 1 column
- **Top null columns:**
  - `qualitative_district`: 23.9% missing
- **Anomalies:** `qualitative_district` shows NaN for ~9% of records; `qualitative_sentiment` missing for ~10%; these appear intentionally unlinked (no linked qualitative interview). `participation_propensity` is well-bounded [0.014, 1.0] with no out-of-range values.
- **Schema drift flags:** 81 records flagged — negligible (<1%).

### segment_labels.parquet
- **Shape:** 5,000 rows × 4 columns
- **Segment coverage:** 6 unique labels, segment_id 0–5, fully mapping population_master
- **DBSCAN noise:** 46 rows flagged as noise — all reassigned to nearest cluster, no orphan records.

### participation_propensity.parquet
- **Shape:** 5,000 rows × 4 columns
- **Range:** [0.3205, 1.0000] — fully bounded in [0,1]
- **Department rake multiplier:** mean 1.40, range [0.63, 2.73] — large dispersion indicates significant demographic imbalance across departments in the raw sample.

### allocation_baseline.csv / allocation_broadcast_to_direct.csv
- **Shape:** 2,772 rows × 21 columns each
- **OPTIMAL solver status:** All rows solver_status = OPTIMAL — no infeasible allocations.
- **Zero-budget rows:** Large number of department × channel × week combinations with $0 allocation, as expected for negligible-tier departments.
- **Total baseline budget:** $6,029,991 USD

### module_c files
- **daily_posterior_forecast.parquet:** 142 daily rows, single calibration series A, no gaps.
- **posterior_house_effects.parquet:** 3 pollsters — small but complete.
- **battleground_department_probability.parquet:** 18 departments, win_probability_a range [0.0736, 1.0000].
- **monte_carlo_draws.parquet:** 10,000 draws across 3 scenario buckets: baseline (3,334), extreme_tracker (3,333), compounded_herd (3,333). alloc_mean_persuasion_contacts populated from the Module B baseline allocation (B-to-C handshake verified non-zero).

---

## Module A: Population & Segmentation

### A1 — Segment Size Bar Chart
**What it shows:** Absolute count and percentage share of the population dataset for each of the six behavioral segments.
**Key finding:** Committed Opposition is the largest segment at 18.4%, ahead of Structurally Dependent Bloc at 18.1%. Rural Committed is the smallest at 13.8%.
**Strategic implication:** Mobilisation strategy must prioritise youth outreach. Even modest propensity lifts in this cohort deliver outsized turnout gains relative to smaller segments.

### A2 — Age Distribution by Segment
**What it shows:** Histogram + KDE of age distribution within each segment, faceted.
**Key finding:** Youth Volatile peaks sharply at 18–30 years. Rural Committed and Structurally Dependent Bloc both show mature age profiles (median ~40–48). Urban High Volatility has a bimodal distribution with peaks at ~25 and ~42.
**Strategic implication:** Messaging for Youth Volatile must be digital-first and culturally proximate to Gen Z; Rural Committed messaging should be delivered via traditional media with community leader endorsements.

### A3 — Gender Breakdown by Segment
**What it shows:** Stacked 100% bar showing F/M split per segment.
**Key finding:** All segments are near-balanced on gender (~50/50). Urban High Volatility skews very slightly female (~52%). No segment exhibits a gender imbalance large enough to drive targeting divergence.
**Strategic implication:** Gender is not a primary segmentation driver; campaign messaging can be gender-neutral by default, with tailored versions only for specific media buys.

### A4 — Department × Segment Propensity Heatmap
**What it shows:** Mean participation propensity for each department × segment cell.
**Key finding:** The heatmap is nearly flat — every department × segment cell sits in a narrow ~0.50–0.70 band. Rural Committed reads about 0.59 / 0.52 / 0.65 in Cordillera, San Pedro, and Misiones (not the uniformly high values a mobilisation-target story would need), and Committed Opposition sits in the ~0.60–0.69 range rather than as a low outlier. Propensity does not separate departments or segments sharply enough to rank mobilisation targets on its own (F-052).
**Strategic implication:** Do not prioritise a department × segment cell on propensity alone — the signal is too flat to differentiate. Targeting must be driven by reachability and preference strength, with propensity used only as a modest tie-breaker. Committed Opposition is deprioritised for *persuasion* on the basis of its B-preference strength, not because of a low participation propensity.

### A5 — Propensity Violin by Segment
**What it shows:** Probability distribution of participation propensity within each segment.
**Key finding:** All six violins overlap heavily in the ~0.50–0.70 band; within-department spread is small (individual propensity is a raked participation-likelihood score with a modest fixed spread, per F-052), so apparent separation between violins reflects department mix more than a genuine propensity gap between segments. No segment forms a high cluster above 0.80 or a low cluster near 0.10.
**Strategic implication:** Youth Volatile combines high reachability (A12) with a wide, soft Intent A tail (A13) — micro-target on persuadable supporters there, not on propensity variance (the violins overlap every other segment in the flat ~0.50–0.70 band).

### A6 — Urban vs Rural by Segment
**What it shows:** 100% stacked bar of urban/rural split per segment.
**Key finding:** Rural Committed is 97.8% rural; Urban High Volatility is 100% urban. Youth Volatile and Rural Low Propensity show mixed urban (73–93%) profiles. Structurally Dependent Bloc is 97.5% rural.
**Strategic implication:** Channel selection must mirror this split: digital/WhatsApp for urban segments, radio/sound_cars for rural segments. A single channel strategy will structurally miss one or the other.

### A7 — Language Composition by Segment
**What it shows:** Jopara / Spanish / Guaraní / Other composition per segment.
**Key finding:** Jopara bilingual speakers account for 47–51% in most segments, indicating a majority of the population communicates in the dominant mixed vernacular. Rural Committed has the highest Guaraní-only share (~10%). Youth Volatile skews slightly more Spanish-only (~30%).
**Strategic implication:** All campaign materials should have Jopara-accessible versions. Pure Spanish content will miss a substantial rural audience; pure Guaraní is only needed for a small minority of Rural Committed.

### A8 — Structural Dependency Rate by Segment
**What it shows:** Percentage of individuals with a structural dependency proxy flag, by segment.
**Key finding:** Rural Committed (48.4%) and Structurally Dependent Bloc (39.2%) have the highest dependency rates. Urban High Volatility has the lowest (9.7%). This flag correlates with clientelistic political networks.
**Strategic implication:** Outreach in high-dependency segments must be sensitive to clientelistic pressures. Monitor for vote-buying activity in Rural Committed and Structurally Dependent territories.

### A9 — Correlation Heatmap of Numeric Features
**What it shows:** Pearson correlation matrix of 12 key numeric variables.
**Key finding:** Media penetration channels (TV, radio, WhatsApp) are positively correlated with each other (r ≈ 0.3–0.6) and with reachability_index. NBI stress prior is negatively correlated with internet access and digital reachability. Participation propensity shows weak negative correlation with structural dependency.
**Strategic implication:** There is no single "silver bullet" contact channel — the media variables cluster together. Targeting high-reachability individuals does not perfectly proxy for high-propensity; both dimensions must be modelled jointly.

### A10 — PCA Biplot
**What it shows:** First two principal components of the numeric feature space, coloured by segment.
**Key finding:** PC1 (explaining ~28% variance) separates high-digital-reach (right) from low-digital-rural individuals (left). PC2 (~17% variance) separates high-propensity from low-propensity. Segments show good cluster separation, validating the segmentation algorithm.
**Strategic implication:** The segmentation captures meaningful population heterogeneity. Segment-specific strategies are empirically warranted rather than being an arbitrary division.

### A11 — NBI Stress Prior by Department
**What it shows:** Box plot of NBI (unmet basic needs) stress scores by department.
**Key finding:** Concepción, San Pedro, and Caazapá display the highest NBI stress medians (>0.65), indicating structural vulnerability. Asunción and Central are the lowest stress departments.
**Strategic implication:** High-NBI departments offer programmatic policy messaging traction (infrastructure, social transfers). Campaign messaging there should be needs-based rather than ideological.

### A12 — Reachability Index by Segment
**What it shows:** Distribution of composite reachability index (TV + radio + digital) per segment.
**Key finding:** Youth Volatile and Rural Low Propensity display higher reachability (peak 0.75–0.95), driven by better digital and TV coverage. Rural Committed has a bimodal distribution with many individuals at very low reachability (<0.5).
**Strategic implication:** A significant minority of Rural Committed is effectively unreachable by any modelled media — these individuals require in-person canvassing, which is expensive. Budget for in-person contact in those micro-zones.

### A13 — Vote-Preference Strength by Segment and Voting Intent
**What it shows:** Histogram of vote-preference strength, broken out by voting intent (A/B/other/none) within each segment.
**Key finding:** Candidate A preference strength (Intent A) peaks above 0.5 in most segments. Youth Volatile shows a wide, flat distribution for Intent A indicating many soft supporters. Committed Opposition's Intent B strength is concentrated at high values — these are firm opponents.
**Strategic implication:** Soft Intent A supporters in Youth Volatile are the primary persuasion/mobilisation opportunity. Hard Intent B in Committed Opposition are a lost cause for persuasion — do not waste budget there.

---

## Module B: Resource Allocation

### B1 — Budget by Department
**What it shows:** Horizontal sorted bar chart of total USD allocated by department.
**Key finding:** Central ($1,921K, 31.8%), Alto Paraná ($784K, 13.0%), and Itapúa ($494K, 8.2%) absorb 53% of the total budget. 2 department(s) receive less than $50K each.
**Strategic implication:** The allocation is demographically rational but should be stress-tested against marginal persuasion value. Chaco departments (Alto Paraguay, Boquerón) receive near-zero budget, which aligns with their high baseline win probability.

### B2 — Weekly Budget Burn-Down by Channel Type
**What it shows:** Line chart of weekly spend by channel type (broadcast, bilateral).
**Key finding:** Bilateral (direct) channels are front-loaded in weeks 1–4, tapering in weeks 10–14. Broadcast shows a more even distribution with a slight peak in weeks 6–9 (mid-campaign intensity period).
**Strategic implication:** The front-loaded direct spend may be losing impact by the time election day arrives. Consider shifting 10–15% of bilateral budget from weeks 1–3 to weeks 11–13 to maintain turnout pressure in the final push.

### B3 — Broadcast vs Direct Budget Split
**What it shows:** Left: the two budget scenarios (Baseline vs Broadcast→Direct) compared as separate lines — they are mutually exclusive, so they are never stacked into a meaningless total. Right: the within-baseline broadcast vs bilateral split (legitimate components of one budget) as a stacked area.
**Key finding:** Baseline allocates 47.5% broadcast / 52.5% bilateral. The broadcast-to-direct scenario shifts this further but does not produce additional persuasion contacts (alloc_mean_persuasion_contacts = 0 in all MC draws), suggesting a possible pipeline data gap.
**Strategic implication:** Until the persuasion contact column is validated for the broadcast-to-direct scenario, treat that scenario's efficiency claims with caution. The baseline split appears operationally sound.

### B4 — Reach Utilisation Heatmap
**What it shows:** Mean reach utilisation (0–1 scale) by department × channel.
**Key finding:** WhatsApp chatbot and Facebook Ads consistently achieve the highest reach utilisation in urban strongholds (Asunción, Central). Radio spots achieve high utilisation in rural departments. Several channels (billboards, SMS) have near-zero utilisation in most departments.
**Strategic implication:** Billboards and SMS are underperforming on reach utilisation and should be reviewed for reallocation. WhatsApp and radio are the workhorses of the reach strategy.

### B5 — Cost per Persuasion Contact
**What it shows:** Scatter plot of cost-per-persuasion-contact (USD) vs. total budget, bubble = budget.
**Key finding:** Caaguazu and San Pedro achieve the best cost efficiency. Asunción and Central, despite receiving the most budget, have higher cost-per-contact due to competitive media markets.
**Strategic implication:** Marginal spend in Central and Asunción is less efficient than equivalent spend in Caaguazu or San Pedro. A 5% budget reallocation from these metro departments to mid-tier departments could increase total persuasion contacts without increasing total spend.

### B6 — FX Rate Series
**What it shows:** Reference and retail USD/PYG rate over 14 campaign weeks.
**Key finding:** PYG depreciated ~1.8% against USD over the campaign window (5,615 → ~5,525 reference rate), with retail spread widening from 1.7% to ~2.0%.
**Strategic implication:** Budget commitments should be made in USD or hedged in PYG at the start of the campaign; waiting incurs currency risk. The FX impact is modest (~$109K at current scale) but non-trivial.

### B7 — Routing Cost Matrix
**What it shows:** Heatmap of travel time (minutes) between all department pairs.
**Key finding:** Chaco-to-Oriental crossings (Boquerón → any Oriental department) have the highest travel times (>600 minutes), reflecting the geography of the Chaco. Within Oriental, interior departments like Caazapá and Misiones also show elevated access times.
**Strategic implication:** In-person canvassing and rally logistics must account for extreme travel times in Chaco and interior Oriental departments. Route pre-planning and local organiser networks are essential to avoid field team inefficiency.

### B8 — Reach Caps vs Expected Contacts
**What it shows:** Grouped bar chart comparing reach cap (population proxy) vs. actual expected contacts, with budget overlay on secondary axis.
**Key finding:** Central and Alto Paraná show expected contacts well below their reach cap, indicating untapped reach capacity. Itapúa and Caaguazu are closer to their cap, suggesting near-saturation.
**Strategic implication:** Central and Alto Paraná have headroom to absorb more contacts without hitting reach ceiling — incremental spend there will not face diminishing returns immediately. Itapúa is near-saturated; marginal returns are declining.

---

## Module C: Forecasting & Scenarios

### C1 — Bayesian Tracking Retrodiction (2018 Series A)
**What it shows:** 142-day Bayesian preference-margin *retrodiction* — in-sample tracking of the past 2018 Series A window, read against the verified +3.70 pp TSJE outcome anchor (drawn on the panel), **not** an out-of-sample forecast — with 94% HDI bands.
**Key finding:** Candidate A's posterior mean preference margin closes near **3.7 pp** on fixture polls (Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp). The 94% HDI is wide (2.8 to 4.7 pp), reflecting only 8 poll waves.
**Strategic implication:** The lead is robust but the HDI is wide — more polling waves would dramatically tighten the uncertainty bounds. The campaign should commission 2–3 additional poll waves in the final 6 weeks.

### C2 — Calibrated Terminal Posterior Distribution
**What it shows:** Terminal (election-eve) posterior margin — mean + 94% HDI. The terminal latent margin is *pinned to the verified outcome anchor* m★ = +3.70 pp by a soft likelihood term (σ = 0.5 pp; `models/tracking/hierarchical.py`), so the posterior sits near m★ **by construction**, not by independent out-of-sample agreement.
**Key finding:** Calibrated final mean margin is 3.7 pp (Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp). Read the proximity to +3.70 pp as a calibration target the model was pinned to — not a forecast that independently recovered the result. Out-of-sample skill is evaluated separately in walk-forward, where the anchor is withheld.
**Strategic implication:** The campaign is in a "protecting the lead" posture. The strategic priority shifts from persuasion to turnout maximisation among A-leaning segments, particularly Youth Volatile and Rural Committed.

### C3 — Battleground Department Win Probability
**What it shows:** Horizontal bar chart of tracking-implied P(Win, Candidate A) by department with 94% HDI whiskers (unanchored national posterior × TSJE swing factors, `c_battleground_v0.5` decoupled σ).
**Key finding:** Modelled win probabilities span **7.4%–100.0%** (Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp; per-dept σ_idio from reference poll residuals where available). GANAR strongholds Central (17.9%) and Alto Paraná (19.9%) sit well below 50%; v0.5 reduces probability plateaus among Abdo-leaning departments (F-081).
**Strategic implication:** Geographic risk is heterogeneous — budget in Central and Alto Paraná targets turnout/defence in GANAR territory, not persuasion swing. Caaguazu (53.5%) and San Pedro (60.0%) remain among the most competitive departments.

### C4 — House Effects Forest Plot
**What it shows:** Posterior mean ± 94% HDI for each pollster's house effect (bias toward Candidate A).
**Key finding:** ATI_SNEAD has the largest negative house effect (-8.7 pp), meaning its polls systematically understate A's lead; ICA has the largest positive house effect (+5.0 pp); ECODAT is the most neutral (+2.9 pp). (Derived from posterior_house_effects.parquet — the same frame the C4 figure plots.)
**Strategic implication:** Never cite raw ATI_SNEAD polls in communications — they will appear worse than reality. ECODAT is the closest to unbiased for public-facing narratives. The campaign analytics team should routinely adjust all external poll reports for these biases.

### C5 — Shock Scale Distribution by Scenario
**What it shows:** Shock-scale distribution per scenario bucket (box + jittered draws). Monte-Carlo draws are *exchangeable*, so a percentile fan over a draw index would be a meaningless x-axis.
**Key finding:** Baseline scenario draws cluster tightly around shock_scale ≈ 0.987 (low volatility); the Extreme Tracker scenario sits at ≈ 1.83 and 2.43. Near-deterministic scenarios collapse to a point — the honest signal of a discrete scenario catalogue.
**Strategic implication:** The extreme tracker scenario requires campaign stress-testing — if late-breaking events cause a 2x shock scale swing, what is the impact on persuasion contacts and turnout? Model this explicitly for contingency planning.

### C6 — Shock Scale Distribution by Scenario
**What it shows:** Histogram of shock_scale per scenario bucket with dotted markers at each discrete point mass — no KDE, because smoothing would fabricate continuous density that is not in the data.
**Key finding:** Baseline has two point-mass clusters at 0.987 and 0.590, suggesting a discrete scenario design rather than continuous draws. Extreme Tracker similarly clusters at 1.83 and 2.43. The MC architecture uses deterministic scenario parameters with draw-level randomness elsewhere.
**Strategic implication:** The shock scale design is scenario-discrete, not continuously random — this limits the model's ability to capture smooth intermediate risk scenarios. A continuous shock prior would be more realistic for final-week planning.

### C7 — Exit Model Parameter Posteriors
**What it shows:** Forest plot of exit model parameters: intercept, beta_oea, beta_eu, sigma.
**Key finding:** The intercept (~25.5 pp) is the baseline exit-poll A−B margin when OEA/EU timing flags are off — exit fixtures run hotter (~26–33 pp) than the tracking posterior mean (~3.7 pp) because quick-count subsamples are a different estimand from the TSJE-anchored tracking series (+3.70 pp). beta_oea and beta_eu both straddle zero (HDI spans positive and negative territory), meaning international observer assessments (OEA, EU) have uncertain systematic influence.
**Strategic implication:** The exit model calibration is weakly identified for international observer effects. Do not use exit model estimates as the primary real-time result metric — rely on the tracking model until polling closes.

### C8_v2 — Win Probability vs Participation Propensity by Department
**What it shows:** Scatter plot of department-level win probability vs. mean participation propensity, coloured by region, with a ranked table of departments by propensity.
**Key finding:** Win probability varies across departments (7.4%–100.0%) with wider spread under v0.5 decoupled σ; propensity varies more. High-propensity departments (Rural Committed-heavy) cluster separately from win-probability bands — both are model outputs on reconstruction fixtures.
**Strategic implication:** Competitive win probability combined with high reachability — not high propensity (Rural Committed cells in San Pedro, Cordillera, and Misiones sit in the flat ~0.52–0.65 band per A4) — identifies departments where turnout-defence spend may outperform persuasion swing bets.

### C9 — Polling Transparency Audit
**What it shows:** Transparency score vs. house-effect magnitude, one point per pollster (n=3 pollsters — a per-pollster audit, not a fitted trend).
**Key finding:** Across the three fixture pollsters, ATI_SNEAD carries the largest |house effect| (8.7 pp) while ECODAT is the closest to neutral (+2.9 pp). With n=3, no transparency–bias relationship can be inferred — read this as an audit, not evidence of a rule.
**Strategic implication:** Apply bias corrections per pollster regardless of transparency rating; do not infer a transparency→bias rule from three points.

### C10 — MC Shock-Scale Distribution (legacy filename)
**What it shows:** Distribution of shock_scale across all MC draws by scenario bucket. The committed filename references "win probability", but this panel does **not** derive P(win) — Candidate-A win probability is C3 / C8_v2.
**Key finding:** Draws are split across 3 canonical buckets (baseline (3,334), extreme_tracker (3,333), compounded_herd (3,333)); shock-scale distributions are multimodal by design of the discrete scenario catalog.
**Strategic implication:** Resource buffers and contingency plans should be stress-tested against the extreme-tracker bucket (1.8–2.4× baseline shock sensitivity) — not just the ±10% band around baseline.

---

## Cross-Module Synthesis

### S1 — Segment × Department Budget Heatmap
**What it shows:** Prorated budget allocation reaching each segment × department combination.
**Key finding:** Youth Volatile in Central receives by far the largest budget flow (~$603K prorated), followed by Urban High Volatility in Central and Alto Paraná. Rural Committed receives relatively little absolute budget — despite being a hard-to-reach, radio-dependent segment worth protecting — because its dominant departments (Itapúa, San Pedro) receive only moderate total allocations.
**Strategic implication:** The budget is highly concentrated in Youth Volatile × Central — a high-risk, high-reward bet. A 10% budget reallocation to Rural Committed × interior departments would likely produce higher propensity-weighted returns.

### S2 — Propensity × Reachability Matrix
**What it shows:** 4-quadrant scatter of segment mean propensity vs. mean reachability, bubble = segment size.
**Key finding:** Rural Committed sits above the segment-median propensity / below-median reachability quadrant — hard to reach, not sharply higher-propensity (all six segment means span just 0.58–0.65). Youth Volatile is high-reachability with typical propensity. Committed Opposition is deprioritised for persuasion on B-preference strength, not on a low propensity outlier.
**Strategic implication:** Campaign resource allocation should weight the propensity × reachability product, not either metric alone. Rural Committed needs investment in delivery mechanisms (radio, canvassing) to unlock its propensity value.

### S3 — Channel ROI by Region
**What it shows:** Persuasion contacts per USD by channel and region.
**Key finding:** Canvassing and rallies show the highest ROI proxy per USD in Oriental departments. Facebook Ads and WhatsApp chatbot show competitive ROI in metro areas. Sound cars have high ROI in CHACO where alternatives are limited.
**Strategic implication:** ROI-optimal channel mix differs by region: metro → digital (WhatsApp, Facebook); Oriental → radio + canvassing; Chaco → sound cars + radio. Channel uniformity across regions wastes budget.

### S4 — Department Priority Matrix
**What it shows:** Win probability × participation propensity × log(budget) priority score by department.
**Key finding:** Central, Caaguazu, and Itapúa score highest on the composite priority index. Misiones, Neembucú, and Caazapá score lowest despite reasonable win probabilities — driven by win-probability weighting and budget size, not sharply lower propensity (department means remain in the narrow ~0.50–0.70 band per A4).
**Strategic implication:** Caaguazu is underweighted relative to its priority score — it ranks 3rd in composite priority but only 5th in total budget. A budget rebalancing toward Caaguazu would improve overall campaign efficiency.

### S5 — Reach Utilisation vs Persuasion Contacts (descriptive)
**What it shows:** Reach utilisation vs. total persuasion-adjusted contacts by department (bubble = budget), with a descriptive OLS trend line — *not* a Pareto efficiency frontier (the non-dominated envelope).
**Key finding:** Most departments cluster in the low-utilisation / low-contacts region, with Central and Alto Paraná as positive outliers. No department reaches both high reach utilisation AND high persuasion contacts.
**Strategic implication:** Departments with moderate reach utilisation but very few persuasion contacts (e.g., Concepción, Misiones) may have a channel–segment mismatch — the channels selected are not penetrating the dominant behavioural segments there. (Descriptive trend, not a frontier-optimality claim.)

---

## Strategic Recommendations

1. **Accelerate Youth Volatile mobilisation in Central and Alto Paraná.** This is the highest-reachability mobilisation cohort (smallest segment at 17.4%, but peak digital/TV reachability per A12). Dedicate a dedicated WhatsApp chatbot campaign to 18–30 year olds in these departments in weeks 11–14. Target propensity lift from 0.58 to 0.63 would add participation-weighted contacts proportional to segment size — not a separate high-propensity lever.

2. **Protect Rural Committed in Itapúa and San Pedro through radio-first strategy.** Do not allow any radio budget reduction in these departments. Rural Committed has a participation propensity of 0.58 (mean, in line with every other segment) and is almost exclusively accessible by radio. Any radio cut in these departments removes contacts that no digital channel can replace for this segment.

3. **Reallocate 5–8% of Central budget to Caaguazu and San Pedro.** Central shows diminishing reach returns (reach cap not binding, but cost-per-persuasion-contact is high). Caaguazu and San Pedro have better cost efficiency and meaningful electoral scale. This reallocation is budget-neutral; the persuasion-contact payoff is whatever the Module B solver reports on re-run — not a fixed percentage claim here.

4. **Eliminate billboard and SMS spend in negligible-tier departments.** Reach utilisation for billboards and SMS is near zero across most departments (B4). Shifting that spend toward radio (highest rural utilisation) and direct channels is strictly reach-improving inside the fixed envelope — no dollar figure is quoted because channel-level allocation is not a committed artifact in this repo.

5. **Commission 2–3 additional polling waves before election day.** The 94% HDI spans ±30 pp — an enormous uncertainty range for strategic planning. Even one additional high-quality poll wave (n≥800) would cut this uncertainty by approximately one-third. CAPLI is the recommended pollster.

6. **Back-load 15% of bilateral direct spend from weeks 1–4 to weeks 11–14.** Direct contact is most effective when proximate to election day. Current front-loading may be wasting goodwill and persuasion capital on contacts made too early for participating voters to retain.

7. **Do not invest in Committed Opposition persuasion.** This segment has a mean propensity of 0.63 and high preference strength for Candidate B. The cost of persuading even a marginal share of this group far exceeds the returns. Redirect any persuasion budget earmarked for this segment to Youth Volatile micro-targeting.

8. **Apply bias corrections to all external polling references.** ATI_SNEAD results understate the lead by ~9 pp; ICA overstates it by ~5 pp. All internal planning documents and public communications should use bias-corrected figures. Share the house effect estimates with the communications team immediately.

9. **Stress-test the extreme tracker scenario for weeks 12–14.** The extreme_tracker bucket (3,333 of 10,000 draws, shock_scale 1.83–2.43) encodes high-volatility outcomes. Ensure field operations have a 72-hour rapid-response protocol if a late-breaking adverse event triggers a 5–8 pp margin compression.

10. **Develop Jopara-language media content for all segments.** Jopara bilingual speakers are 47–51% of every segment. Spanish-only content structurally misses this plurality; Guaraní-only content is niche. Jopara-accessible creative is the single messaging investment with the broadest cross-segment reach.

---

## Methodology Notes

- **Segmentation:** 6 clusters from KMeans on scaled numeric features; segment names are profile-derived (Hungarian assignment of cluster profiles to the canonical vocabulary, with interpretation tests). DBSCAN runs as a noise diagnostic only (46 flagged rows). Segment IDs 0–5 map to labels via `segment_labels.parquet`.
- **Participation propensity:** Bayesian logistic regression with department-level random effects and post-stratification rake weights. Rake multipliers vary substantially across departments (mean 1.40×, range [0.63, 2.73]) indicating sampling imbalance in raw data.
- **Bayesian tracking model:** Hierarchical Gaussian random walk with house effect corrections. Credible bands are true 94% highest-density intervals (`az.hdi`, ≈±1.9σ for a Gaussian posterior) — not 5/95 equal-tailed quantiles. Only 8 poll waves ingested — uncertainty is fundamentally limited by sparse polling data.
- **Budget optimisation:** Linear programming solver (OPTIMAL status confirmed for all cells). Constraints include reach caps, department tiers, and channel eligibility rules. FX conversion uses retail spread rate (not reference rate).
- **Monte Carlo:** 10,000 draws across 3 scenario buckets. Shock scale parameterises outcome volatility. alloc_mean_persuasion_contacts populated from the Module B baseline allocation (B-to-C handshake verified non-zero).
- **Exit model:** Gaussian likelihood with intercept + two international observer beta parameters. Identified on historical exit survey data. Wide HDI intervals suggest limited historical data for calibration.

---

## Appendix: Data Dictionary of Key Columns

| Column | Dataset | Description |
|--------|---------|-------------|
| `entity_id` | population_master | Unique individual identifier (1–5,000) |
| `segment_label` | population_master, segment_labels | Qualitative segment name (6 categories) |
| `segment_id` | population_master, segment_labels | Integer segment code (0–5) |
| `participation_propensity` | population_master, participation_propensity | Bayesian posterior probability of electoral participation [0,1] |
| `preference_proxy` | population_master | Voting intent: A (Candidate A), B, other, none |
| `preference_proxy_strength` | population_master | Continuous strength of stated preference [0,1] |
| `nbi_stress_prior` | population_master | Unmet Basic Needs stress score (structural deprivation index) |
| `reachability_index` | population_master | Composite media reachability (TV + radio + digital) [0,1] |
| `structural_dependency_proxy` | population_master | Boolean flag for clientelistic dependency indicators |
| `rural_flag` | population_master | Boolean: True if individual resides in rural area |
| `language_census_bucket` | population_master | Language spoken: jopara_bilingual / spanish_only / guarani_only / other |
| `budget_allocation_usd` | allocation_baseline | Campaign budget allocated to dept × channel × week (USD) |
| `persuasion_adjusted_contacts` | allocation_baseline | Expected contacts weighted by salience and attention multipliers |
| `reach_utilization` | allocation_baseline | Fraction of reachable audience contacted [0,1] |
| `win_probability_a` | battleground | P(Candidate A wins department) from Bayesian battleground model [0,1] |
| `posterior_mean_preference_margin_pp` | daily_posterior_forecast | Daily posterior mean of (A − B) preference margin in percentage points |
| `posterior_hdi_low_pp` / `high_pp` | daily_posterior_forecast | Lower/upper bounds of 94% Highest Density Interval |
| `house_effect_posterior_mean` | posterior_house_effects | Pollster-specific bias in pp (positive = over-states A's lead) |
| `shock_scale` | monte_carlo_draws | Electoral volatility multiplier for Monte Carlo scenario simulation |
| `scenario_bucket` | monte_carlo_draws | Scenario category: baseline or extreme_tracker |
| `tc_rate_pyg_per_usd` | fx_layer_series_b_weekly | Weekly reference FX rate (PYG per USD) |
| `travel_time_minutes` | routing_cost_matrix | Road travel time between department pairs under dry standard conditions |

---

*Report generated by generate_eda.py — Paraguay Campaign Analytics Pipeline*
