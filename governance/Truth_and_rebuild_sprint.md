# Truth and Rebuild Sprint — Multi-Agent Coordination

**Updated:** 2026-06-12  
**Human walkthrough:** complete — parallel agent audit in progress.

## Agent lanes

| Agent | Scope | Status |
|-------|-------|--------|
| **CL Agent** | `make lint`, Black, ruff, F-008 radon, `make debt-check`, typecheck | **DONE** (see below) |
| **Sprint Agent** | `make verify`, findings queue, test gaps | **DONE** — F-041, F-043, F-044 closed |
| **Deploy Agent** | Live URLs, DEPLOYMENT.md, `check_live_deployment_urls.py` | **BLOCKED** — F-021 Module A timeout |

## CL Agent — final snapshot

| Gate | Status |
|------|--------|
| `make lint` (ruff + black --check) | **PASS** |
| F-008 (`check_radon_complexity_zero.py`) | **CL owns** — sprint note: possible regression `radon_complex_blocks=1` (do not fix in Sprint Agent pass) |
| `make debt-scan` | **PASS** — baseline locked at 0 |
| `make typecheck` | **PASS** (pyright on module src) |
| `make verify` | **FAIL** — F-021 deploy timeout (Deploy Agent); other sprint findings cleared |

### F-008 remediation (CL Agent)

- Refactored high-CC functions across `scripts/`, modules A/B/C, and `tests/`
- Worst offenders reduced: `allocation.solve` F(67)→A(2), `verify_doc_registry.main` F(77)→split helpers
- Debt baseline: `governance/DEBT_BASELINE.json` → `radon_complex_blocks: 0`
- **Sprint Agent note:** re-run `check_radon_complexity_zero.py` before merge; if `radon_complex_blocks=1`, CL Agent must re-close F-008 without Sprint Agent touching radon refactors

## Sprint Agent — closed findings (2026-06-12)

| Finding | Verification | Summary |
|---------|--------------|---------|
| **F-041** | `check_terminology_compliance.py` | Public markdown uses scope §12 terms (survey measurement, program, participation rate); Module C README exit/quickcount prose fixed |
| **F-043** | `check_tracked_operator_artifacts.py` | Untracked 68 operator maintainer paths; `.gitignore` tightened to `maintainer/*` with only `doc_debt/` exception (3 files tracked, ≤40) |
| **F-044** | `check_module_a_config_wiring.py` | `reachability.py` loads `reachability_weights` from `model_params.yaml`; YAML header documents wired vs unwired keys |

**Skipped (CL Agent):** F-008 radon — note only, no refactor in this pass.

## Deploy Agent — handoff

- **F-021 regression:** `module_a_streamlit=Timeout` (Render); B and C return 200
- Owns `scripts/check_live_deployment_urls.py` URL list and `docs/DEPLOYMENT.md`
- Do not edit allocation/model code

## Conflict rules

1. One agent per file — note in **Active locks** before editing
2. CL Agent owns lint/format/complexity; Deploy Agent owns live URL checks
3. Update this file each audit loop; commit only when human requests

## Active locks

| File | Agent | Since |
|------|-------|-------|
| — | — | Sprint pass complete; locks cleared |
