#!/usr/bin/env python3
"""Verification script for F-082: battleground ceiling investigation artifacts.

Gates that the statistical investigation protocol completed with required
deliverables under reports/module_c/battleground_investigation/.
Finding F-082 remains in_progress until methodological review closes it.
"""

from __future__ import annotations

import json
import sys

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


def main() -> int:
    gaps: list[str] = []

    for path in REQUIRED_FILES:
        if not path.is_file():
            gaps.append(f"missing {path.relative_to(REPO_ROOT)}")

    fig_dir = INV / "figures"
    for name in REQUIRED_FIGURES:
        if not (fig_dir / name).is_file():
            gaps.append(f"missing figure {name}")

    h0_path = INV / "h0_verification_table.csv"
    if h0_path.is_file():
        import pandas as pd

        h0 = pd.read_csv(h0_path)
        if "pass" not in h0.columns:
            gaps.append("h0_verification_table.csv missing pass column")
        elif not bool(h0["pass"].all()):
            failed = h0.loc[~h0["pass"].astype(bool), "check"].tolist()
            gaps.append(f"H0 checks failed: {failed}")

    report_path = INV / "INVESTIGATION_REPORT.md"
    if report_path.is_file():
        text = report_path.read_text(encoding="utf-8")
        for section in REPORT_MARKERS:
            if section not in text:
                gaps.append(f"INVESTIGATION_REPORT missing marker: {section!r}")
        if "**Primary outcome:** A" in text or "no model revision required" in text.lower():
            gaps.append("report uses over-strong Outcome A / no-revision language")

    meta_path = INV / "investigation_meta.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        label = meta.get("conclusion_label")
        if label not in VALID_CONCLUSION_LABELS:
            gaps.append(f"invalid or missing conclusion_label: {label!r}")
        if meta.get("h0_implementation") is None:
            gaps.append("investigation_meta.json missing h0_implementation")
        if meta.get("h5_internal_coherence") is None:
            gaps.append("investigation_meta.json missing h5_internal_coherence (H0/adequacy split)")
        if (
            meta.get("hypothesis_status", {}).get("H0_implementation") != "verified"
            and not gaps
            and not meta.get("h0_implementation", "").startswith("verified")
        ):
            gaps.append("H0 implementation not verified in meta")

    power_path = INV / "power_analysis.json"
    if power_path.is_file():
        power = json.loads(power_path.read_text(encoding="utf-8"))
        if "power_by_true_effect" not in power:
            gaps.append("power_analysis.json missing power_by_true_effect")
        if "minimum_detectable_mad_improvement_approx_pp" not in power:
            gaps.append("power_analysis.json missing MDE estimate")

    ok = not gaps
    gap_msg = "; ".join(gaps) if gaps else ""
    return gate("F-082", "check_battleground_ceiling_investigation.py", ok, gap_msg)


if __name__ == "__main__":
    sys.exit(main())
