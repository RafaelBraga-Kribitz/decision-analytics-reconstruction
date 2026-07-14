#!/usr/bin/env python3
"""Verification script for F-078: battleground circularity disclosed at every surface.

The department win-probability product consumes outcome data at the swing-factor
layer (and optionally at the national anchor for retrodiction). F-078 closes
only while every consumer-facing surface says so:

  1. ``schema_contracts/battleground_department_probability.yaml`` declares
     poll_implied and retrodiction estimands, outcome-data entry points, and
     the illustrative sigma.
  2. The contract's field set carries ``estimand`` and bounded ``hdi_low``/``hdi_high``.
  3. The Quarto source's battleground section carries swing-factor and
     retrodiction disclosure adjacent to ``fig-battleground``, and the chart
     draws the interval (``error_x`` from the hdi columns).
  4. ``geo/heatmap.py`` justifies ``_SIGMA_IDIO_PP`` without a target visual
     property and records its provenance.
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
        ("poll_implied", "poll_implied primary estimand declaration"),
        ("retrodiction", "retrodiction companion estimand declaration"),
        ("use_outcome_anchor", "outcome-anchored national posterior entry point"),
        ("tsje_2018_department_results", "outcome-derived swing factors entry point"),
        ("data/reference/battleground", "reference sigma_idio data path"),
    ):
        if needle not in desc:
            gaps.append(f"contract description lost the {what}")
    fields = spec.get("fields", {})
    est = fields.get("estimand", {})
    allowed = est.get("allowed_values") or []
    for val in ("poll_implied", "retrodiction"):
        if val not in allowed:
            gaps.append(f"contract lacks estimand allowed_value {val}")
    for col in ("hdi_low", "hdi_high"):
        f = fields.get(col, {})
        if f.get("min") != 0.0 or f.get("max") != 1.0:
            gaps.append(f"contract lacks bounded {col} field ([0,1])")
    return gaps


def _qmd_gaps() -> list[str]:
    gaps: list[str] = []
    text = QMD.read_text(encoding="utf-8")
    m = re.search(r"## Department-Level Win Probability.*?fig-battleground-choropleth", text, re.S)
    block = m.group(0) if m else ""
    if not block:
        return ["post_mortem.qmd battleground section not found"]
    if "retrodiction" not in block.lower():
        gaps.append("qmd battleground section lost the retrodiction disclosure")
    if "swing factors" not in block:
        gaps.append("qmd battleground section lost the outcome-derived swing factors disclosure")
    if "error_x" not in block:
        gaps.append("fig-battleground no longer draws the HDI interval (error_x)")
    if "reference" not in block.lower() and "illustrative" not in block.lower():
        gaps.append("qmd battleground section lost sigma provenance disclosure")
    if "poll-implied" not in block.lower() and "poll_implied" not in block.lower():
        gaps.append("qmd battleground section lost poll-implied primary labeling")
    return gaps


def _heatmap_gaps() -> list[str]:
    gaps: list[str] = []
    src = HEATMAP.read_text(encoding="utf-8")
    if re.search(r"calibrated to give\s*~?\d+", src, re.I):
        gaps.append("heatmap.py justifies sigma by a target visual width again")
    if "_SIGMA_IDIO_PROVENANCE_FALLBACK" not in src and "_SIGMA_IDIO_PROVENANCE" not in src:
        gaps.append("heatmap.py lost the sigma provenance record")
    if "load_sigma_yaml" not in src:
        gaps.append("heatmap.py lost reference sigma loader")
    return gaps


def main() -> int:
    gaps = _contract_gaps() + _qmd_gaps() + _heatmap_gaps()
    ok = not gaps
    detail = "all disclosure surfaces intact" if ok else "; ".join(gaps)
    return gate("F-078", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
