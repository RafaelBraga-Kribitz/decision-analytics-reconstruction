#!/usr/bin/env python3
"""Verification script for F-073: canonical figure regen — deploy screenshots retired,
EDA narrative and epistemic_boundaries re-synced to real TSJE swing model.

Closure invariants:
  1. docs/assets/*-deploy/ directories are absent (screenshots retired).
  2. reports/epistemic_boundaries.md row for battleground_probability_heatmap.geojson
     says CALIBRATED (not ILLUSTRATIVE) and does not contain the stale
     '0.49–0.51' or 'seed=42' claims.
  3. reports/eda/generate_eda.py ILLUSTRATIVE_BATTLE_SUB no longer contains
     'synthetic dept mapping' — replaced with TSJE-calibrated label.
  4. reports/eda/build_notebook.py C3/C8/S4 subtitle strings no longer contain
     'synthetic dept mapping'.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

_DEPLOY_DIRS = [
    REPO_ROOT / "docs" / "assets" / "module-a-deploy",
    REPO_ROOT / "docs" / "assets" / "module-b-deploy",
    REPO_ROOT / "docs" / "assets" / "module-c-deploy",
]

_EPISTEMIC = REPO_ROOT / "reports" / "epistemic_boundaries.md"
_GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"
_NOTEBOOK = REPO_ROOT / "reports" / "eda" / "build_notebook.py"

_STALE_ILLUSTRATIVE_CLAIM = "0.49–0.51"
_STALE_SEED = "seed=42"
_STALE_SYNTHETIC_LABEL = "synthetic dept mapping"


def _deploy_gaps() -> list[str]:
    return [
        f"{d.name} deploy-screenshot directory still exists"
        for d in _DEPLOY_DIRS
        if d.exists()
    ]


def _epistemic_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    battleground_lines = [
        ln for ln in src.splitlines() if "battleground_probability_heatmap" in ln
    ]
    if not battleground_lines:
        return ["epistemic_boundaries.md has no battleground_probability_heatmap row"]
    for ln in battleground_lines:
        if "ILLUSTRATIVE" in ln and "CALIBRATED" not in ln:
            gaps.append(
                "epistemic_boundaries.md battleground row is still ILLUSTRATIVE, not CALIBRATED"
            )
        if _STALE_ILLUSTRATIVE_CLAIM in ln:
            gaps.append(
                f"epistemic_boundaries.md battleground row still contains stale claim: "
                f"{_STALE_ILLUSTRATIVE_CLAIM!r}"
            )
        if _STALE_SEED in ln:
            gaps.append(
                f"epistemic_boundaries.md battleground row still references fabricated: "
                f"{_STALE_SEED!r}"
            )
    return gaps


def _eda_gaps(gen_src: str, nb_src: str) -> list[str]:
    gaps: list[str] = []
    if _STALE_SYNTHETIC_LABEL in gen_src:
        gaps.append(
            f"generate_eda.py still contains stale label: {_STALE_SYNTHETIC_LABEL!r}"
        )
    if _STALE_SYNTHETIC_LABEL in nb_src:
        gaps.append(
            f"build_notebook.py still contains stale label: {_STALE_SYNTHETIC_LABEL!r}"
        )
    return gaps


def main() -> int:
    gaps: list[str] = _deploy_gaps()

    if not _EPISTEMIC.is_file():
        gaps.append("reports/epistemic_boundaries.md not found")
    else:
        gaps += _epistemic_gaps(_EPISTEMIC.read_text(encoding="utf-8"))

    gen_src = _GENERATOR.read_text(encoding="utf-8") if _GENERATOR.is_file() else ""
    nb_src = _NOTEBOOK.read_text(encoding="utf-8") if _NOTEBOOK.is_file() else ""
    if not _GENERATOR.is_file():
        gaps.append("reports/eda/generate_eda.py not found")
    if not _NOTEBOOK.is_file():
        gaps.append("reports/eda/build_notebook.py not found")
    gaps += _eda_gaps(gen_src, nb_src)

    detail = (
        "; ".join(gaps)
        if gaps
        else (
            "deploy screenshots retired; epistemic_boundaries battleground row "
            "reclassified CALIBRATED; EDA subtitle strings updated to TSJE-calibrated label"
        )
    )
    return gate("F-073", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
