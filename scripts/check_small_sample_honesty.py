#!/usr/bin/env python3
"""Verification script for F-085 (small-sample honesty in Module C validation).

Checks that (a) the exit quick-count flags fits below its documented
reliability floor, with one shared threshold that METHODOLOGY.md cites;
(b) walk-forward coverage is published as k/n with an exact binomial CI; and
(c) the evidence surfaces do not call these powerless checks proof.

Spec: governance/improvement_plan/IMP-C06_small-sample-honesty.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from _governance_check import REPO_ROOT, gate

MODULE_C = REPO_ROOT / "module_c_forecasting_scenarios"
METHODOLOGY = MODULE_C / "METHODOLOGY.md"
EVIDENCE_TABLE = MODULE_C / "reports" / "C_research_evidence_table.md"
LEGACY_TABLE = MODULE_C / "reports" / "C_research_proof_table.md"
LOO_REPORT = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_report.md"
LOO_METRICS = REPO_ROOT / "reports" / "module_c" / "walk_forward_loo_metrics.json"

CI_KEYS = ("coverage_95pct_k", "coverage_95pct_ci_low", "coverage_95pct_ci_high")
EVIDENTIARY = re.compile(r"\b(proof|proven|validated|calibrated)\b", re.I)
POWER_QUALIFIER = re.compile(r"no power|not evidence|cannot distinguish|smoke", re.I)


def _exit_gaps() -> list[str]:
    from module_c_forecasting_scenarios.models.exit.exit_model import fit_exit_quickcount
    from module_c_forecasting_scenarios.validation.small_n import (
        EXIT_MIN_RELIABLE_WAVES,
        is_low_n,
    )

    gaps = []
    if f"EXIT_MIN_RELIABLE_WAVES = {EXIT_MIN_RELIABLE_WAVES}" not in METHODOLOGY.read_text(
        encoding="utf-8"
    ):
        gaps.append("METHODOLOGY.md does not cite the shared EXIT_MIN_RELIABLE_WAVES value")
    if not is_low_n(EXIT_MIN_RELIABLE_WAVES - 1) or is_low_n(EXIT_MIN_RELIABLE_WAVES):
        gaps.append("is_low_n does not switch at EXIT_MIN_RELIABLE_WAVES")
    # The one-row stub path needs no sampler, so this stays fast.
    stub, _ = fit_exit_quickcount(pd.DataFrame({"m_poll_pp": [1.0]}), calibration_series="A")
    if not {"low_n", "n_waves"} <= set(stub.columns) or not bool(stub["low_n"].all()):
        gaps.append("exit model output rows lack a true low_n flag below the floor")
    return gaps


def _coverage_gaps() -> list[str]:
    from module_c_forecasting_scenarios.validation.walk_forward import summarize_walk_forward

    per_holdout = pd.DataFrame(
        {
            "prob_margin_positive": [0.6, 0.4],
            "observed_positive": [1, 0],
            "in_hdi80": [True, False],
            "in_hdi95": [True, False],
        }
    )
    gaps = []
    if not set(CI_KEYS) <= set(summarize_walk_forward(per_holdout)):
        gaps.append("summarize_walk_forward does not report coverage k and binomial CI")
    if not LOO_METRICS.is_file() or not set(CI_KEYS) <= set(
        json.loads(LOO_METRICS.read_text(encoding="utf-8"))
    ):
        gaps.append("walk_forward_loo_metrics.json lacks coverage k / binomial CI")
    if not LOO_REPORT.is_file() or "exact binomial 95% CI" not in LOO_REPORT.read_text(
        encoding="utf-8"
    ):
        gaps.append("walk_forward_loo_report.md does not quote coverage with its binomial CI")
    return gaps


def _language_gaps() -> list[str]:
    gaps = []
    if LEGACY_TABLE.exists():
        gaps.append("C_research_proof_table.md still exists (renamed to the evidence table)")
    for path in (EVIDENCE_TABLE, LOO_REPORT):
        if not path.is_file():
            gaps.append(f"missing {path.relative_to(REPO_ROOT)}")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if EVIDENTIARY.search(line) and not POWER_QUALIFIER.search(line):
                gaps.append(
                    f"{path.name}: evidentiary wording without power qualifier: {line[:80]!r}"
                )
    return gaps


def main() -> int:
    sys.path.insert(0, str(MODULE_C / "src"))
    try:
        gaps = _exit_gaps() + _coverage_gaps()
    except ImportError as exc:
        gaps = [f"small-n helpers missing ({exc})"]
    gaps += _language_gaps()
    return gate("F-085", Path(__file__).name, not gaps, "; ".join(gaps))


if __name__ == "__main__":
    sys.exit(main())
