#!/usr/bin/env python3
"""Verification script for F-078: battleground dept win prob marked illustrative."""

from __future__ import annotations

import json
from pathlib import Path

from _governance_check import REPO_ROOT, gate

BG = (
    REPO_ROOT
    / "data"
    / "processed"
    / "module_c"
    / "run_all"
    / "battleground_department_probability.parquet"
)
HEATMAP = (
    REPO_ROOT
    / "data"
    / "processed"
    / "module_c"
    / "run_all"
    / "battleground_probability_heatmap.geojson"
)
HEATMAP_PY = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)
EDA_GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def _heatmap_py_gaps(src: str) -> list[str]:
    if "illustrative" not in src.lower():
        return ["heatmap.py missing illustrative mapping disclosure"]
    return []


def _battleground_parquet_gaps() -> list[str]:
    if not BG.is_file():
        return []
    import pandas as pd

    gaps: list[str] = []
    df = pd.read_parquet(BG)
    if (
        "model_version" in df.columns
        and "illustrative" not in str(df["model_version"].iloc[0]).lower()
    ):
        gaps.append("battleground model_version not marked illustrative")
    spread = float(df["win_probability_a"].max() - df["win_probability_a"].min())
    if spread > 0.15:
        gaps.append(f"dept win prob spread {spread:.3f} > 0.15 without structural model")
    return gaps


def _geojson_gaps() -> list[str]:
    if not HEATMAP.is_file():
        return []
    geo = json.loads(HEATMAP.read_text(encoding="utf-8"))
    props = geo["features"][0]["properties"] if geo.get("features") else {}
    if props.get("mapping_method") != "illustrative_national_jitter":
        return ["heatmap geojson missing mapping_method=illustrative_national_jitter"]
    return []


def _eda_s4_gaps(eda: str) -> list[str]:
    if (
        "win_probability_a" in eda
        and "priority_score" in eda
        and "win_probability_a" in eda.split("priority_score")[1][:400]
    ):
        return ["S4 priority_score still multiplies win_probability_a"]
    return []


def main() -> int:
    gaps = [
        *_heatmap_py_gaps(HEATMAP_PY.read_text(encoding="utf-8")),
        *_battleground_parquet_gaps(),
        *_geojson_gaps(),
        *_eda_s4_gaps(EDA_GENERATOR.read_text(encoding="utf-8")),
    ]
    ok = not gaps
    detail = (
        "; ".join(gaps) if gaps else "battleground mapping disclosed; S4 decoupled from win prob"
    )
    return gate("F-078", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
