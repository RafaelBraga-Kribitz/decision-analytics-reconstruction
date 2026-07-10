#!/usr/bin/env python3
"""Verification script for F-079: propensity AUC gate integrity + spread parity.

Three invariants (IMP-A01), all static — no model fit:

  1. The Gate A8 test (tests/test_propensity.py::test_auc_floor_ablated_gate)
     imports PropensityModel, calls fit_predict, and gates
     ``auc_roc_ablated`` — and no test anywhere claims to be "Gate A8" while
     asserting an AUC floor on a hand-built array (the retired
     test_auc_floor defect).
  2. Test/production spread parity: tests/test_propensity.py must read
     ``individual_spread_std`` from config/model_params.yaml (a
     production_spread_std fixture built from the YAML) and pass it to every
     gate's PropensityModel construction — no gate may run on the bare
     dataclass default again.
  3. The module README's AUC gate line must quote the ablated metric or
     carry an explicit circularity caveat — a bare "AUC-ROC > 0.70" with no
     caveat is a failing state.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from _governance_check import REPO_ROOT, gate

MOD = REPO_ROOT / "module_a_population_segmentation"
TEST_PROPENSITY = MOD / "tests" / "test_propensity.py"
TEST_EVALUATION = MOD / "tests" / "test_evaluation.py"
MODEL_PARAMS = MOD / "config" / "model_params.yaml"
README = MOD / "README.md"


def _gate_test_gaps() -> list[str]:
    gaps: list[str] = []
    src = TEST_PROPENSITY.read_text(encoding="utf-8")
    if "def test_auc_floor_ablated_gate" not in src:
        gaps.append("test_propensity.py lost test_auc_floor_ablated_gate")
        return gaps
    if "PropensityModel" not in src or "fit_predict" not in src:
        gaps.append("Gate A8 test no longer calls PropensityModel.fit_predict")
    if "auc_roc_ablated" not in src:
        gaps.append("Gate A8 test no longer gates auc_roc_ablated")
    if "auc_floor_ablated" not in src:
        gaps.append("Gate A8 floor is not read from model_params.yaml")
    ev = TEST_EVALUATION.read_text(encoding="utf-8")
    for m in re.finditer(r"def (test_\w*auc\w*)\(.*?\n(?=def |\Z)", ev, re.S):
        body = m.group(0)
        if "Gate" in body and "PropensityModel" not in body and ">=" in body:
            gaps.append(
                f"test_evaluation.py::{m.group(1)} claims a gate but never "
                "calls the model (the retired toy-array defect)"
            )
    return gaps


def _spread_parity_gaps() -> list[str]:
    gaps: list[str] = []
    params = yaml.safe_load(MODEL_PARAMS.read_text(encoding="utf-8"))
    if "individual_spread_std" not in params.get("propensity", {}):
        return ["model_params.yaml lost propensity.individual_spread_std"]
    src = TEST_PROPENSITY.read_text(encoding="utf-8")
    if "production_spread_std" not in src or "individual_spread_std" not in src:
        gaps.append(
            "test_propensity.py no longer wires model_params.yaml's "
            "individual_spread_std into its PropensityModel constructions"
        )
    # every gate construction must pass the production value
    bare = re.findall(r"PropensityModel\(random_state=\d+\)", src)
    if bare:
        gaps.append(
            f"{len(bare)} PropensityModel construction(s) in test_propensity.py "
            "use the bare dataclass spread default instead of the production value"
        )
    return gaps


def _readme_gaps() -> list[str]:
    text = README.read_text(encoding="utf-8")
    for line in text.splitlines():
        is_gate_line = "AUC" in line and (">" in line or "≥" in line)
        if is_gate_line and "ablated" not in line.lower() and "circular" not in line.lower():
            return [
                "README AUC gate line carries neither the ablated metric "
                f"nor a circularity caveat: {line.strip()[:100]}"
            ]
    return []


def main() -> int:
    gaps = _gate_test_gaps() + _spread_parity_gaps() + _readme_gaps()
    ok = not gaps
    detail = "gate integrity + spread parity intact" if ok else "; ".join(gaps)
    return gate("F-079", Path(__file__).name, ok, detail)


if __name__ == "__main__":
    sys.exit(main())
