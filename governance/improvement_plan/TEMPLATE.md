# TEMPLATE — Improvement Specification Document

This template defines the mandatory format for every `IMP-*` document in this
directory (and in `Chart_Audit_Framework/improvement_plan/`). These documents
are **specifications, not code**: prose, schemas, thresholds, and queue stubs
only. They feed the two existing work queues defined in
`governance/AUDIT_PROCEDURE.md` — they do not define a new methodology, role,
tier, or scoring system.

Every document has YAML front matter followed by exactly five sections.

---

```yaml
---
id: IMP-X00                      # series A|B|C|V (this repo) or F (Chart_Audit_Framework)
title: "One-line change summary"
absorbs: [X0, X0]                # audit finding codes from INDEX.md traceability matrix
overlaps_triage: []              # related open AUD-* rows in governance/ISSUE_TRIAGE_MASTER.yaml
priority: P0 | P1 | P2
effort: low | medium | high      # implementation effort, per .github/labels.yaml scale
depends_on: []                   # IMP ids that must be DONE first (hard deps only)
soft_depends_on: []              # IMP ids that should ideally land first
queue: findings | issues | dual  # which existing queue executes this change
target_repo: decision-analytics-reconstruction | Chart_Audit_Framework
issue: null                      # GitHub issue number once filed
status: draft                    # draft -> approved -> filed -> done
---
```

## 1. Define the Scope (The Data Guardrails)

**In-Scope:** concrete, bounded statements of what this change covers — the
exact files, models, pipeline stages, artifacts, and data ranges affected.

**Out-of-Scope:** explicit exclusions, especially adjacent work that belongs to
another IMP document (name it) or to no document at all.

## 2. Data-Driven "Given-When-Then" Scenarios

BDD scenarios adapted to data distributions, feature engineering steps, and
model outputs. At minimum: one happy path and one edge case. Each scenario must
be phrased against **observable artifacts** (files, columns, metric values,
exit codes) — never intentions.

**Scenario: <name> (Happy Path)**
- **Given** <precondition on data/config/artifact state>
- **When** <the pipeline stage / command runs>
- **Then** <observable, verifiable outcome with concrete thresholds>

**Scenario: <name> (Edge Case)**
- **Given** / **When** / **Then** as above.

## 3. Specify Undesirable Behaviors (Negative Constraints)

What the pipeline/model/chart must **never** do after this change — silent
failure modes, leakage paths, fabrication, mislabeling. Each constraint as a
scenario:

**Scenario: Preventing <failure mode>**
- **Given** / **When** / **Then** — where the *Then* states the required
  refusal, abort, log, or disclosure behavior.

## 4. Detail Data-Specific Non-Functional Requirements

- **Model fairness / bias:** protected attributes, proxies, or population
  subgroups this change must not distort (or `N/A — <reason>`).
- **Performance & decay:** runtime bounds, metric floors/ceilings, and the
  monitoring trigger if the metric decays (concrete numbers, not adjectives).
- **Data integrity:** the schema-drift / NULL / out-of-range abort conditions
  this change must enforce, and which validator enforces them.
- **Reproducibility:** seed, tolerance, and cross-run stability requirements.

## 5. Queue Stub (ready to file)

For `queue: findings` — a complete finding YAML matching
`governance/findings/F-TEMPLATE.yaml`, with `id: F-XXX` left as a placeholder
(numbers are assigned at filing time, never reserved here) and a **proposed**
`verification_script` path plus a one-paragraph description of what that
script must check (writing the script is the first half of the remediation,
per AUDIT_PROCEDURE.md).

For `queue: issues` — the verbatim GitHub issue body, plus the label set
(`type:`, `skill:`, `effort:`, `priority:`, and `status:claude-ready` only if
`depends_on` is empty).

For `queue: dual` — both stubs, with one sentence delimiting which slice of
the change each queue item owns.
