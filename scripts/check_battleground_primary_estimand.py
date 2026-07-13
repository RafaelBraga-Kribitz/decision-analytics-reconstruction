#!/usr/bin/env python3
"""Verification script for F-080: battleground primary table is poll-implied v0.4.

The headline department win-probability chart must not consume the
outcome-anchored retrodiction table — that estimand collapses to realized
2018 margins and saturates at ~100% for Abdo landslides (F-080).

Gates:
  1. Primary ``battleground_department_probability.parquet`` (when present)
     carries ``estimand=poll_implied`` and ``model_version`` containing v0.4.
  2. At least five departments have HDI width >= 0.05 (percentile propagation).
  3. ``post_mortem.qmd`` primary chart title says poll-implied, not bare
     "outcome probability".
  4. ``heatmap.py`` exports ``c_battleground_v0.4`` with ``poll_implied`` estimand.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

PRIMARY = (
    REPO_ROOT
    / "data"
    / "processed"
    / "module_c"
    / "run_all"
    / "battleground"
    / "battleground_department_probability.parquet"
)
QMD = REPO_ROOT / "module_c_forecasting_scenarios" / "portfolio" / "quarto" / "post_mortem.qmd"
HEATMAP = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)


def _parquet_gaps() -> list[str]:
    gaps: list[str] = []
    if not PRIMARY.exists():
        return gaps  # pipeline not run locally — source-level gates still apply
    try:
        import pandas as pd
    except ImportError:
        return ["pandas required to validate primary battleground parquet"]
    df = pd.read_parquet(PRIMARY)
    if "estimand" not in df.columns:
        gaps.append("primary parquet missing estimand column")
        return gaps
    if not (df["estimand"] == "poll_implied").all():
        gaps.append("primary parquet estimand is not poll_implied")
    if "model_version" in df.columns:
        versions = df["model_version"].astype(str).unique()
        if not any("v0.4" in v for v in versions):
            gaps.append(f"primary parquet model_version not v0.4: {versions.tolist()}")
    if {"hdi_low", "hdi_high"} <= set(df.columns):
        widths = df["hdi_high"] - df["hdi_low"]
        if int((widths >= 0.05).sum()) < 5:
            gaps.append(
                f"expected ≥5 departments with HDI width ≥0.05, got {(widths >= 0.05).sum()}"
            )
    return gaps


def _qmd_gaps() -> list[str]:
    gaps: list[str] = []
    text = QMD.read_text(encoding="utf-8")
    m = re.search(
        r"## Department-Level Win Probability.*?fig-battleground-choropleth", text, re.S
    )
    block = m.group(0) if m else ""
    if not block:
        return ["post_mortem.qmd battleground section not found"]
    if "poll-implied" not in block.lower() and "poll_implied" not in block.lower():
        gaps.append("qmd primary chart lost poll-implied labeling")
    if re.search(r"outcome probability with HDI \(Series A, retrodiction\)", block, re.I):
        gaps.append("qmd primary chart still titled as retrodiction outcome probability")
    if "error_x" not in block:
        gaps.append("fig-battleground no longer draws the HDI interval (error_x)")
    if "TSJE" not in block:
        gaps.append("qmd battleground section lost TSJE winner overlay")
    return gaps


def _heatmap_gaps() -> list[str]:
    gaps: list[str] = []
    src = HEATMAP.read_text(encoding="utf-8")
    if 'MODEL_VERSION = "c_battleground_v0.4"' not in src:
        gaps.append("heatmap.py not bumped to c_battleground_v0.4")
    if "_ESTIMAND_POLL_IMPLIED" not in src:
        gaps.append("heatmap.py lost poll_implied estimand constant")
    if "_win_prob_hdi" not in src:
        gaps.append("heatmap.py lost percentile HDI propagation helper")
    return gaps


def main() -> int:
    gaps = _parquet_gaps() + _qmd_gaps() + _heatmap_gaps()
    ok = not gaps
    detail = "primary poll_implied battleground intact" if ok else "; ".join(gaps)
    return gate("F-080", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
