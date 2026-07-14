#!/usr/bin/env python3
"""Regenerate the committed leave-one-wave-out walk-forward report (issue #97).

Runs Module C walk-forward validation on the real poll fixture
(``polls_raw_fixture.csv``), then writes:

- ``reports/module_c/walk_forward_loo_metrics.json``
- ``reports/module_c/walk_forward_loo_report.md``

Uses ``MC_FAST=1`` when unset so regeneration stays CI-friendly; set
``MC_FAST=0`` locally for a full MCMC run before publishing headline numbers.
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
from module_c_forecasting_scenarios.paths import module_config_dir
from module_c_forecasting_scenarios.validation.walk_forward import (
    walk_forward_tracking_validation,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "tests"
    / "fixtures"
    / "polls_raw_fixture.csv"
)
METRICS_OUT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_metrics.json"
REPORT_OUT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_report.md"


def _render_report(payload: dict[str, object], per_holdout_rows: list[dict[str, object]]) -> str:
    m = payload
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
        f"- **Small n:** only **{int(m['n_total_polls'])}** tracking waves → **{int(m['n_holdouts'])}** holdouts at ``min_train_size={int(m['min_train_size'])}``.",
        "- **Wide intervals expected:** sparse polls + house effects → interval coverage is a structural diagnostic, not proof of calibration.",
        "- **Regeneration mode:** this committed artifact was produced with "
        f"``MC_FAST={'1' if os.environ.get('MC_FAST', '1') == '1' else '0'}``; "
        "re-run without ``MC_FAST`` for publication-grade MCMC.",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value | Interpretation |",
        "|---|---:|---|",
        f"| Brier score (sign task) | {m['brier_score']:.4f} | P(margin>0) vs observed sign |",
        f"| Log loss | {m['log_loss']:.4f} | Same task, log score |",
        f"| 80% interval coverage | {100 * float(m['coverage_80pct']):.1f}% | Share of holdouts inside 80% HDI |",
        f"| 95% interval coverage | {100 * float(m['coverage_95pct']):.1f}% | Share of holdouts inside 95% HDI |",
        "",
        "## Per-holdout detail",
        "",
        "| Holdout wave | Date | Observed margin (pp) | Predictive mean (pp) | 95% HDI (pp) | In 95% HDI |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in per_holdout_rows:
        lines.append(
            f"| `{row['poll_wave_id']}` | {row['publication_date']} | "
            f"{row['observed_margin_pp']:.2f} | {row['predicted_posterior_mean_pp']:.2f} | "
            f"[{row['hdi95_low_pp']:.1f}, {row['hdi95_high_pp']:.1f}] | "
            f"{'yes' if row['in_hdi95'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## How to regenerate",
            "",
            "```bash",
            "MC_FAST=1 poetry run python scripts/generate_walk_forward_loo_report.py",
            "```",
            "",
            f"*Generated on {date.today().isoformat()} from ``{FIXTURE.relative_to(REPO_ROOT).as_posix()}``.*",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    os.environ.setdefault("MC_FAST", "1")
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
        "mc_fast": os.environ.get("MC_FAST", "1") == "1",
        **result.metrics,
    }

    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    per_rows = result.per_holdout.to_dict(orient="records")
    REPORT_OUT.write_text(_render_report(payload, per_rows), encoding="utf-8")

    print(f"[PASS] wrote {METRICS_OUT.relative_to(REPO_ROOT)}")
    print(f"[PASS] wrote {REPORT_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
