# Technical-Debt Tooling

The debt ratchet (`scripts/debt_scan.py` + `scripts/check_debt_ratchet.py`) is
tool-agnostic: it runs whatever specialized analyzers are installed and gates
only the metrics it can actually measure. Install the rows that apply to your
project's languages. Missing tools are skipped (not fatal) but leave that
dimension of debt unguarded.

## Python

| Debt dimension | Tool | Install | Metric emitted |
|---|---|---|---|
| Unused imports / vars | **ruff** | `pip install ruff` | `ruff_unused` |
| Dead code (funcs, classes, attrs) | **vulture** | `pip install vulture` | `vulture_dead_code` |
| Cyclomatic complexity | **radon** | `pip install radon` | `radon_complex_blocks` |
| Duplication (optional) | **jscpd** | `npm i -g jscpd` | `jscpd_duplication_pct` |
| Runtime hotspots (optional) | **viztracer**, **coverage.py** | `pip install viztracer coverage` | *(advisory, not ratcheted)* |

One-liner for the core three:

```bash
pip install ruff vulture radon
```

## TypeScript / JavaScript

| Debt dimension | Tool | Install | Metric emitted |
|---|---|---|---|
| Unused files / exports / deps | **knip** | `npm i -g knip` | `knip_unused_files`, `knip_unused_exports` |
| Duplication | **jscpd** | `npm i -g jscpd` | `jscpd_duplication_pct` |
| All of the above (preferred) | **fallow** | see [fallow-rs/fallow](https://github.com/fallow-rs/fallow) | `fallow_dead_code`, `fallow_duplication_pct` |

If `fallow` is on `PATH`, the scanner uses it directly for TS/JS and supersedes
knip+jscpd for those metrics — one tool that blends static analysis with runtime
coverage, which is the model this whole ratchet is patterned on.

## Thresholds

Absolute caps live in `governance/debt_config.yaml` (optional). Defaults:

```yaml
thresholds:
  duplication_pct_max: 5.0     # jscpd/fallow duplication ceiling
  complexity_cc_max: 10        # radon counts blocks worse than this
```

The ratchet fails when a metric **grows past the baseline** OR sits **above an
absolute cap** — so a project can't quietly stay at a bad-but-flat level.

## Workflow

1. **Establish the baseline** once tools are installed: `make debt-scan`, commit
   `governance/DEBT_BASELINE.json`.
2. **Every PR** runs `make debt-check` (locally + CI `tech-debt` job). New debt
   fails the PR.
3. **When you reduce debt**, run `make debt-scan` again to lock the lower number
   into the baseline. A baseline that moves *up* must be its own PR explaining why
   — the same discipline as reopening a finding.
4. **The Steward surfaces hotspots**: `make session-start` lists the biggest
   current metrics as candidates for the next remediation finding. Promote one
   into `governance/findings/F-NNN.yaml` and remediate it one PR at a time.
