#!/usr/bin/env python3
"""Verification script for F-082: battleground ceiling investigation artifacts.

Gates that the statistical investigation protocol completed with required
deliverables under reports/module_c/battleground_investigation/.
Finding F-082 remains in_progress until methodological review closes it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

INV = REPO_ROOT / "reports" / "module_c" / "battleground_investigation"
REQUIRED_FILES = [
    INV / "INVESTIGATION_REPORT.md",
    INV / "h0_verification_table.csv",
    INV / "summary_tables.csv",
    INV / "investigation_meta.json",
    INV / "power_analysis.json",
]
REQUIRED_FIGURES = [
    "residual_vs_swing.png",
    "qq_residuals.png",
    "calibration_pred_vs_realized.png",
    "abs_residual_vs_abs_swing.png",
    "P_vs_z.png",
    "m_sweep_ceiling.png",
    "ppc_max_margin_2018.png",
    "ppc_dept_margins_2018.png",
    "ppc_dept_margins_faceted.png",
    "ppc_dept_probabilities.png",
    "ppc_z_distribution.png",
    "ppc_ceiling_count.png",
    "ppc_summary_panel.png",
]
VALID_CONCLUSION_LABELS = {
    "insufficient_evidence_for_revision",
    "evidence_suggests_revision",
    "inconclusive_ppc_stress",
    "implementation_defect",
}
REPORT_MARKERS = (
    "## Part I — Model verification (H0)",
    "## Part II — Model validation",
    "## Statistical power and detectable effects",
    "## Posterior predictive checks",
    "## Part III — Model criticism",
    "no statistically robust evidence requiring a revision",
    "should **not** be interpreted as proof that the current mapping is optimal",
    "### H5 three-way verdict",
    "H0 verification establishes software fidelity only",
)


def _missing_required_files() -> list[str]:
    return [
        f"missing {path.relative_to(REPO_ROOT)}" for path in REQUIRED_FILES if not path.is_file()
    ]


def _missing_figures() -> list[str]:
    fig_dir = INV / "figures"
    return [f"missing figure {name}" for name in REQUIRED_FIGURES if not (fig_dir / name).is_file()]


def _h0_table_gaps(h0_path: Path) -> list[str]:
    if not h0_path.is_file():
        return []
    import pandas as pd

    h0 = pd.read_csv(h0_path)
    if "pass" not in h0.columns:
        return ["h0_verification_table.csv missing pass column"]
    if not bool(h0["pass"].all()):
        failed = h0.loc[~h0["pass"].astype(bool), "check"].tolist()
        return [f"H0 checks failed: {failed}"]
    return []


def _report_gaps(report_path: Path) -> list[str]:
    if not report_path.is_file():
        return []
    text = report_path.read_text(encoding="utf-8")
    gaps = [
        f"INVESTIGATION_REPORT missing marker: {section!r}"
        for section in REPORT_MARKERS
        if section not in text
    ]
    if "**Primary outcome:** A" in text or "no model revision required" in text.lower():
        gaps.append("report uses over-strong Outcome A / no-revision language")
    return gaps


def _meta_gaps(meta_path: Path, prior_gaps: list[str]) -> list[str]:
    if not meta_path.is_file():
        return []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    gaps: list[str] = []
    label = meta.get("conclusion_label")
    if label not in VALID_CONCLUSION_LABELS:
        gaps.append(f"invalid or missing conclusion_label: {label!r}")
    if meta.get("h0_implementation") is None:
        gaps.append("investigation_meta.json missing h0_implementation")
    if meta.get("h5_internal_coherence") is None:
        gaps.append("investigation_meta.json missing h5_internal_coherence (H0/adequacy split)")
    h0_verified = meta.get("hypothesis_status", {}).get("H0_implementation") == "verified"
    h0_impl_ok = meta.get("h0_implementation", "").startswith("verified")
    if not h0_verified and not prior_gaps and not h0_impl_ok:
        gaps.append("H0 implementation not verified in meta")
    return gaps


def _power_gaps(power_path: Path) -> list[str]:
    if not power_path.is_file():
        return []
    power = json.loads(power_path.read_text(encoding="utf-8"))
    gaps: list[str] = []
    if "power_by_true_effect" not in power:
        gaps.append("power_analysis.json missing power_by_true_effect")
    if "minimum_detectable_mad_improvement_approx_pp" not in power:
        gaps.append("power_analysis.json missing MDE estimate")
    return gaps


def main() -> int:
    gaps: list[str] = []
    gaps.extend(_missing_required_files())
    gaps.extend(_missing_figures())
    gaps.extend(_h0_table_gaps(INV / "h0_verification_table.csv"))
    gaps.extend(_report_gaps(INV / "INVESTIGATION_REPORT.md"))
    gaps.extend(_meta_gaps(INV / "investigation_meta.json", gaps))
    gaps.extend(_power_gaps(INV / "power_analysis.json"))

    ok = not gaps
    gap_msg = "; ".join(gaps) if gaps else ""
    return gate("F-082", "check_battleground_ceiling_investigation.py", ok, gap_msg)


if __name__ == "__main__":
    sys.exit(main())
