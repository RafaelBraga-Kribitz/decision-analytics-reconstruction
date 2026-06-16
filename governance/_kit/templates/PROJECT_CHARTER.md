<!--
================================================================================
PROJECT CHARTER: Single Source of Truth (SSOT)
================================================================================
This document is the ONLY authoritative source for project goals, scope,
requirements, and design decisions.

RULES (enforced by CI):
  1. Any project decision that is not in this document or in governance/adrs/
     does not exist.
  2. Changes to anything in this file require a corresponding ADR entry.
  3. README.md and code docstrings MAY summarize from this file but MUST link
     back here for authority.
  4. The metadata block below is machine-read by scripts/check_charter_size.py.

DO NOT create separate Charter.md, Requirements.md, SRS.md, etc. Sprawl is
forbidden. Cap at 200 lines.
================================================================================
-->

<!-- SSOT_METADATA_START
version: 0.1.0
status: active
last_updated: 2026-01-01
last_reviewed: 2026-01-01
owner: {PROJECT_OWNER}
project_codename: {PROJECT_SLUG}
SSOT_METADATA_END -->

# Project Charter: {PROJECT_TITLE}

> **This is the Single Source of Truth (SSOT).** If you are looking for what
> the project is, what it does, what it does not do, or why a decision was
> made, **the answer is here or in [`governance/adrs/`](./governance/adrs/).**
> Nowhere else. CI enforces this discipline.

## 1. Quick Facts

| Field | Value |
|---|---|
| Project codename | `{PROJECT_SLUG}` |
| Owner | {PROJECT_OWNER} |
| Primary goal | {PROJECT_GOAL} |
| Status | bootstrapping |

## 2. Documentation Discipline

This file is the SSOT. No parallel requirements, spec, or design documents.
State it once, link everywhere else. Every scope change needs an ADR in
`governance/adrs/`. Every content change needs a `governance/CHANGELOG.md`
entry and a `last_updated` bump.

Full rules: `CONTRIBUTING.md` and `governance/AUDIT_PROCEDURE.md`.

## 3. Business Case

### 3.1 Problem Statement

<!-- 2-4 sentences. What problem does this project address? Who has it? -->

### 3.2 Project Goal

<!-- 1 sentence. The single thing that, when done, makes this project a success. -->

### 3.3 Success Criteria

The project succeeds if **all** of these are true at completion:

| Criterion | Measurement | Verification |
|---|---|---|
| <criterion 1> | <how measured> | <where verified> |
| <criterion 2> | <how measured> | <where verified> |

### 3.4 Stakeholders

| Stakeholder | Role | Engagement |
|---|---|---|
| {PROJECT_OWNER} | Owner | Daily |

### 3.5 Out of Scope

<!-- Hard scope locks. Adding anything here requires an ADR + scope-change review. -->

### 3.6 Known Limitations

<!-- Constraints accepted at v1.0. -->

## 4. Documentation Index

| Document | Purpose | Location |
|---|---|---|
| Methodology | Three roles, finding lifecycle | `governance/AUDIT_PROCEDURE.md` |
| Agent Protocol | LLM session contract | `CLAUDE.md` |
| Contributor Rules | Standards, PR rules | `CONTRIBUTING.md` |
| ADRs | Append-only decision log | `governance/adrs/` |
| Change Log | Version history | `governance/CHANGELOG.md` |

<!-- END OF SSOT. Any content below this line is a violation. -->
