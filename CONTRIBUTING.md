# Contributing to decision_analytics_reconstruction

## The five rules

1. **Every session begins with `make session-start`.** Read `governance/SESSION_HANDOUT.md` before opening any file.
2. **One finding per PR.** PR title contains `F-NNN`. Exception: trivial cross-cutting cleanups under 10 lines.
3. **Close findings only when their `verification_script` exits 0.** Editing `status: closed` without a passing script is forbidden — CI's Adversary job will reopen it.
4. **No scope changes without an ADR.** Any change to `PROJECT_CHARTER.md` requires a corresponding append-only entry in `governance/adrs/`.
5. **Debt cannot grow.** `make debt-check` runs in CI and fails any PR where dead code, duplication, or complexity rises past `governance/DEBT_BASELINE.json`. To raise the baseline (rare, intentional) it's a dedicated PR explaining why; to lower it, run `make debt-scan` and commit the smaller numbers.

## Banned anti-patterns

- "Comprehensive audit / review / scan / sweep" as a first action. The audit lives in `governance/AUDIT_STATE.json`; regenerate it via `make session-start`.
- Inventing a new scoring framework, dimension count, or audit tier. The methodology is `governance/AUDIT_PROCEDURE.md`.
- "Audited / fixed / closed / complete" in commits, PRs, or docs without a `verification_script` reference.
- Creating parallel docs (`TODO.md`, `PLAN.md`, `ROADMAP.md`, `SRS.md`, etc.). State lives in findings and ADRs.
- Hand-editing `governance/AUDIT_STATE.json` or `governance/SESSION_HANDOUT.md`. Both are machine-generated.

## Fresh-clone smoke test

Before claiming a release-ready branch, run from a clean tree (or fresh clone):

```bash
poetry install
make test
make verify
poetry run python scripts/check_fresh_clone_smoke.py
make graphify         # after any src/ or config change
```

`make pipeline-full` is optional and slow (CPU-only); it validates A→B→C→EDA when
`data/processed/` is populated.

`make verify` re-runs every closed finding's `verification_script` (Adversary locally).

## Filing a new finding

```bash
cp governance/findings/F-TEMPLATE.yaml governance/findings/F-XXX-short-slug.yaml
$EDITOR governance/findings/F-XXX-short-slug.yaml
```

Required fields: `id`, `title`, `category`, `kind`, `status: open`, `opened_at`, `evidence`, `verification_script`.

The `verification_script` must exist (or be created in the same PR). It must xfail or print `[GAP]` while the finding is open, and hard-fail / print `[FAIL]` if a closed finding regresses.

## Closing a finding

1. Make the change.
2. Run the verification script. Confirm `[PASS]` (script) or `passed` (pytest).
3. Update YAML: `status: closed`, `closed_at: <today>`.
4. Run `make verify`. All 0 open regressions.
5. Open the PR. Title contains `F-NNN`.

## Adding an ADR

```bash
cp governance/adrs/ADR-TEMPLATE.md governance/adrs/$(date +%N | head -c 4)-short-title.md
```

ADRs are append-only. To revisit a decision, mark the old one `superseded` and write a new one referencing it via `supersedes`.

## Technical-debt remediation

The debt ratchet (`scripts/debt_scan.py`) measures dead code, unused exports,
duplication, and complexity using whatever tools are installed (see
`governance/DEBT_TOOLS.md`). The workflow:

1. `make session-start` surfaces current debt hotspots in the handout.
2. Promote one hotspot into a finding (`governance/CATEGORIES.md` has the
   metric→category mapping). Its `verification_script` re-runs the tool scoped
   to the fixed area and asserts the metric hit zero.
3. Remediate one PR at a time. Do **not** mass-clean — that produces
   unreviewable diffs and breaks one-finding-per-PR.
4. After the fix lands, `make debt-scan` to lock the lower baseline.

## Tests and coverage

Root-level pytest modules live in `tests/` (cross-cutting contracts, CI, portfolio smoke). Per-module tests:

- `module_a_population_segmentation/tests/`
- `module_b_resource_allocation/tests/`
- `module_c_forecasting_scenarios/tests/`

| Command | Scope |
|--------|--------|
| `make test` | All module + root tests, excludes `-m slow`, with coverage on the three `src/` trees |
| `make coverage` | Same paths as `make test` but includes slow tests |
| `poetry run pytest <path> -q` | Targeted run |

**Policy:** Combined statement coverage across Module A, B, and C `src/` trees shall be **≥ 80%** on the default suite (`make test`).

Tests marked `@pytest.mark.slow` (full MCMC) are excluded from `make test`. Run with `MC_FAST=1 poetry run pytest module_c_forecasting_scenarios/tests -m slow`.

`tests/test_reproducibility.py` and `tests/test_eda.py` validate pipeline artifacts and EDA outputs; they **skip** on a fresh clone until `make pipeline-full` has run.

## Module C — full NUTS / PyTensor setup (#142)

Full MCMC gates (Module C tracking NUTS) require a **C++ compiler** so PyTensor can build C extensions. Without one, PyTensor falls back to pure Python and a single full-NUTS fit can exceed 10 minutes.

| Platform | Setup |
|----------|--------|
| **Windows** | [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with “Desktop development with C++” |
| **Linux / WSL** | `conda install -c conda-forge gxx` or system `g++` |
| **macOS** | Xcode command-line tools (`xcode-select --install`) |

For local development and CI-speed checks, use the sanctioned fast sampler:

```bash
MC_FAST=1 poetry run pytest module_c_forecasting_scenarios/tests -m slow
```

`MC_FAST=1` selects reduced `draws`/`tune` from `module_c_forecasting_scenarios/config/pymc_sampler.yaml`. Out-of-sample walk-forward evidence lives in [`reports/module_c/walk_forward_loo_report.md`](reports/module_c/walk_forward_loo_report.md) (6 holdouts, 8 waves, honestly caveated).

## Coding standards

<!-- Fill in once the project picks a language/framework. Examples:
- Python: black + ruff + pyright strict; snake_case; type hints required on public APIs
- TypeScript: prettier + eslint; strict mode; no `any` without an inline comment justifying
-->
