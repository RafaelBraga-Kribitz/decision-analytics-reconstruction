#!/usr/bin/env python3
"""Verification script for F-074: entity covariates carry within-department variation.

Chart audit A9/A10 documented department-constant TV/radio penetration producing
PCA lattice artifacts. This script gates the canonical population_master artifact:
populous departments must show entity-level dispersion on media penetration fields.
"""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

POPULATION_MASTER = REPO_ROOT / "data" / "processed" / "population_master_clean.parquet"

MIN_DEPT_STD = 0.005
MIN_DEPT_COUNT = 500
MEDIA_COLUMNS = ("media_penetration_tv", "media_penetration_radio")


def main() -> int:
    gaps: list[str] = []

    if not POPULATION_MASTER.is_file():
        return gate(
            "F-074",
            Path(__file__).name,
            False,
            "missing data/processed/population_master_clean.parquet",
        )

    import pandas as pd

    df = pd.read_parquet(POPULATION_MASTER, columns=["department", *MEDIA_COLUMNS])
    for col in MEDIA_COLUMNS:
        if col not in df.columns:
            gaps.append(f"missing column {col}")
            continue
        stats = df.groupby("department")[col].agg(std="std", count="count")
        for dept, row in stats.iterrows():
            if int(row["count"]) >= MIN_DEPT_COUNT and float(row["std"]) < MIN_DEPT_STD:
                gaps.append(f"{col} department {dept} std={row['std']:.5f} < {MIN_DEPT_STD}")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "media penetrations show within-dept dispersion"
    return gate("F-074", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
