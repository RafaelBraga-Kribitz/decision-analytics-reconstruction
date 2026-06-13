# Chart-Audit Completion Sprint — 2026-06-13

Declared per `governance/adrs/0001-completion-sprint-cadence.md` to authorise
themed multi-finding work that burns down the **F-054** backlog
(`governance/ISSUE_TRIAGE_MASTER.yaml` reject/critical rows). Without this
committed plan, the one-finding-per-PR rule applies with no exception.

## Scope

F-054 is the umbrella tracker; it stays **open** until every reject/critical
triage row is filed or resolved. This sprint files them **one finding at a
time**, criticals first, along the Module C → B → A critical path. Each finding
ships its own static verification gate over `reports/eda/generate_eda.py` (no
data dependency, matching F-053/F-055); the canonical PNGs regenerate via
`make pipeline-full` (F-050 lineage) and the CI adversary re-checks every gate.

## Tractable presentation / disclosure findings (this sprint)

| Finding | Triage row | Theme |
|---|---|---|
| F-055 | AUD-C1 | C1 retrodiction label + verified anchor drawn (done, PR #9) |
| F-056 | AUD-C2 | C2 terminal posterior is anchor-calibrated — disclose the pinning |
| F-057 | AUD-C5 | C5 MC fan chart — honest x-axis / re-type for discrete scenarios |
| F-058 | AUD-C6 | C6 shock-scale is discrete point masses — no KDE |
| F-059 | AUD-C9 | C9 polling-transparency small-n (n=3) disclosure |
| F-060 | AUD-C10 | C10 content must match its win-probability filename/title |
| F-061 | AUD-B3 | B3 must not stack mutually exclusive scenarios |
| F-062 | AUD-B7 | B7 routing matrix fully labelled, no orphan channel |
| F-063 | AUD-S5 | S5 "efficiency frontier" honestly labelled |
| F-064 | AUD-A12 | A12 reachability distribution readable |
| F-065 | AUD-PUB-004 | eda_overview scope label + non-truncated bars |

## Explicitly deferred — architecturally significant (need a human decision)

These are **not** chart-presentation fixes: they require model / data-generation
changes plus full pipeline regeneration, and overlap the project's own
`post_publish_backlog`. They will not be claimed "solved" by a chart edit.

- **AUD-A10 / F-052 family** — individual covariates are department constants
  (generative-model change; "Non-circular propensity evaluation, A-3 deep").
- **AUD-BMC** — Monte-Carlo persuasion contacts flat across scenarios
  (MC → forecast coupling, C-10 deep).
- **AUD-B5 / AUD-B8 / AUD-S4** — cost-per-contact plausibility, contacts-vs-caps,
  and priority-score circularity depend on regenerated allocation values, not
  just chart styling; triaged before filing.
