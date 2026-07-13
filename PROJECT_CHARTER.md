<!--
================================================================================
PROJECT CHARTER: Single Source of Truth (SSOT)
================================================================================
This document is the authoritative source for project goals, scope, requirements,
and design decisions. Detailed implementation notes live in derived docs and ADRs.
Cap at 600 lines.
================================================================================
-->

<!-- SSOT_METADATA_START
version: 0.1.0
status: active
last_updated: 2026-06-08
last_reviewed: 2026-06-08
owner: Rafael Braga
project_codename: decision_analytics_reconstruction
SSOT_METADATA_END -->

# Project Charter: Decision-Analytics Reconstruction Platform

> This is the Single Source of Truth (SSOT). Project goals, scope, and operating
> governance live here or in `governance/adrs/`. Derived docs must link back to
> this file instead of restating authority.

## 1. Quick Facts

| Field | Value |
|---|---|
| Project codename | `decision_analytics_reconstruction` |
| Owner | Rafael Braga |
| Primary goal | Produce reproducible decision-analytics workflows with governed inputs, allocation logic, scenario modeling, and evidence-backed outputs. |
| Status | governance replacement in progress |

## 2. Documentation Discipline

This file is the SSOT. No parallel requirements, plan, or roadmap documents are
active. State each decision once, link everywhere else, and record durable
changes in `governance/adrs/` plus `governance/CHANGELOG.md`.

Full rules: `CONTRIBUTING.md` and `governance/AUDIT_PROCEDURE.md`.

## 3. Business Case

### 3.1 Problem Statement

Complex programs often need to allocate limited resources across heterogeneous
geographies and audiences while preserving traceability, uncertainty awareness,
and reproducible evidence. This project reconstructs that decision layer as a
portfolio-grade analytical system rather than a single notebook or dashboard.

### 3.2 Project Goal

Deliver a governed, reproducible three-module analytics platform that turns a
synthetic voter population, resource constraints, and poll inputs into
traceable allocation and scenario outputs.

### 3.3 Success Criteria

The project succeeds if all of these are true:

| Criterion | Measurement | Verification |
|---|---|---|
| Module contracts remain stable | Schema YAMLs cover all cross-module artifacts | `schema_contracts/` plus architecture tests |
| Core workflows are reproducible | Make targets run from a clean Poetry environment | `make test`, module smoke targets, CI |
| Governance state survives sessions | Findings and handoffs are generated from disk | `make session-start`, `governance/AUDIT_STATE.json` |
| Technical debt cannot grow silently | Debt metrics stay at or below baseline | `make debt-check` |
| Public-facing docs have one authority | Root docs link to this Charter and ADRs | Manual review + `governance/adrs/` |

### 3.4 Stakeholders

| Stakeholder | Role | Engagement |
|---|---|---|
| Rafael Braga | Owner and maintainer | Daily |
| Portfolio reviewers | Technical audience | As needed |
| Future maintainers | Operators of the workflow | As needed |

### 3.5 Out of Scope

- Real-time production decisioning.
- External SaaS governance bots or LLM judges.
- Reworking module internals outside a filed `governance/findings/F-*.yaml` item.
- Treating generated data or report outputs as source authority.

### 3.6 Known Limitations

- The maintainer machine is CPU-only for practical purposes; workflows must stay
  compatible with the Mac Pro 6,1 constraints documented in Cursor rules.
- Some historical docs and artifacts are retained in `maintainer/archive/` for
  audit trail only.
- Current test and lint baselines include inherited failures recorded before this
  governance replacement.

## 4. Documentation Index

| Document | Purpose | Location |
|---|---|---|
| Methodology | Steward / Remediator / Adversary roles | `governance/AUDIT_PROCEDURE.md` |
| Agent Protocol | Session-start contract | `CLAUDE.md` |
| Contributor Rules | Finding workflow and PR rules | `CONTRIBUTING.md` |
| ADRs | Append-only decision log | `governance/adrs/` |
| Change Log | Version history | `governance/CHANGELOG.md` |
| Architecture | Derived technical map | `ARCHITECTURE.md` |
| Deployment | Cloud Run deployment guide | `docs/DEPLOYMENT.md` |

<!-- END OF SSOT. Any content below this line is a violation. -->
