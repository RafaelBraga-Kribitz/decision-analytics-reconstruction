#!/usr/bin/env python3
"""Verify Module B solver correctness gates (F-033).

Runs the post-solve contract gate tests: real 80% coverage floor (regression
for the silent `* 0.05` bug), budget envelope enforcement, binding-constraint
diagnostics, and counterfactual DR-parameter fidelity.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

TESTS = [
    "module_b_resource_allocation/tests/test_allocation_output_gate.py",
    "module_b_resource_allocation/tests/test_counterfactual.py",
]


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "pytest", "-q", *TESTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    passed = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    summary = tail[-1] if tail else "no output"
    return gate("F-033", Path(__file__).name, passed, summary)


if __name__ == "__main__":
    sys.exit(main())
