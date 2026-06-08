#!/usr/bin/env python3
"""Verify the default pytest target can collect without conftest collisions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

ARGS = [
    "poetry",
    "run",
    "pytest",
    "module_a_population_segmentation/tests",
    "module_b_resource_allocation/tests",
    "module_c_forecasting_scenarios/tests",
    "tests",
    "--collect-only",
    "-q",
]


def main() -> int:
    proc = subprocess.run(
        ARGS,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = proc.stdout + proc.stderr
    return gate(
        "F-006",
        Path(__file__).name,
        proc.returncode == 0,
        "pytest collection failed: " + output.splitlines()[-1][:160],
    )


if __name__ == "__main__":
    sys.exit(main())
