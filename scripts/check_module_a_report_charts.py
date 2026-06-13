#!/usr/bin/env python3
"""Verification script for F-047 (Module A static report charts missing).

The propensity model card documents SHAP summary output at
reports/module_a/shap_summary.png. The reliability diagram is the primary
calibration visual cited in the model card but is only rendered in Streamlit,
not exported to reports/ for portfolio or CI consumption.
"""

from __future__ import annotations

from pathlib import Path

from _governance_check import REPO_ROOT, gate

MODEL_CARD = REPO_ROOT / "module_a_population_segmentation" / "reports" / "model_card_propensity.md"
SHAP_PNG = REPO_ROOT / "reports" / "module_a" / "shap_summary.png"
RELIABILITY_PNG = REPO_ROOT / "reports" / "module_a" / "reliability_diagram.png"
SHAP_SCRIPT = REPO_ROOT / "scripts" / "generate_module_a_report_charts.py"
MAKEFILE = REPO_ROOT / "Makefile"


def _png_too_small(path: Path) -> bool:
    return not path.is_file() or path.stat().st_size < 512


def _shap_gaps() -> list[str]:
    if not MODEL_CARD.is_file() or "shap_summary.png" not in MODEL_CARD.read_text(encoding="utf-8"):
        return []
    if _png_too_small(SHAP_PNG):
        return ["reports/module_a/shap_summary.png missing (referenced in model card)"]
    return []


def _reliability_gaps() -> list[str]:
    if _png_too_small(RELIABILITY_PNG):
        return [
            "reports/module_a/reliability_diagram.png missing "
            "(model card cites reliability diagram)"
        ]
    return []


def _makefile_gaps() -> list[str]:
    if not MAKEFILE.is_file():
        return []
    mk = MAKEFILE.read_text(encoding="utf-8")
    gaps: list[str] = []
    if "module-a-report-charts" not in mk or "generate_module_a_report_charts" not in mk:
        gaps.append("Makefile missing module-a-report-charts target")
    if "pipeline-full:" in mk:
        block = mk.split("pipeline-full:", 1)[1].split("\n\n", 1)[0]
        if "module-a-report-charts" not in block:
            gaps.append("pipeline-full does not invoke module-a-report-charts")
    return gaps


def main() -> int:
    gaps = _shap_gaps() + _reliability_gaps() + _makefile_gaps()
    if not SHAP_SCRIPT.is_file():
        gaps.append("missing scripts/generate_module_a_report_charts.py")
    ok = not gaps
    detail = "; ".join(gaps) if gaps else "Module A report chart artifacts present and wired"
    return gate("F-047", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
