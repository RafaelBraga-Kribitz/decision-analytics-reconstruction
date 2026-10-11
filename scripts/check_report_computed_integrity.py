#!/usr/bin/env python3
"""Verification script for F-084 (post-mortem report computed from artifacts).

Static checks on module_c_forecasting_scenarios/portfolio/quarto/post_mortem.qmd:
interval labels are interpolated from config (no literal "NN% HDI"), the
sampling-diagnostics table reads the exported summary instead of hand-typed
values, and the methodology table matches the model constants in code.

Spec: governance/improvement_plan/IMP-C03_report-computed-integrity.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MODULE_C = REPO_ROOT / "module_c_forecasting_scenarios"
REPORT = MODULE_C / "portfolio" / "quarto" / "post_mortem.qmd"
SRC = MODULE_C / "src" / "module_c_forecasting_scenarios"
HIERARCHICAL = SRC / "models" / "tracking" / "hierarchical.py"
HEATMAP = SRC / "geo" / "heatmap.py"

LITERAL_INTERVAL = re.compile(r"\b\d{2}\s?%\s?HDI\b|\bHDI\s?\d{2}\s?%")
# A literal number (optionally &gt;/&lt;-prefixed) as an HTML table cell.
LITERAL_CELL = re.compile(r"<td[^>]*>\s*(?:&[lg]t;\s*)?\d[\d.,]*\s*</td>")
SUPERSEDED = (
    "HalfNormal(2.0)",
    "Normal(0, 3)",
    "logistic transformation",
    "synthetic geographic jitter",
    "MC_FAST=0",
    "(b) non-centered random walk reparameterization",
)


def _cell(text: str, label: str) -> str | None:
    match = re.search(r"```\{python\}\n#\| label: " + re.escape(label) + r"\n(.*?)```", text, re.S)
    return match.group(1) if match else None


def _code_constant(path: Path, pattern: str) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _label_gaps(text: str) -> list[str]:
    hits = sorted({m.group(0) for m in LITERAL_INTERVAL.finditer(text)})
    gaps = [f"literal interval label(s) {hits}; interpolate HDI_LABEL"] if hits else []
    if "pymc_sampler.yaml" not in text or "HDI_LABEL" not in text:
        gaps.append("report does not derive HDI_LABEL from config/pymc_sampler.yaml")
    return gaps


def _diagnostics_gaps(text: str) -> list[str]:
    cell = _cell(text, "tbl-diagnostics")
    if cell is None:
        return ["report has no tbl-diagnostics cell"]
    gaps = []
    if LITERAL_CELL.search(cell):
        gaps.append("tbl-diagnostics contains hand-typed numeric cells")
    if "mcmc_diagnostics_summary.json" not in text or "diag[" not in cell:
        gaps.append("tbl-diagnostics does not read mcmc_diagnostics_summary.json")
    if "not found" not in cell:
        gaps.append("tbl-diagnostics has no missing-artifact notice")
    if 'DIAGNOSTICS_FILENAME = "mcmc_diagnostics_summary.json"' not in HIERARCHICAL.read_text(
        encoding="utf-8"
    ):
        gaps.append("tracking pipeline does not export mcmc_diagnostics_summary.json")
    return gaps


def _methodology_gaps(text: str) -> list[str]:
    cell = _cell(text, "tbl-methodology")
    if cell is None:
        return ["report has no tbl-methodology cell"]
    gaps = []
    expected = {
        "sigma_rw": _code_constant(HIERARCHICAL, r'HalfNormal\("sigma_rw",\s*([\d.]+)\)'),
        "sigma_house": _code_constant(HIERARCHICAL, r'HalfNormal\("sigma_house",\s*([\d.]+)\)'),
    }
    for name, value in expected.items():
        if value is None or f"{name} ~ HalfNormal({value})" not in cell:
            gaps.append(f"methodology table {name} prior does not match code ({value})")
    battleground = _code_constant(HEATMAP, r'MODEL_VERSION = "([^"]+)"')
    if battleground is None or battleground not in cell:
        gaps.append(f"methodology table battleground version does not match code ({battleground})")
    gaps += [f"report still contains superseded text {s!r}" for s in SUPERSEDED if s in text]
    return gaps


def main() -> int:
    if not REPORT.is_file():
        return gate("F-084", Path(__file__).name, False, "missing post_mortem.qmd")
    text = REPORT.read_text(encoding="utf-8")
    gaps = _label_gaps(text) + _diagnostics_gaps(text) + _methodology_gaps(text)
    return gate("F-084", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
