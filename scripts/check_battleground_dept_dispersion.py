#!/usr/bin/env python3
"""Verification script for F-081: battleground v0.5 anti-clustering + estimated sigma.

The v0.4 mapping collapsed large-swing departments to identical win probabilities
(~90.4–90.5%) because swing scaled both mean and dispersion. v0.5 decouples
national uncertainty from swing and uses reference-data σ_idio estimates.

Gates:
  1. Primary parquet (when present) uses model_version containing v0.5.
  2. Manifest mapping is v0.5_decoupled_sigma; sigma provenance not purely illustrative
     when reference data is committed.
  3. Anti-clustering: among depts with 0.8 ≤ win_probability_a < 0.985, at most 4 share
     the same 0.1% rounded value (targets v0.4 ~90% plateaus; ceiling saturation excluded).
  4. Geographic spread: std(win_probability_a) >= 0.12 on poll_implied table.
  5. F-080 regression: >=5 departments with HDI width >= 0.05; poll_implied estimand.
  6. heatmap.py exports c_battleground_v0.5 with decoupled sigma helpers.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
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
MANIFEST = (
    REPO_ROOT
    / "data"
    / "processed"
    / "module_c"
    / "run_all"
    / "battleground"
    / "battleground_department_probability_manifest.json"
)
HEATMAP = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)
REF_SIGMA = REPO_ROOT / "data" / "reference" / "battleground" / "battleground_sigma_idio.yaml"


def _parquet_gaps() -> list[str]:
    gaps: list[str] = []
    if not PRIMARY.exists():
        return gaps
    try:
        import pandas as pd
    except ImportError:
        return ["pandas required to validate battleground parquet"]
    df = pd.read_parquet(PRIMARY)
    if "model_version" not in df.columns:
        gaps.append("primary parquet missing model_version")
    elif not any("v0.5" in str(v) for v in df["model_version"].astype(str).unique()):
        gaps.append("primary parquet model_version not v0.5")
    if "estimand" in df.columns and not (df["estimand"] == "poll_implied").all():
        gaps.append("primary parquet estimand is not poll_implied")
    if {"hdi_low", "hdi_high", "win_probability_a"} <= set(df.columns):
        widths = df["hdi_high"] - df["hdi_low"]
        if int((widths >= 0.05).sum()) < 5:
            gaps.append(
                f"expected ≥5 departments with HDI width ≥0.05, got {(widths >= 0.05).sum()}"
            )
        high = df[(df["win_probability_a"] >= 0.8) & (df["win_probability_a"] < 0.985)]
        if not high.empty:
            rounded = [round(float(v) * 1000) / 10 for v in high["win_probability_a"]]
            counts = Counter(rounded)
            max_same = max(counts.values()) if counts else 0
            if max_same > 4:
                gaps.append(
                    f"anti-clustering failed: {max_same} depts share same 0.1% rounded "
                    f"win prob in [80%, 98.5%)"
                )
        if float(df["win_probability_a"].std()) < 0.12:
            gaps.append(
                f"expected std(win_probability_a) ≥ 0.12, got {df['win_probability_a'].std():.3f}"
            )
    return gaps


def _manifest_gaps() -> list[str]:
    gaps: list[str] = []
    if not MANIFEST.is_file():
        return gaps
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("mapping") != "v0.5_decoupled_sigma":
        gaps.append("manifest missing v0.5_decoupled_sigma mapping label")
    prov = str(manifest.get("sigma_idio_provenance", ""))
    if REF_SIGMA.is_file() and prov == "illustrative_assumption_not_estimated":
        gaps.append("reference sigma yaml present but manifest still illustrative")
    if "sigma_idio_by_department" not in manifest:
        gaps.append("manifest missing per-department sigma_idio_by_department")
    return gaps


def _heatmap_gaps() -> list[str]:
    gaps: list[str] = []
    src = HEATMAP.read_text(encoding="utf-8")
    if 'MODEL_VERSION = "c_battleground_v0.5"' not in src:
        gaps.append("heatmap.py not bumped to c_battleground_v0.5")
    if "_sigma_dept_v05" not in src:
        gaps.append("heatmap.py missing v0.5 decoupled sigma helper")
    if "load_sigma_yaml" not in src:
        gaps.append("heatmap.py missing per-dept sigma yaml loader")
    return gaps


def main() -> int:
    gaps = _parquet_gaps() + _manifest_gaps() + _heatmap_gaps()
    ok = not gaps
    detail = "battleground v0.5 anti-clustering intact" if ok else "; ".join(gaps)
    return gate("F-081", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
