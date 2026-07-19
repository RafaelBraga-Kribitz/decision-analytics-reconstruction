# Paraguay Campaign Analytics — Strategic Brief
**Portfolio reconstruction brief | Generated from pipeline artifacts**
**Date:** June 14, 2026 | **Analyst:** Decision Analytics Reconstruction

---

## Situation Assessment

The Bayesian tracking model closes at a **3.7 pp preference margin** on fixture polls (94% HDI: 2.8 to 4.7 pp). Illustrative model output on fixture survey polls — not verified outcome; TSJE Series A anchor is +3.70 pp. Modelled department win probabilities range **7%–100%**. Portfolio framing: use verified TSJE anchor (+3.70 pp) for outcome facts; treat tracking outputs as illustrative decision-support machinery.

---

## Top 3 Priority Departments

**1. Caaguazu (Budget: $468K, Modelled Win Prob: 53.5%, Propensity: ~0.58)**
Caaguazu is the top battleground department — tracking-implied win probability sits near the 50% threshold with visible HDI uncertainty. A strong Rural Committed presence (high propensity) and lower cost-per-persuasion-contact than metro departments make it the efficiency sweet spot for marginal persuasion spend.

**2. San Pedro (Budget: $340K, Modelled Win Prob: 60.0%, Propensity: ~0.58)**
San Pedro ranks among the most competitive departments after Caaguazu. Radio and canvassing channels reach Rural Committed segment efficiently here; protecting budget through the final fortnight is critical.

**3. Itapua (Budget: $494K, Modelled Win Prob: 72.8%, Propensity: ~0.65)**
Itapúa has the highest mean participation propensity of any department with significant Rural Committed presence. It is the dominant department for that segment. Radio is the primary reach channel. At near-saturation on reach utilisation, the channel is performing well — the risk is a budget cut that disrupts this performance. Protect Itapúa's radio budget unconditionally and explore whether a modest canvassing supplement in rural municipalities can push propensity-weighted turnout past 70%.

---

## Segment Strategy: Double Down vs Deprioritise

**Double Down:**
- **Youth Volatile (17.4% of population, propensity 0.58):** High reachability — the mobilisation opportunity. Digital-first (WhatsApp, Facebook), Jopara-friendly content, peer-to-peer activation via youth networks.
- **Rural Committed (13.8% of population):** Baseline propensity (0.58, typical of every segment) but distinctively low reachability. The case for protecting this segment is reachability, not a propensity edge: radio + canvassing are the only channels that reach it, so each contact is hard to replace. Do not sacrifice these voters to cut costs.

**Maintain:**
- **Urban High Volatility (17.6%):** Good reachability, propensity 0.65. Currently receiving fair budget share. No change needed — the strategy is working.
- **Structurally Dependent Bloc (18.1%):** High rural, high NBI stress. Sensitive segment requiring careful messaging. Maintain current radio + community organiser approach.

**Deprioritise:**
- **Committed Opposition (18.4%):** Participation propensity 0.63 (baseline, like every segment — it does *not* make them a mobilisation target), but their high, tightly clustered B-preference strength makes them locked opposition-aligned voters. Any persuasion spend here is waste. Reallocate immediately.
- **Rural Low Propensity (14.6%):** Propensity 0.64 — despite the name, in the same narrow band as every other segment; the label reflects its cluster profile, not a distinctly low turnout score. Passive presence only — no active spend increases warranted.

---

## Channel Mix Recommendation

| Channel | Recommended Action | Rationale |
|---------|-------------------|-----------|
| **WhatsApp Chatbot** | Increase 20% in weeks 11–14 | Highest reach utilisation in urban areas; peak effectiveness near election day |
| **Radio Spots** | Hold flat; do not cut | Irreplaceable for Rural Committed and Structurally Dependent Bloc; no substitute |
| **Facebook Ads** | Maintain current level | Good metro ROI; complements WhatsApp without cannibalising |
| **Canvassing** | Increase 10% in Itapúa, Caaguazu | Highest ROI per USD in Oriental mid-tier departments |
| **TV Spots** | Reduce 10% in weeks 1–5 | High cost, low marginal persuasion value vs. direct channels |
| **Billboards** | Eliminate in negligible-tier depts | Near-zero reach utilisation; money better spent on radio |
| **SMS** | Evaluate and likely eliminate | Worst reach utilisation of any channel; no evidence of incremental contact generation |
| **Sound Cars** | Maintain in Chaco only | Only viable channel in Alto Paraguay and Boquerón |

