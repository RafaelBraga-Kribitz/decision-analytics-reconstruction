---
doc_id: DOC-MODCRS-003
doc_type: methodology
doc_role: derived
visibility: public
status: active
owner: module_c
last_reviewed: '2026-05-20'
canonical_source:
- DOC-MODC-001
derived_from:
- DOC-MODC-001
supersedes: null
tags: []
allowed_content:
- interpretation
- summarization
forbidden_content:
- novel_metrics
- novel_claims
---

# TSJE calibration — Series A vs Series B

**Status:** stub for research lock-in. Replace bracketed placeholders with bulletin line citations.

## Series A — valid-vote shares (repo default)

- Candidate A: **46.43%** `[VERIFIED — TSJE]`
- Candidate B: **42.73%** `[VERIFIED]`
- Margin `m*`: **+3.70 pp**

## Series B — final official headline pair

- Candidate A: **48.96%** `[VERIFIED]`
- Candidate B: **45.08%** `[VERIFIED]`
- Margin `m*`: **+3.88 pp`

## Rule

Do not mix numerators from one series with denominators from the other. Active series is `module_c_forecasting_scenarios/config/calibration.yaml` → `series`.
