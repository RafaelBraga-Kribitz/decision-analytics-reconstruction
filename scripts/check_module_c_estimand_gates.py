#!/usr/bin/env python3
"""Verify Module C estimand and calibration-verdict gates (F-034).

Runs the fast core-correctness tests (verdict rubric, config-driven shock
threshold, shared observation-noise function) plus the walk-forward suite,
whose coverage assertion fails under the former latent-only estimand.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

TESTS = [
    "module_c_forecasting_scenarios/tests/test_core_correctness_gates.py",
    "module_c_forecasting_scenarios/tests/test_walk_forward.py",
]


def main() -> int:
    env = dict(os.environ, MC_FAST="1")
    proc = subprocess.run(
        ["poetry", "run", "pytest", "-q", *TESTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=1800,
        env=env,
    )
    passed = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    summary = tail[-1] if tail else "no output"
    return gate("F-034", Path(__file__).name, passed, summary)


if __name__ == "__main__":
    sys.exit(main())
