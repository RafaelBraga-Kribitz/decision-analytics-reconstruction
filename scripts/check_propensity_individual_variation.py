#!/usr/bin/env python3
"""Verification script for F-052: participation propensity carries individual variation.

Chart audit A5/A11 documented near-constant propensity within departments and
degenerate segment violins. This script gates the canonical population_master
artifact: each populous department and behavioral segment must show enough
within-group dispersion that targeting math is not operating on ~18 dept atoms.
"""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

POPULATION_MASTER = REPO_ROOT / "data" / "processed" / "population_master_clean.parquet"

MIN_DEPT_STD = 0.01
MIN_SEGMENT_STD = 0.04
MIN_DEPT_COUNT = 500
MIN_SEGMENT_COUNT = 1000
MAX_DOMINANT_ROUNDED2_SHARE = 0.50


def main() -> int:
    gaps: list[str] = []

    if not POPULATION_MASTER.is_file():
        return gate(
            "F-052",
            Path(__file__).name,
            False,
            "missing data/processed/population_master_clean.parquet",
        )

    import pandas as pd

    df = pd.read_parquet(
        POPULATION_MASTER,
        columns=["department", "segment_label", "participation_propensity"],
    )
    prop = df["participation_propensity"].astype(float)

    dept_stats = df.assign(_prop=prop).groupby("department")["_prop"].agg(std="std", count="count")
    for dept, row in dept_stats.iterrows():
        if int(row["count"]) >= MIN_DEPT_COUNT and float(row["std"]) < MIN_DEPT_STD:
            gaps.append(f"department {dept} propensity std={row['std']:.4f} < {MIN_DEPT_STD}")

    seg_stats = (
        df.assign(_prop=prop).groupby("segment_label")["_prop"].agg(std="std", count="count")
    )
    for label, row in seg_stats.iterrows():
        if int(row["count"]) < MIN_SEGMENT_COUNT:
            continue
        if float(row["std"]) < MIN_SEGMENT_STD:
            gaps.append(f"segment {label} propensity std={row['std']:.4f} < {MIN_SEGMENT_STD}")
        sub = prop[df["segment_label"] == label]
        dominant = float(sub.round(2).value_counts(normalize=True).iloc[0])
        if dominant > MAX_DOMINANT_ROUNDED2_SHARE:
            gaps.append(
                f"segment {label} dominant rounded-2dp share={dominant:.3f} > "
                f"{MAX_DOMINANT_ROUNDED2_SHARE}"
            )

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "propensity shows dept/segment-level dispersion"
    return gate("F-052", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
