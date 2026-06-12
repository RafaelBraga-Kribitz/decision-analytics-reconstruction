#!/usr/bin/env python3
"""Verification script for F-051: segment label semantics on canonical chart data.

F-039 gates profile-derived assignment on a fresh pipeline fit. Chart audit batch 1
showed the committed population_master_clean.parquet still carries inverted urbanicity
semantics (e.g. rural_committed 95% urban). This script asserts semantic invariants
on the artifact generate_eda.py and the published report actually consume.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from _governance_check import REPO_ROOT, gate

POPULATION_MASTER = REPO_ROOT / "data" / "processed" / "population_master_clean.parquet"
INTERPRETATION_TEST = "module_a_population_segmentation/tests/test_segment_label_interpretation.py"

# Minimum rural share for a segment named rural_committed on canonical artifacts.
MIN_RURAL_COMMITTED_RURAL_SHARE = 0.20
# committed_opposition cannot be a purely metro cluster on canonical artifacts.
MAX_COMMITTED_OPPOSITION_URBAN_SHARE = 0.99


def _artifact_semantics() -> list[str]:
    gaps: list[str] = []
    if not POPULATION_MASTER.is_file():
        return ["missing data/processed/population_master_clean.parquet"]

    import pandas as pd

    df = pd.read_parquet(POPULATION_MASTER, columns=["segment_label", "rural_flag", "metro_flag"])
    if "rural_flag" not in df.columns:
        return ["population_master_clean.parquet missing rural_flag column"]

    rural = df["rural_flag"].astype(bool)

    def rural_share(label: str) -> float:
        mask = df["segment_label"] == label
        if not mask.any():
            return float("nan")
        return float(rural[mask].mean())

    rc = rural_share("rural_committed")
    uhv = rural_share("urban_high_volatility")
    if rc < MIN_RURAL_COMMITTED_RURAL_SHARE:
        gaps.append(f"rural_committed rural_share={rc:.3f} < {MIN_RURAL_COMMITTED_RURAL_SHARE}")
    if rc <= uhv:
        gaps.append(
            f"rural_committed rural_share={rc:.3f} must exceed "
            f"urban_high_volatility rural_share={uhv:.3f}"
        )

    co_urban = 1.0 - rural_share("committed_opposition")
    if co_urban > MAX_COMMITTED_OPPOSITION_URBAN_SHARE:
        gaps.append(
            f"committed_opposition urban_share={co_urban:.3f} > "
            f"{MAX_COMMITTED_OPPOSITION_URBAN_SHARE} (metro-only cluster)"
        )

    return gaps


def _interpretation_suite() -> tuple[bool, str]:
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "pytest",
            INTERPRETATION_TEST,
            "-q",
            "--no-header",
            "-p",
            "no:warnings",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode == 0:
        return True, "interpretation gate passed on fresh 6k fit"
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
    return False, "interpretation gate failed: " + " | ".join(tail)


def main() -> int:
    gaps = _artifact_semantics()
    ok_interp, interp_msg = _interpretation_suite()
    if not ok_interp:
        gaps.append(interp_msg)

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "canonical parquet + interpretation gates hold"
    return gate("F-051", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
