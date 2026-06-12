#!/usr/bin/env python3
"""Verification script for F-042 (MCMC diagnostics aspirational disclosure)."""

from __future__ import annotations

import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

README = REPO_ROOT / "module_c_forecasting_scenarios" / "README.md"
VALIDATION = REPO_ROOT / "reports" / "VALIDATION.md"
MCMC_TEST = (
    REPO_ROOT / "module_c_forecasting_scenarios" / "tests" / "test_mcmc_diagnostics_summary.py"
)

REQUIRED_MARKERS = (
    "aspirational",
    "not enforced",
    "does not block",
    "xfail",
    "MC_FAST",
    "non-centered",
)


def _readme_gaps() -> list[str]:
    if not README.is_file():
        return ["missing module_c README"]
    readme = README.read_text(encoding="utf-8")
    has_rhat = "R̂" in readme or "R-hat" in readme
    missing_disclosure = not any(m.lower() in readme.lower() for m in REQUIRED_MARKERS)
    if has_rhat and missing_disclosure:
        return ["README lists R-hat/ESS without aspirational disclosure"]
    return []


def _mcmc_test_gaps() -> list[str]:
    if not MCMC_TEST.is_file():
        return ["missing test_mcmc_diagnostics_summary.py"]
    if MCMC_TEST.read_text(encoding="utf-8").count("@pytest.mark.xfail") == 0:
        return ["expected xfail MCMC diagnostics tests while MC_FAST is default"]
    return []


def _validation_gaps() -> list[str]:
    if not VALIDATION.is_file():
        return ["missing reports/VALIDATION.md"]
    val = VALIDATION.read_text(encoding="utf-8").lower()
    if "divergences" in val and "does not block" not in val:
        return ["VALIDATION.md should state divergences do not block delivery"]
    return []


def main() -> int:
    gaps = _readme_gaps() + _mcmc_test_gaps() + _validation_gaps()
    ok = not gaps
    detail = "; ".join(gaps) if gaps else "MCMC diagnostics disclosed as aspirational"
    return gate("F-042", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
