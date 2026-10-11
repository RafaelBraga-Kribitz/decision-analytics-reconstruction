#!/usr/bin/env python3
"""Verification script for F-083 (MCMC convergence gates are a real merge gate).

F-042 only required that the full-NUTS diagnostics be *disclosed*. This check
requires that they are *enforced*: the tests are hard (no xfail), a CI job
actually runs the slow lane with full NUTS, and no committed doc still calls
the gates aspirational.

Spec: governance/improvement_plan/IMP-C01_mcmc-convergence-gates.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

MCMC_TEST = (
    REPO_ROOT / "module_c_forecasting_scenarios" / "tests" / "test_mcmc_diagnostics_summary.py"
)
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PROOF_TABLE = REPO_ROOT / "module_c_forecasting_scenarios" / "reports" / "C_research_proof_table.md"
MODULE_C_README = REPO_ROOT / "module_c_forecasting_scenarios" / "README.md"

SLOW_LANE_JOB = "module-c-slow-nuts"

# Gate name -> assertion that must appear verbatim in the test module.
REQUIRED_ASSERTIONS = {
    "R-hat <= 1.01": "rhat <= 1.01",
    "bulk ESS >= 400": "ess_bulk >= 400",
    "tail ESS >= 400": "ess_tail >= 400",
    "zero divergences": "n_div == 0",
    "posterior stability (mean)": "mean_gap.max() <= 0.05",
}


def _test_gaps() -> list[str]:
    if not MCMC_TEST.is_file():
        return ["missing test_mcmc_diagnostics_summary.py"]
    text = MCMC_TEST.read_text(encoding="utf-8")
    gaps = []
    if "pytest.mark.xfail" in text:
        gaps.append("an MCMC diagnostics test is xfail'd")
    gaps += [
        f"diagnostics test lacks the {name} assertion"
        for name, needle in REQUIRED_ASSERTIONS.items()
        if needle not in text
    ]
    return gaps


def _runs_slow_lane(step: dict) -> bool:
    run = str(step.get("run", ""))
    targets_tests = re.search(
        r"module_c_forecasting_scenarios/tests(/test_mcmc_diagnostics_summary\.py)?(\s|$)", run
    )
    return bool(targets_tests and re.search(r"-m\s+[\"']?slow\b", run))


def _ci_gaps() -> list[str]:
    if not CI_WORKFLOW.is_file():
        return ["missing .github/workflows/ci.yml"]
    jobs = (yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8")) or {}).get("jobs", {})
    job = jobs.get(SLOW_LANE_JOB)
    if job is None:
        return [f"ci.yml has no '{SLOW_LANE_JOB}' job, so no CI run executes the slow lane"]
    if "if" in job:
        return [f"'{SLOW_LANE_JOB}' is conditional ({job['if']!r}); it must run on every PR"]
    runs_slow = [s for s in job.get("steps", []) if _runs_slow_lane(s)]
    if not runs_slow:
        return [f"'{SLOW_LANE_JOB}' does not run the Module C diagnostics tests with -m slow"]
    # MC_FAST is truthy for any non-empty string, so any value selects the
    # 50-draw path and silently voids the full-NUTS gates.
    if any("MC_FAST" in {**job.get("env", {}), **s.get("env", {})} for s in runs_slow):
        return [f"'{SLOW_LANE_JOB}' sets MC_FAST, which disables full NUTS"]
    return []


def _doc_gaps() -> list[str]:
    gaps = []
    if PROOF_TABLE.is_file():
        text = PROOF_TABLE.read_text(encoding="utf-8")
        section = text.split("## MCMC diagnostics", 1)[-1].split("\n## ", 1)[0]
        if "## MCMC diagnostics" not in text:
            gaps.append("C_research_proof_table.md has no MCMC diagnostics section")
        elif "aspirational" in section.lower():
            gaps.append("C_research_proof_table.md still calls the MCMC gates aspirational")
        elif SLOW_LANE_JOB not in section:
            gaps.append(f"C_research_proof_table.md does not name the '{SLOW_LANE_JOB}' CI lane")
    if MODULE_C_README.is_file() and "--run-slow" in MODULE_C_README.read_text(encoding="utf-8"):
        gaps.append("Module C README cites a nonexistent --run-slow flag")
    return gaps


def main() -> int:
    gaps = _test_gaps() + _ci_gaps() + _doc_gaps()
    return gate("F-083", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
