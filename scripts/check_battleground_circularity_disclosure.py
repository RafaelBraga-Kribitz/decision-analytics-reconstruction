#!/usr/bin/env python3
"""Verification script for F-078: battleground circularity disclosed at every surface.

The department win-probability product consumes outcome data twice — an
outcome-anchored national posterior and swing factors derived from the
realized TSJE department results — and its idiosyncratic dispersion floor is
an illustrative assumption, not an estimate. F-078 closes only while every
consumer-facing surface says so:

  1. ``schema_contracts/battleground_department_probability.yaml`` declares
     the retrodiction estimand, both outcome-data entry points, and the
     illustrative sigma.
  2. The contract's field set carries ``estimand`` (allowed values naming
     retrodiction) and bounded ``hdi_low``/``hdi_high``.
  3. The Quarto source's battleground section carries the retrodiction
     disclosure adjacent to ``fig-battleground``, and the chart draws the
     interval (``error_x`` from the hdi columns) rather than hover-only.
  4. ``geo/heatmap.py`` justifies ``_SIGMA_IDIO_PP`` without a target visual
     property ("gives ~X pp width" is banned) and records its provenance.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

CONTRACT = REPO_ROOT / "schema_contracts" / "battleground_department_probability.yaml"
QMD = REPO_ROOT / "module_c_forecasting_scenarios" / "portfolio" / "quarto" / "post_mortem.qmd"
HEATMAP = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "heatmap.py"
)


def _contract_gaps() -> list[str]:
    gaps: list[str] = []
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    desc = str(spec.get("description", ""))
    for needle, what in (
        ("RETRODICTION", "retrodiction estimand declaration"),
        ("use_outcome_anchor", "outcome-anchored national posterior entry point"),
        ("tsje_2018_department_results", "outcome-derived swing factors entry point"),
        ("ILLUSTRATIVE", "illustrative sigma_idio declaration"),
    ):
        if needle not in desc:
            gaps.append(f"contract description lost the {what}")
    fields = spec.get("fields", {})
    est = fields.get("estimand", {})
    if "retrodiction" not in (est.get("allowed_values") or []):
        gaps.append("contract lacks estimand field with retrodiction in allowed_values")
    for col in ("hdi_low", "hdi_high"):
        f = fields.get(col, {})
        if f.get("min") != 0.0 or f.get("max") != 1.0:
            gaps.append(f"contract lacks bounded {col} field ([0,1])")
    return gaps


def _qmd_gaps() -> list[str]:
    gaps: list[str] = []
    text = QMD.read_text(encoding="utf-8")
    m = re.search(
        r"## Department-Level Outcome Probability.*?fig-battleground-choropleth", text, re.S
    )
    block = m.group(0) if m else ""
    if not block:
        return ["post_mortem.qmd battleground section not found"]
    if "retrodiction" not in block.lower():
        gaps.append("qmd battleground section lost the retrodiction disclosure")
    if "swing factors" not in block:
        gaps.append("qmd battleground section lost the outcome-derived swing factors disclosure")
    if "error_x" not in block:
        gaps.append("fig-battleground no longer draws the HDI interval (error_x)")
    if "illustrative" not in block.lower():
        gaps.append("qmd battleground section lost the illustrative-sigma disclosure")
    return gaps


def _heatmap_gaps() -> list[str]:
    gaps: list[str] = []
    src = HEATMAP.read_text(encoding="utf-8")
    if re.search(r"calibrated to give\s*~?\d+", src, re.I):
        gaps.append("heatmap.py justifies sigma by a target visual width again")
    if "_SIGMA_IDIO_PROVENANCE" not in src:
        gaps.append("heatmap.py lost the sigma provenance record")
    if "illustrative" not in src.lower():
        gaps.append("heatmap.py lost the illustrative-assumption labeling")
    return gaps


def main() -> int:
    gaps = _contract_gaps() + _qmd_gaps() + _heatmap_gaps()
    ok = not gaps
    detail = "all disclosure surfaces intact" if ok else "; ".join(gaps)
    return gate("F-078", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
