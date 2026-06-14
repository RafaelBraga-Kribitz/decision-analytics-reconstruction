#!/usr/bin/env python3
"""Verification script for F-068: tracking credible bands are honest 94% HDIs.

AUD interval-mislabel: ``export_daily_posterior_table`` and
``export_house_effects_table`` computed ``post.quantile(0.05)`` / ``quantile(0.95)``
— a 90% equal-tailed interval — and stored it in ``*_hdi_*`` columns that every
figure titled "94% HDI". The column name, the figure title, and the interval
that was actually computed did not agree.

Closure invariant (static source checks):
  hierarchical.py
    - computes bounds with ``az.hdi`` at ``HDI_PROB`` = 0.94,
    - no longer feeds ``quantile(0.05)`` / ``quantile(0.95)`` into the hdi columns,
    - stamps ``interval_type`` / ``interval_prob`` into the idata attrs,
    - bumped ``MODEL_VERSION`` past v0.2.
  reports/eda/generate_eda.py
    - keeps the honest "94% HDI" titles and drops the false "≈ 2σ" note.

The runtime numeric proof (exported bands == az.hdi(0.94) and are wider than the
old 90% ETI) lives in module_c .../tests/test_interval_consistency.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

HIER = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "models"
    / "tracking"
    / "hierarchical.py"
)
GENERATOR = REPO_ROOT / "reports" / "eda" / "generate_eda.py"


def _hier_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if "HDI_PROB = 0.94" not in src:
        gaps.append("hierarchical.py does not define HDI_PROB = 0.94")
    if "az.hdi(" not in src:
        gaps.append("hierarchical.py does not compute bounds via az.hdi")
    if re.search(r"quantile\(0\.0?5", src) or re.search(r"quantile\(0\.95", src):
        gaps.append("hierarchical.py still uses 5/95 quantiles (mislabelled as HDI)")
    if 'idata.attrs["interval_type"]' not in src:
        gaps.append("hierarchical.py does not stamp interval_type into idata attrs")
    if re.search(r'MODEL_VERSION = "c_tracking_hierarchical_v0\.2"', src):
        gaps.append("MODEL_VERSION still v0.2 — interval semantics changed, bump it")
    return gaps


def _generator_gaps(src: str) -> list[str]:
    gaps: list[str] = []
    if "94% HDI" not in src:
        gaps.append("generate_eda.py lost the '94% HDI' band titles")
    if "equivalent to 2σ" in src or "equivalent to 2\\u03c3" in src:
        gaps.append("generate_eda.py still claims the 94% HDI is '≈ 2σ' (it is ≈1.9σ)")
    return gaps


def main() -> int:
    if not HIER.is_file():
        return gate("F-068", Path(__file__).name, False, "missing hierarchical.py")
    if not GENERATOR.is_file():
        return gate("F-068", Path(__file__).name, False, "missing generate_eda.py")
    gaps = _hier_gaps(HIER.read_text(encoding="utf-8"))
    gaps += _generator_gaps(GENERATOR.read_text(encoding="utf-8"))
    detail = (
        "; ".join(gaps)
        if gaps
        else "tracking bands computed as true 94% HDI; column / title / interval agree"
    )
    return gate("F-068", Path(__file__).name, not gaps, detail)


if __name__ == "__main__":
    sys.exit(main())
