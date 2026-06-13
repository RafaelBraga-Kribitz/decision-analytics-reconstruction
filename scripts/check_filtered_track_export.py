#!/usr/bin/env python3
"""Verification script for F-077: filtered walk-forward track exported alongside anchored."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

TRACKING = REPO_ROOT / "data" / "processed" / "module_c" / "run_all" / "tracking"
FILTERED = TRACKING / "daily_posterior_forecast_filtered.parquet"
ANCHORED = TRACKING / "daily_posterior_forecast.parquet"
POLLS = TRACKING / "polls_clean_tracking_wave.parquet"


def main() -> int:
    gaps: list[str] = []
    for path in (FILTERED, ANCHORED, POLLS):
        if not path.is_file():
            gaps.append(f"missing {path.relative_to(REPO_ROOT)}")

    if not gaps:
        import pandas as pd

        fc_f = pd.read_parquet(FILTERED)
        fc_a = pd.read_parquet(ANCHORED)
        if len(fc_f) != len(fc_a):
            gaps.append(f"filtered/anchored row count mismatch: {len(fc_f)} vs {len(fc_a)}")
        if "posterior_mean_preference_margin_pp" not in fc_f.columns:
            gaps.append("filtered track missing posterior_mean_preference_margin_pp")

        eda = (REPO_ROOT / "reports" / "eda" / "generate_eda.py").read_text(encoding="utf-8")
        if "forecast_filtered" not in eda:
            gaps.append("generate_eda.py does not load forecast_filtered for C1")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "filtered track artifact present for C1 dual-line"
    return gate("F-077", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