---

## Where Budget Is Being Underused

The solver runs reach-constrained — every department sits at reach_utilization = 1.0 (see B4) — so "underused" here means spend on channels that add little incremental reach, ranked by reach utilisation, not audited dollar overspend. Channel-level spend is not a committed artifact in this repo, so the items below carry no dollar estimate; they identify *where* to reallocate inside the fixed envelope, not *how much* is recoverable.

**1. Billboards and SMS:** the two lowest reach-utilisation channels — near-zero utilisation across most departments (B4). Reallocating their spend toward radio (highest rural utilisation) and direct channels is strictly reach-improving.
**2. Front-loaded bilateral spend (weeks 1–4):** direct contact made 10+ weeks before election day has low modelled retention; shifting it toward weeks 11–13 raises effective late-campaign contact. This is a modelling-assumption argument, not a measured loss.
**3. Persuasion spend on Committed Opposition:** this segment's B-preference strength is tightly clustered at high values, so persuasion contacts here are low-value regardless of volume. Redirect toward persuadable segments.
**4. Broadcast-to-direct scenario exploration:** the counterfactual redistributes the channel mix without increasing aggregate persuasion contacts; treat it as a sensitivity check, not a strategy.

**Reclaimable share:** the moves above shift spend *between* channels inside the fixed $6,029,991 envelope; they do not change the total, and its recoverable magnitude cannot be quoted here because the channel-level allocation output is not a committed artifact. The persuasion-adjusted payoff of any reallocation is whatever the Module B solver reports on re-run — not a number fixed in this brief.

---

## Forecast Risk Assessment

**Low risk (manageable within current strategy):**
- FX depreciation: ~1.8% over campaign window; hedge with USD commitments
- Polling uncertainty: Wide HDI is a data availability problem, not a trend problem. Commission 2 additional poll waves to confirm.

**Medium risk (requires contingency planning):**
- Late-breaking adverse events: The extreme-tracker bucket (3,333 of 10,000 draws) assumes 1.83–2.43× shock scale. A major scandal or crisis event in weeks 12–14 could compress the margin by 5–8 pp. Pre-position a rapid-response team.
- Participation depression in Youth Volatile: this segment's propensity is 0.58. If youth registration or turnout infrastructure fails (long queues, administrative errors), the mandate could shrink materially.

**Low but non-zero systemic risk:**
- Model miscalibration: Only 8 poll waves feed the tracking model. If all three pollsters share an unmeasured systematic bias not captured by the house effect model, the posterior could be significantly wrong. Diversify polling sources.

**Bottom line:** The outcome fact is the verified TSJE anchor — Candidate A carried the 2018 presidential election by +3.70 pp. The illustrative tracking model reproduces that direction (posterior 3.7 pp, 94% HDI 2.8–4.7 pp), but its wide HDI and 7%–100% department win-probability range reflect genuine uncertainty from sparse fixture polls — not a near-certain sweep, and several GANAR-winning departments sit below 50%. Read this brief as decision-support machinery, not a forecast. The defensible recommendations — invest in turnout, protect Rural Committed's irreplaceable radio/canvassing reach, mobilise the high-reachability Youth Volatile segment, reallocate the lowest reach-utilisation channel spend, and widen polling coverage — follow from the allocation and reachability structure and hold across the plausible range of the true margin. Their support is structural, not a claim of statistical certainty about the outcome.

---

*Reconstruction artifact — strategic brief generated from pipeline outputs by reports/eda/generate_eda.py. Illustrative decision-support framing; see reports/epistemic_boundaries.md.*
