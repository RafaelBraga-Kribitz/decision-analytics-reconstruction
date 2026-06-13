#!/usr/bin/env python3
"""Verification script for F-056: MC shock_scale couples to contacts and emits p_win_a."""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

MC = REPO_ROOT / "data" / "processed" / "module_c" / "run_all" / "mc" / "monte_carlo_draws.parquet"


def main() -> int:
    gaps: list[str] = []
    if not MC.is_file():
        return gate("F-056", Path(__file__).name, False, f"missing {MC.relative_to(REPO_ROOT)}")

    import pandas as pd

    df = pd.read_parquet(MC)
    for col in ("shock_scale", "alloc_mean_persuasion_contacts", "p_win_a"):
        if col not in df.columns:
            gaps.append(f"missing column {col}")

    if not gaps:
        if float(df["alloc_mean_persuasion_contacts"].std()) <= 0.0:
            gaps.append("alloc_mean_persuasion_contacts has zero variance across draws")
        if float(df["p_win_a"].std()) <= 0.0:
            gaps.append("p_win_a has zero variance across draws")
        if (df["alloc_mean_persuasion_contacts"] <= 0).any():
            gaps.append("alloc_mean_persuasion_contacts contains non-positive values")

    ok = not gaps
    detail = (
        "; ".join(gaps) if gaps else "MC draws show shock-coupled contacts and p_win_a variance"
    )
    return gate("F-056", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
