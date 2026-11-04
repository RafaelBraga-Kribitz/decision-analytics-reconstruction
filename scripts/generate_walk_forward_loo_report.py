#!/usr/bin/env python3
"""Regenerate the committed leave-one-wave-out walk-forward report (issue #97).

Runs Module C walk-forward validation on the real poll fixture
(``polls_raw_fixture.csv``), then writes:

- ``reports/module_c/walk_forward_loo_metrics.json``
- ``reports/module_c/walk_forward_loo_report.md``

Default (``MC_FAST`` unset, no flag) keeps the CI-friendly fast path. Pass
``--full`` for a publication-grade full-NUTS run: the flag removes ``MC_FAST``
from the environment. Never set ``MC_FAST=0``: the sampler tests truthiness, so
any non-empty value (including ``"0"``) selects the 50-draw fast path.

Per-fold MCMC diagnostics (R-hat, ESS, divergences versus ``DIAGNOSTIC_GATES``)
are recorded for every refit and written to
``reports/module_c/walk_forward_loo_diagnostics.json``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml
from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.models.tracking import hierarchical as _hier
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.validation import walk_forward as _wf
from module_c_forecasting_scenarios.validation.walk_forward import (
    walk_forward_tracking_validation,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    REPO_ROOT / "module_c_forecasting_scenarios" / "tests" / "fixtures" / "polls_raw_fixture.csv"
)
METRICS_OUT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_metrics.json"
DIAG_OUT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_diagnostics.json"
REPORT_OUT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_report.md"


def _is_fast() -> bool:
    """Mirror the sampler: any non-empty ``MC_FAST`` selects the fast path."""
    return bool(os.environ.get("MC_FAST"))


def _render_report(
    payload: dict[str, object],
    per_holdout_rows: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
) -> str:
    m = payload
    n_waves = int(m["n_total_polls"])
    n_holdouts = int(m["n_holdouts"])
    min_train = int(m["min_train_size"])
    fast = _is_fast()
    sk = _hier._sampler_kwargs()  # pyright: ignore[reportPrivateUsage]
    sampler_desc = (
        f"{sk['chains']} chains x {sk['draws']} draws, {sk['tune']} tune, "
        f"target_accept={sk['target_accept']}, seed={sk['random_seed']}"
    )
    if not fast:
        sampler_desc += f", max_treedepth={sk['nuts_sampler_kwargs']['max_treedepth']}"
    mode_desc = "the ``MC_FAST=1`` fast path" if fast else "full NUTS, ``MC_FAST`` unset"

    def _cov(level: str) -> str:
        k = int(m[f"coverage_{level}pct_k"])
        lo, hi = float(m[f"coverage_{level}pct_ci_low"]), float(m[f"coverage_{level}pct_ci_high"])
        return f"{k}/{n_holdouts} = {k / n_holdouts:.0%} [{lo:.2f}, {hi:.2f}]"

    fixture_rel = FIXTURE.relative_to(REPO_ROOT).as_posix()
    lines = [
        "# Module C — Leave-One-Wave-Out Walk-Forward Report",
        "",
        "First **out-of-sample** predictive score on the real Paraguay 2018 poll fixture.",
        "Each row holds out one tracking wave, refits the hierarchical model **without** the",
        "verified outcome anchor (``m_star_pp=None``; see F-069), and scores the held-out poll",
        "against its posterior-predictive distribution.",
        "",
        "## Caveats (read before quoting these numbers)",
        "",
        (
            f"- **Small n:** only **{n_waves}** tracking waves → **{n_holdouts}** "
            f"holdouts at ``min_train_size={min_train}``."
        ),
        (
            "- **Wide intervals expected:** sparse polls + house effects → interval "
            "coverage is a structural diagnostic, not evidence of calibration."
        ),
        (
            "- **No power:** coverage is quoted as k/n with its exact binomial 95% CI; "
            f"with n={n_holdouts} that CI spans most of [0, 1], so this check cannot "
            "distinguish a calibrated model from a badly miscalibrated one."
        ),
        (
            f"- **Regeneration mode:** this committed artifact was produced with {mode_desc} "
            f"({sampler_desc})."
            + (" Re-run with ``--full`` for publication-grade MCMC." if fast else "")
        ),
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value | Interpretation |",
        "|---|---:|---|",
        f"| Brier score (sign task) | {m['brier_score']:.4f} | P(margin>0) vs observed sign |",
        f"| Log loss | {m['log_loss']:.4f} | Same task, log score |",
        (
            f"| 80% interval coverage | {_cov('80')} | "
            "Holdouts inside 80% HDI [exact binomial 95% CI] |"
        ),
        (
            f"| 95% interval coverage | {_cov('95')} | "
            "Holdouts inside 95% HDI [exact binomial 95% CI] |"
        ),
        "",
        "## Per-holdout detail",
        "",
        (
            "| Holdout wave | Date | Observed margin (pp) | Predictive mean (pp) | "
            "95% HDI (pp) | In 95% HDI |"
        ),
        "|---|---|---:|---:|---|---|",
    ]
    for row in per_holdout_rows:
        lines.append(
            f"| `{row['poll_wave_id']}` | {row['publication_date']} | "
            f"{row['observed_margin_pp']:.2f} | {row['predicted_posterior_mean_pp']:.2f} | "
            f"[{row['hdi95_low_pp']:.1f}, {row['hdi95_high_pp']:.1f}] | "
            f"{'yes' if row['in_hdi95'] else 'no'} |"
        )
    gates = _hier.DIAGNOSTIC_GATES
    lines.extend(
        [
            "",
            "## MCMC diagnostics per fold",
            "",
            (
                f"Gates: R-hat <= {gates['rhat_max']}, ESS bulk >= {gates['ess_bulk_min']:.0f}, "
                f"ESS tail >= {gates['ess_tail_min']:.0f}, divergences <= "
                f"{gates['divergences']:.0f} (``DIAGNOSTIC_GATES`` in the tracking model)."
            ),
            "",
            "| Fold (train size) | Holdout wave | R-hat max | ESS bulk min | ESS tail min "
            "| Divergences | Treedepth hits | Gates |",
            "|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for d in diagnostics:
        v = d["values"]  # type: ignore[index]
        ok = all(d["passed"].values())  # type: ignore[union-attr]
        lines.append(
            f"| {d['train_size']} | `{d['holdout_wave']}` | {v['rhat_max']:.3f} | "
            f"{v['ess_bulk_min']:.0f} | {v['ess_tail_min']:.0f} | {v['divergences']} | "
            f"{d['max_treedepth_hits']} | {'pass' if ok else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## How to regenerate",
            "",
            "```bash",
            "# Publication-grade full NUTS (do not set MC_FAST, not even to 0):",
            "poetry run python scripts/generate_walk_forward_loo_report.py --full",
            "# CI-friendly fast path:",
            "poetry run python scripts/generate_walk_forward_loo_report.py",
            "```",
            "",
            f"*Generated on {date.today().isoformat()} from ``{fixture_rel}``.*",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    if "--full" in sys.argv[1:]:
        os.environ.pop("MC_FAST", None)
    else:
        os.environ.setdefault("MC_FAST", "1")

    # Record diagnostics of every refit without touching the model: wrap the
    # fit function that the walk-forward routine calls.
    diagnostics: list[dict[str, object]] = []
    orig_fit = _wf.fit_tracking_hierarchical

    def _recording_fit(train, *args, **kwargs):  # type: ignore[no-untyped-def]
        idata = orig_fit(train, *args, **kwargs)
        d = _hier.diagnostics_summary(idata)
        d["train_size"] = len(train)
        diagnostics.append(d)
        return idata

    _wf.fit_tracking_hierarchical = _recording_fit  # type: ignore[assignment]
    if not FIXTURE.is_file():
        print(f"[FAIL] missing fixture: {FIXTURE}", file=sys.stderr)
        return 1

    cal_path = module_config_dir() / "calibration.yaml"
    with open(cal_path, encoding="utf-8") as f:
        cal = yaml.safe_load(f)
    series = str(cal["series"]).strip().upper()
    outcome = date.fromisoformat(str(cal.get("outcome_event_date", "2018-04-22")))
    min_train = 2

    raw = load_raw_polls_csv(FIXTURE)
    tracking, _ = clean_raw_polls(raw, series)
    result = walk_forward_tracking_validation(
        tracking,
        outcome_event_date=outcome,
        calibration_series=series,
        min_train_size=min_train,
    )

    payload: dict[str, object] = {
        "fixture": FIXTURE.relative_to(REPO_ROOT).as_posix(),
        "calibration_series": series,
        "outcome_event_date": outcome.isoformat(),
        "min_train_size": min_train,
        "n_total_polls": len(tracking),
        "mc_fast": _is_fast(),
        "sampler_path": "mc_fast" if _is_fast() else "full_nuts",
        **result.metrics,
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    per_rows = result.per_holdout.to_dict(orient="records")
    for d, row in zip(diagnostics, per_rows, strict=True):
        d["holdout_wave"] = row["poll_wave_id"]
    DIAG_OUT.write_text(json.dumps(diagnostics, indent=2, default=str) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(_render_report(payload, per_rows, diagnostics), encoding="utf-8")

    print(f"[PASS] wrote {METRICS_OUT.relative_to(REPO_ROOT)}")
    print(f"[PASS] wrote {DIAG_OUT.relative_to(REPO_ROOT)}")
    print(f"[PASS] wrote {REPORT_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
