#!/usr/bin/env python3
"""Verification script for F-090 (SHAP artifact provenance).

reports/module_a/shap_summary.png must have exactly one producer, the
canonical report-charts script that explains the fitted pipeline model, and
FIGURE_MANIFEST.yaml must name it. The orphan generator that plotted SHAP
values of a throwaway model fitted on random data must stay deleted.

Spec: governance/improvement_plan/IMP-V03_shap-provenance.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

ARTIFACT = "reports/module_a/shap_summary.png"
CANONICAL = "scripts/generate_module_a_report_charts.py"
ORPHAN = REPO_ROOT / "scripts" / "generate_module_a_shap.py"
MANIFEST = REPO_ROOT / "governance" / "FIGURE_MANIFEST.yaml"
SCAN_ROOTS = ("scripts", "module_a_population_segmentation", "reports", "shared")


def _writers() -> list[str]:
    """Python files (outside checkers) that reference the SHAP artifact's filename."""
    out = []
    for root in SCAN_ROOTS:
        for path in (REPO_ROOT / root).rglob("*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if path.name.startswith(("check_", "test_")) or "/tests/" in rel:
                continue
            if "shap_summary.png" in path.read_text(encoding="utf-8", errors="ignore"):
                out.append(rel)
    return sorted(out)


def main() -> int:
    gaps = []
    if ORPHAN.exists():
        gaps.append("scripts/generate_module_a_shap.py (fabricated-data SHAP) exists")
    writers = _writers()
    if writers != [CANONICAL]:
        gaps.append(f"expected {CANONICAL} as the only producer of {ARTIFACT}, found {writers}")
    figures = (yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}).get("figures", [])
    entry = next((f for f in figures if f.get("path") == ARTIFACT), None)
    if entry is None:
        gaps.append(f"{ARTIFACT} missing from FIGURE_MANIFEST.yaml")
    elif entry.get("generator") != CANONICAL:
        gaps.append(f"FIGURE_MANIFEST.yaml names {entry.get('generator')!r} as the SHAP generator")
    return gate("F-090", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
