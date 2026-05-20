---
doc_id: DOC-RES-011
doc_type: research
doc_role: reference
visibility: public
status: active
owner: research
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# Currently, Facebook Ads (ch_facebook_ads) is alrea...

导出时间: 14/05/2026, 22:51:22

---

Currently, **Facebook Ads** (`ch_facebook_ads`) is already fully integrated into the system's 11-channel taxonomy as a broadcast-to-bilateral channel, modeled on a USD-per-impression basis with direct response/conversion attribution\[1\].

However, **Instagram Ads, Google Ads (and the Google Display Network), and LinkedIn Ads** are completely absent from the project\[1\].

To realistically add these three platforms into the Decision Analytics System and have the Module B optimizer allocate budget to them, we need to gather specific historical data for the Paraguayan market during the early 2018 campaign window. Here is the exact missing data required by the system's architecture:

**1\. Reachability and Penetration (Module A)**We need to know exactly who was on these platforms in early 2018 so the K-Means segments can be accurately targeted. We need:

**Active User Base:** The total reachable audience size in Paraguay for Instagram, Google Network, and LinkedIn\[2\].

**Demographic Penetration:** How usage varied by urban vs. rural locations, age brackets, and structural dependency to update the `media_reachability_by_segment` matrix\[3\],\[4\]. (For example, LinkedIn will likely skew heavily toward the Urban High Volatility segment, while Google Search might have broader but shallower reach).

**2\. Unit Economics and Financials (Module B)**The Mixed-Integer Linear Program (MILP) optimizer needs precise costs to calculate the expected return on ad spend. We need:

**Average Cost Per Click (CPC) or Cost Per Mille/Impression (CPM)** in USD for Instagram, Google Search/Display, and LinkedIn specifically targeting Paraguayan users in Q1 2018\[2\],\[1\].

**3\. Response Curve and Saturation Metrics (Module B)**The system uses a diminishing returns model to prevent overspending on a single channel\[5\]. To configure these new networks, we need:

**Platform Salience & Attention Multipliers:** Estimates of how effective an impression is on LinkedIn vs. Instagram vs. Google Search\[2\].

**Diminishing Returns Variables:** The inflection point (`diminishing_returns_inflection_pct`) indicating at what budget threshold the audience on these specific platforms becomes saturated and stops converting\[2\].

### Deep Search Plan

Since this data is highly specific to the 2018 Latin American digital advertising market, we will need to query digital marketing reports (such as Datareportal's "Digital 2018 Paraguay" report), historical ad-spend benchmarks, or Meta/Google transparency reports from that era.

I can run a comprehensive search for this using the following prioritized queries:

**Audience Size:**`Find Datareportal or Hootsuite/WeAreSocial "Digital 2018 Paraguay" report data detailing the exact active user counts and demographic penetration for Instagram and LinkedIn in Paraguay during early 2018.`

**Ad Costs:**`Find historical digital marketing benchmarks from Q1 2018 showing the average CPC (Cost Per Click) and CPM (Cost Per Mille) in USD for Google Ads, Instagram Ads, and LinkedIn Ads in Paraguay or Latin America.`

Before I initiate a `deep_research` search on the public web, could you confirm which of these two topics we should prioritize first? Please note that deep research handles one query at a time and takes several minutes to complete.
---

## 引用来源

[1] scope_module_B_resource_allocation_engine.md
[2] reach_caps_baseline.csv
[3] data_dictionary.md
[4] media_reachability_by_segment.csv
[5] response_curve_spec.md
