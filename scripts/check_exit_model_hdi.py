#!/usr/bin/env python3
"""Verification script for F-074: exit_model.py uses az.hdi(0.94), not 90% ETI quantiles.

Prior bug: s.quantile(0.05) / s.quantile(0.95) stored under hdi_low / hdi_high column names.
That is a 90% equal-tailed interval, not a 94% highest-density interval. F-068 fixed the
equivalent bug in hierarchical.py but left exit_model.py unchanged — a partial remediation.

Closure invariant:
  exit_model.py must NOT contain 's.quantile(0.05)' or 's.quantile(0.95)'.
  exit_model.py must reference 'az.hdi' and 'HDI_PROB'.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

EXIT_MODEL = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "models"
    / "exit"
    / "exit_model.py"
)

_BANNED = ["s.quantile(0.05)", "s.quantile(0.95)"]
_REQUIRED = ["az.hdi", "HDI_PROB"]


def _check(src: str) -> list[str]:
    gaps: list[str] = []
    for banned in _BANNED:
        if banned in src:
            gaps.append(f"exit_model.py still contains banned ETI expression: {banned!r}")
    for required in _REQUIRED:
        if required not in src:
            gaps.append(f"exit_model.py missing required expression: {required!r}")
    return gaps


def main() -> int:
    if not EXIT_MODEL.is_file():
        return gate("F-074", Path(__file__).name, False, "exit_model.py not found")
    gaps = _check(EXIT_MODEL.read_text(encoding="utf-8"))
    detail = (
        "; ".join(gaps)
        if gaps
        else "exit_model.py uses az.hdi(HDI_PROB=0.94); 90%-ETI expressions absent"
    )
    return gate("F-074", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
