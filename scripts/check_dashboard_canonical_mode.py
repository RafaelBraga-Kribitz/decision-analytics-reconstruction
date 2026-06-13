#!/usr/bin/env python3
"""Verification script for F-071: Module A dashboard uses canonical bundle by default."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

DASH = REPO_ROOT / "module_a_population_segmentation" / "app" / "streamlit_dashboard.py"


def main() -> int:
    gaps: list[str] = []
    src = DASH.read_text(encoding="utf-8")
    if "_load_canonical_bundle" not in src:
        gaps.append("missing _load_canonical_bundle")
    if (
        "PropensityModel(" in src
        and "fit_predict(feat, anc)" in src
        and "_fit_propensity_for_shap" not in src
    ):
        gaps.append("dashboard still refits propensity on canonical load")
    if "Live rebuild (non-canonical)" not in src:
        gaps.append("missing live rebuild opt-in checkbox")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "dashboard defaults to canonical parquet bundle"
    return gate("F-071", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
