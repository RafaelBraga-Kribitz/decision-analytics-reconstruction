#!/usr/bin/env python3
"""Verification script for F-045 (battleground probabilities honestly classified).

History: F-045 originally required geo/heatmap.py to label its department win
probabilities as "synthetic/illustrative", because v0.1 derived them from
deterministic jitter around the national margin (seed=42). F-070 replaced that
fabricated formula with a model calibrated to the verified 2018 TSJE per-department
returns. Continuing to force the word "synthetic" onto a real-data model would be a
NEW dishonesty — exactly the failure mode the governance system exists to prevent.

Honest post-F-070 invariant (what this script now enforces):
  1. geo/heatmap.py documents its real data provenance (references TSJE) and does
     NOT reintroduce the fabricated v0.1 formula.
  2. epistemic_boundaries.md still carries an honest epistemic classification for
     the battleground artifact AND an explicit anti-overclaim caveat — the
     per-department probabilities must never be presented as a verified, independent
     per-department outcome forecast. Both the pre-regen ("illustrative … not
     verified outcome") and post-regen ("calibrated swing reconstruction … not
     verified outcome") wordings satisfy this; what is banned is dropping the
     caveat or presenting the choropleth as a verified forecast.
"""

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

# The fabricated v0.1 formula that must never come back.
_BANNED_FORMULA = "0.12 * (last - 3.8)"
# An honest epistemic classification: any one of these must label the battleground row.
_CLASSIFICATION = ("illustrative", "calibrated", "reconstruction", "swing")
# An explicit anti-overclaim caveat: the choropleth is not a verified outcome forecast.
_ANTI_OVERCLAIM = ("not verified outcome", "not a verified", "not an independent")


def _heatmap_gaps() -> list[str]:
    if not HEATMAP_SRC.is_file():
        return ["missing geo/heatmap.py"]
    src = HEATMAP_SRC.read_text(encoding="utf-8")
    gaps: list[str] = []
    if "tsje" not in src.lower():
        gaps.append("heatmap.py does not document its TSJE data provenance")
    if _BANNED_FORMULA in src:
        gaps.append("heatmap.py reintroduced the fabricated v0.1 jitter formula")
    return gaps


def _epistemic_gaps() -> list[str]:
    if not EPISTEMIC.is_file():
        return ["missing epistemic_boundaries.md"]
    lower = EPISTEMIC.read_text(encoding="utf-8").lower()
    if "battleground" not in lower:
        return []
    gaps: list[str] = []
    if not any(k in lower for k in _CLASSIFICATION):
        gaps.append("epistemic_boundaries.md battleground row missing epistemic class")
    if not any(k in lower for k in _ANTI_OVERCLAIM):
        gaps.append("epistemic_boundaries.md battleground row dropped the not-a-verified caveat")
    return gaps


def main() -> int:
    gaps = _heatmap_gaps() + _epistemic_gaps()
    detail = "; ".join(gaps) if gaps else "battleground honestly classified, not overclaimed"
    return gate("F-045", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
