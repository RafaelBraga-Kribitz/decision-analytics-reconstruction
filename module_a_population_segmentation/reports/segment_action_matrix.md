---
doc_id: DOC-MODA-005
doc_type: narrative
doc_role: canonical
visibility: public
status: active
owner: project
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Segment Action Matrix

Maps each behavioral segment to the recommended channel mix, priority tier, and operational rationale.
This document is the primary bridge between Module A segmentation outputs and Module B allocation inputs.

**Status:** Verified against Module A segment profiles and Module B channel taxonomy.
**Source:** `segment_labels.parquet`, `media_reachability_by_segment.csv`, `calibration_anchors.yaml`

---

## Summary table

| Segment | Size | Propensity | Priority tier | Primary channel | Secondary | Do not invest |
|---------|------|-----------|--------------|----------------|-----------|---------------|
| Rural Committed | 14.4% | 0.71 (high) | T1 — Protect | Radio | Community mobilization | Digital (dark) |
| Urban High Volatility | 18.6% | 0.77 (high) | T1 — Maximize | TV spots + WhatsApp | Direct (canvassing) | — |
| Youth Volatile | 31.3% | 0.49 (moderate) | T2 — Convert | WhatsApp | Social / SMS | Radio (low reach) |
| Structurally Dependent | 13.1% | 0.58 (moderate-high) | T2 — Mobilize | Community + Radio | Direct | Digital |
| Rural Low Propensity | 12.4% | 0.35 (low) | T3 — Passive | Radio (passive) | — | Any high-cost direct |
| Committed Opposition | 10.2% | 0.10 (locked) | T4 — Do not target | — | — | All channels |

---

## Segment profiles and action rationale

### Rural Committed (14.4% · propensity 0.71)

**Who they are:** Rural population, older age mix, Guaraní-dominant or Jopará bilingual, low NBI stress relative to rural average. Already favorable to the program outcome.

**Strategic role:** Protect and mobilize. These entities are high-value (high propensity) but digitally dark — WhatsApp and social channels do not reach them. Investing in digital here is wasted spend.

**Recommended actions:**
- Maintain radio spot frequency in rural departments (Guairá, Misiones, Paraguarí) throughout weeks 1–14.
- Community mobilization via local leaders is the marginal high-ROI add; slot budget in weeks 6–10.
- Do not reduce radio budget below baseline even if Module B optimization proposes reallocation to digital — this segment is the radio channel's primary addressable population.

**Budget priority:** Protect against downward reallocation. Underserving this segment is the highest participation-rate loss scenario.

---

### Urban High Volatility (18.6% · propensity 0.77)

**Who they are:** Metro and peri-urban population (Central, Asunción, Alto Paraná), younger-to-middle age, digitally reachable, Spanish-dominant or Jopará, low NBI stress. The highest-propensity segment in the urban stratum.

**Strategic role:** Maximize conversion. High propensity + high reachability = highest ROAS of any segment. TV + WhatsApp combined reach is high; direct canvassing effective in dense urban precincts.

**Recommended actions:**
- TV spots in Asunción and Alto Paraná metro: front-load weeks 1–6 for awareness; reinforce weeks 11–14 with turnout messaging.
- WhatsApp activation: weeks 4–14 (conversion-stage messaging after initial TV exposure).
- Direct canvassing: concentrated in peri-urban precincts with high youth concentration within this segment.

**Budget priority:** T1 — allocate proportionally to share (18.6%) plus a multiplier for ROAS efficiency. Cap at reach saturation before reallocating.

---

### Youth Volatile (31.3% · propensity 0.49)

**Who they are:** Ages 18–29, high digital access (WhatsApp-first), distributed across urban and peri-urban areas, moderate NBI. The largest segment; moderate propensity with high sensitivity to mobilization.

**Strategic role:** High-volume conversion opportunity. At 31.3% of population, moving this segment's effective participation rate by even 2 pp is equivalent to a national participation rate lift of 0.63 pp. The program's aggregate +3.70 pp outcome was partly driven by youth mobilization in this segment.

**Recommended actions:**
- WhatsApp is the primary and almost exclusive effective channel. Allocate aggressively from week 3 onward.
- SMS as secondary (lower deliverability but lower cost; useful for final-week reminders).
- Avoid TV and radio for this segment specifically — budget spent here has near-zero marginal return.
- Message framing: peer-norm and social proof messages outperform institutional messaging for this cohort.

**Budget priority:** T2, but by total budget weight this is the largest single allocation target. WhatsApp budget should scale with segment size, not segment propensity.

---

### Structurally Dependent Bloc (13.1% · propensity 0.58)

**Who they are:** Rural-to-peri-urban, elevated NBI stress index (DGEEC Censo 2012 proxy), Jopará or Guaraní-dominant, structural economic dependency. Moderate-to-high propensity; significant NBI stress means outreach barriers are practical as well as informational.

**Strategic role:** Mobilize with friction reduction. These entities are sympathetic to the program but face logistical and informational access barriers. Community channels (local leaders, events at accessible gathering points) outperform broadcast.

**Recommended actions:**
- Community events and local leader mobilization in San Pedro, Caazapá, Canindeyú (highest structural dependency by department-rural strata).
- Radio spots as a second layer.
- Digital spend is not effective here — internet penetration in the target strata is below 28%.

**Budget priority:** T2 — efficiency-adjusted per-contact cost is higher than T1 segments due to community mobilization logistics. Allocate to weeks 4–12 (avoid final-week concentration which requires advance logistics).

---

### Rural Low Propensity (12.4% · propensity 0.35)

**Who they are:** Rural, older, low digital access, no strong structural dependency signal. Propensity is low; these entities are neither committed supporters nor committed opposition — they are disengaged.

**Strategic role:** Passive reach only. Attempting to convert this segment with targeted spend would require 3–5× the per-contact investment of the T1 segments for a fraction of the participation-rate lift. High-cost direct channels produce negative ROAS here.

**Recommended actions:**
- Passive radio exposure only (no incremental budget above baseline broadcast).
- Do not allocate canvassing, WhatsApp, or community event spend to this segment.

**Budget priority:** T3 — appear in Module B allocation only via passive broadcast coverage that reaches other segments in the same geographic units. No targeted spend.

---

### Committed Opposition (10.2% · propensity 0.10)

**Who they are:** Entities with a stable, locked preference for the opposing outcome (propensity 0.10). Represented across geographic and demographic strata; not primarily identified by demographic features but by preference proxy signals.

**Strategic role:** Do not target. Persuasion spend on this segment has effectively zero return and risks activating motivated opposition turnout.

**Recommended actions:**
- Exclude from all addressable channel targeting lists.
- The ~$8,000 in budget that would otherwise reach this segment (at average channel cost rates) is reallocated to Youth Volatile WhatsApp activation.

**Budget priority:** T4 — zero allocation. The segment's existence in the model is a budget-protection mechanism, not a targeting signal.

---

## Module B integration

This matrix maps to Module B's optimization problem as follows:

| Matrix concept | Module B variable |
|----------------|-------------------|
| Priority tier | `persuasion_weight[segment_affinity(d,c)]` in the LP objective |
| Do not invest (channel exclusion) | Upper bound constraint `x[d,c,w] = 0` for that (segment, channel) pair |
| Primary channel | Highest `persuasion_weight` for the segment × channel cross |
| Segment size | Population denominator for `reach_cap[d,c]` per department |

The `media_reachability_by_segment.csv` artifact (produced by Module A) provides the `primary_reach_channel` and per-segment reach proportions that Module B reads to construct the persuasion weight matrix.
