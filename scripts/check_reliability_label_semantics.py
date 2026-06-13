#!/usr/bin/env python3
"""Verification script for F-075: reliability diagnostics use training-target labels.

Bernoulli national-rate coin-flips against dept-structured propensity scores
produce wild bin swings (AUD-REL). Production paths must use the same synthetic
label generator as propensity fit, and static PNGs must carry a disclaimer footer.
"""

from __future__ import annotations

import re
from pathlib import Path

from _governance_check import REPO_ROOT, gate

ROOT = REPO_ROOT
DASHBOARD = ROOT / "module_a_population_segmentation" / "app" / "streamlit_dashboard.py"
REPORT_CHARTS = ROOT / "scripts" / "generate_module_a_report_charts.py"
RELIABILITY_PNG = ROOT / "reports" / "module_a" / "reliability_diagram.png"
PROP_PATH = (
    ROOT
    / "module_a_population_segmentation"
    / "src"
    / "population_segmentation"
    / "pipeline"
    / "models"
    / "propensity.py"
)
SCHEMA_PATH = (
    ROOT
    / "module_a_population_segmentation"
    / "src"
    / "population_segmentation"
    / "evaluation"
    / "schema_validator.py"
)


def _dashboard_gaps(dash: str) -> list[str]:
    gaps: list[str] = []
    if "synthetic_training_reference_labels" not in dash:
        gaps.append("dashboard missing synthetic_training_reference_labels")
    if "_make_national_reference_labels" in dash:
        gaps.append("dashboard still defines Bernoulli national reference helper")
    if "Bernoulli" in dash and "training-target" not in dash.lower():
        gaps.append("dashboard still references Bernoulli without training-target framing")
    return gaps


def _report_charts_gaps(charts: str) -> list[str]:
    gaps: list[str] = []
    if "synthetic_training_reference_labels" not in charts:
        gaps.append("generate_module_a_report_charts missing training-target labels")
    if "rng.random(len(pop)) < national_rate" in charts:
        gaps.append("generate_module_a_report_charts still uses Bernoulli national labels")
    if "RELIABILITY_DISCLAIMER" not in charts:
        gaps.append("generate_module_a_report_charts missing disclaimer constant")
    return gaps


def _propensity_gaps(prop_src: str) -> list[str]:
    if "def synthetic_training_reference_labels" not in prop_src:
        return ["propensity.py missing synthetic_training_reference_labels export"]
    return []


def _schema_gaps(schema: str) -> list[str]:
    if re.search(r"youth_flag.*18.?29", schema):
        return ["schema_validator youth_flag title still says 18-29"]
    return []


def main() -> int:
    gaps = [
        *_dashboard_gaps(DASHBOARD.read_text(encoding="utf-8")),
        *_report_charts_gaps(REPORT_CHARTS.read_text(encoding="utf-8")),
        *_propensity_gaps(PROP_PATH.read_text(encoding="utf-8")),
        *_schema_gaps(SCHEMA_PATH.read_text(encoding="utf-8")),
    ]
    if not RELIABILITY_PNG.is_file():
        gaps.append(
            "missing reports/module_a/reliability_diagram.png — "
            "run generate_module_a_report_charts.py"
        )

    ok = not gaps
    detail = "; ".join(gaps) if gaps else "reliability paths use training-target label semantics"
    return gate("F-075", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
