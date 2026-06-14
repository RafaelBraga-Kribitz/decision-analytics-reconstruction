#!/usr/bin/env python3
"""Verification script for F-070: department heatmap uses real TSJE data, not a fake formula.

AUD fabricated-dept-model: heatmap.py v0.1 used ``z = 0.12 * (last − 3.8) + noise + 0.001 * i``
to generate per-department win probabilities — a formula with no empirical basis, calibrated
to neither 2018 TSJE returns nor historical swing patterns. It produced plausible-looking but
fabricated departmental win probabilities.

Closure invariant (static source checks):
  geo/heatmap.py — references tsje_2018_department_results.csv and the
        _swing_factors() function; does NOT contain the fabricated 0.12*(last-3.8) formula.

Closure invariant (runtime reconciliation):
  geo/tsje_2018_department_results.csv (shipped as package data) — candidate totals
        reconcile to the verified nationals (1,206,067 / 1,110,464) within 0.3% AND all five
        GANAR-winning departments (Alto Parana, Central, Concepcion, Cordillera, Exterior)
        have positive alegre − abdo votes.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

HEATMAP = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)
TSJE_CSV = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "tsje_2018_department_results.csv"
)

_NATIONAL_ABDO = 1_206_067
_NATIONAL_GANAR = 1_110_464
_GANAR_WINNERS = frozenset({"Alto Parana", "Central", "Concepcion", "Cordillera", "Exterior"})

# The fabricated formula that must NOT appear in the new heatmap.
_BANNED = "0.12 * (last - 3.8)"


def _static_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if _BANNED in src:
        gaps.append(f"heatmap.py still contains the fabricated formula: {_BANNED!r}")
    if "tsje_2018_department_results.csv" not in src:
        gaps.append("heatmap.py does not reference the TSJE CSV")
    if "_swing_factors" not in src:
        gaps.append("heatmap.py does not define _swing_factors()")
    return gaps


def _runtime_gaps() -> list[str]:
    if not TSJE_CSV.exists():
        return ["geo/tsje_2018_department_results.csv (package data) is absent"]
    gaps: list[str] = []
    rows = list(csv.DictReader(TSJE_CSV.open()))
    try:
        sum_abdo = sum(int(r["abdo_anr_votes"]) for r in rows)
        sum_ganar = sum(int(r["alegre_ganar_votes"]) for r in rows)
    except (KeyError, ValueError) as exc:
        return [f"CSV schema error: {exc}"]
    if abs(sum_abdo - _NATIONAL_ABDO) / _NATIONAL_ABDO >= 0.003:
        gaps.append(
            f"Abdo total {sum_abdo:,} deviates from verified {_NATIONAL_ABDO:,} by "
            f"{(sum_abdo - _NATIONAL_ABDO) / _NATIONAL_ABDO * 100:+.2f}%"
        )
    if abs(sum_ganar - _NATIONAL_GANAR) / _NATIONAL_GANAR >= 0.003:
        gaps.append(
            f"GANAR total {sum_ganar:,} deviates from verified {_NATIONAL_GANAR:,} by "
            f"{(sum_ganar - _NATIONAL_GANAR) / _NATIONAL_GANAR * 100:+.2f}%"
        )
    actual_winners = frozenset(
        r["department_ascii"]
        for r in rows
        if int(r["alegre_ganar_votes"]) > int(r["abdo_anr_votes"])
    )
    wrong = actual_winners.symmetric_difference(_GANAR_WINNERS)
    if wrong:
        gaps.append(f"Wrong GANAR department winners: {sorted(wrong)}")
    return gaps


def main() -> int:
    if not HEATMAP.is_file():
        return gate("F-070", Path(__file__).name, False, "geo/heatmap.py not found")
    gaps = _static_gaps(HEATMAP.read_text(encoding="utf-8")) + _runtime_gaps()
    detail = (
        "; ".join(gaps)
        if gaps
        else (
            "heatmap.py derives win probabilities from TSJE CSV via _swing_factors(); "
            "CSV reconciles to 1,206,067/1,110,464 with correct GANAR winners"
        )
    )
    return gate("F-070", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
