#!/usr/bin/env python3
"""Verification script for F-055: allocation contacts respect row caps and util bounds."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

ALLOC = REPO_ROOT / "data" / "processed" / "module_b" / "allocation_baseline.parquet"


def main() -> int:
    gaps: list[str] = []
    if not ALLOC.is_file():
        return gate("F-055", Path(__file__).name, False, f"missing {ALLOC.relative_to(REPO_ROOT)}")

    import pandas as pd

    df = pd.read_parquet(ALLOC)
    over = df[df["expected_contacts"] > df["reach_cap_population_proxy"] * 1.001]
    if len(over):
        gaps.append(f"{len(over)} rows exceed reach_cap_population_proxy")
    bad_util = df[(df["reach_utilization"] < -1e-9) | (df["reach_utilization"] > 1.0 + 1e-6)]
    if len(bad_util):
        gaps.append(
            f"reach_utilization outside [0,1]: max={float(df['reach_utilization'].max()):.4f}"
        )

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "allocation rows respect contact caps and util bounds"
    return gate("F-055", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
