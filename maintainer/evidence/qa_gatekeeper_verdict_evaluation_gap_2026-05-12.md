---
doc_id: DOC-EVID-001
doc_type: evidence
doc_role: evidence
visibility: internal
status: archived
owner: harness
last_reviewed: '2026-05-20'
canonical_source: null
derived_from: null
supersedes: null
tags: []
---

# QA gatekeeper verdict — evaluation gap remediation

**Date:** 2026-05-12  
**Scope:** CI `poetry install` semantics, Module A rural WhatsApp anchor vs `generation.yaml`, markdown repo-root `.py` path guard (`scripts/verify_doc_code_paths.py`), README/ROADMAP MLflow opt-in note, decision log errata for stale external path claims.  
**Verdict:** **PASS WITH CAVEATS**

## PASS evidence

- `.github/workflows/ci.yml` Module A/B/C and tier3 install steps use full `poetry install` (with extras where applicable) so pytest jobs see editable first-party packages.
- `make validate` passes locally including `doc-path-verify`.
- `module_a_population_segmentation` generator tests include `TestWhatsAppPenetrationFromConfig`; non-slow suite green under current branch.

## Caveats (explicit)

1. **Pre-commit ruff hook** uses `--fix --exit-non-zero-on-fix`. A full `pre-commit run --all-files` can exit non-zero after normalizing files that were not part of this remediation; **`make lint` remains the authoritative no-fix gate** until a dedicated ruff-formatting PR lands.
2. **`verify_doc_code_paths.py`** only resolves inline codes that start with known repo-root prefixes (`module_*`, `scripts/`, `tests/`, etc.); shorthand filenames in older audit prose are intentionally skipped to avoid false positives.

**Reviewer instruction:** Treat caveats as tooling boundaries, not functional regressions for the evaluation-gap items above.
