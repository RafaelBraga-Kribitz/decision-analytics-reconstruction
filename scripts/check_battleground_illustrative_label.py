#!/usr/bin/env python3
"""Verification script for F-045 (battleground probabilities labeled illustrative)."""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

EPISTEMIC = REPO_ROOT / "reports" / "epistemic_boundaries.md"
HEATMAP_SRC = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)

REQUIRED = ("ILLUSTRATIVE", "illustrative", "not verified outcome")


def main() -> int:
    gaps: list[str] = []

    if EPISTEMIC.is_file():
        text = EPISTEMIC.read_text(encoding="utf-8")
        if "battleground" in text.lower() and not any(r in text for r in REQUIRED):
            gaps.append("epistemic_boundaries.md missing ILLUSTRATIVE for battleground")
    else:
        gaps.append("missing epistemic_boundaries.md")

    if HEATMAP_SRC.is_file():
        src = HEATMAP_SRC.read_text(encoding="utf-8")
        if "synthetic" not in src.lower() and "illustrative" not in src.lower():
            gaps.append("heatmap.py should document synthetic/illustrative mapping")
    else:
        gaps.append("missing geo/heatmap.py")

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "battleground outputs labeled illustrative"
    return gate("F-045", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
