#!/usr/bin/env python3
"""Verification script for F-072: published artifacts single-source shared numbers.

AUD SSOT: two published artifacts reported the same quantity with different numbers.
reports/eda/generate_eda.py prose said pollster house effects were ATI/Snead −5.1 pp
/ ICA +3.8 pp, while reports/eda/build_notebook.py prose said ATI/Snead +1.5 pp /
CAPLI −2.1 pp — both hardcoded, mutually contradictory, and disagreeing with the
posterior_house_effects.parquet that the C4 figure in each actually plots.

Closure invariant (static source checks):
  Both generators derive their house-effect prose from the parquet (they reference
  the derived ``_he_*`` variables) and neither hardcodes a contradictory pollster
  house-effect pp literal. Single source => the report, the notebook, and the figure
  cannot diverge on this quantity.

The runtime cross-artifact agreement (the report's house-effect number matches the
parquet) is gated by tests/test_golden_metrics.py::test_house_effect_prose_single_sourced.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

GEN = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
NB = REPO_ROOT / "reports" / "eda" / "build_notebook.py"

# Stale hardcoded house-effect literals that must never reappear in prose.
_BANNED = re.compile(r"(ATI/Snead has a [+\-−]?5\.1|~\+1\.5 pp|\(-2\.1 pp\)|\+3\.8 pp\)\. CAPLI)")


def _gen_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if "_he_neg_name" not in src or "_he_pos_name" not in src:
        gaps.append("generate_eda.py house-effect prose is not derived (_he_*_name missing)")
    if _BANNED.search(src):
        gaps.append("generate_eda.py still hardcodes a contradictory house-effect pp literal")
    return gaps


def _nb_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if "_he_hi_name" not in src or "_he_lo_name" not in src:
        gaps.append("build_notebook.py house-effect prose is not derived (_he_*_name missing)")
    if _BANNED.search(src):
        gaps.append("build_notebook.py still hardcodes a contradictory house-effect pp literal")
    return gaps


def main() -> int:
    for path in (GEN, NB):
        if not path.is_file():
            return gate("F-072", Path(__file__).name, False, f"missing {path.name}")
    gaps = _gen_gaps(GEN.read_text(encoding="utf-8")) + _nb_gaps(NB.read_text(encoding="utf-8"))
    detail = (
        "; ".join(gaps)
        if gaps
        else "house-effect prose is single-sourced from the parquet in both generators"
    )
    return gate("F-072", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
