#!/usr/bin/env python3
"""Verification script for F-037: MILP objective equals reported contacts.

Runs the objective-identity test module, which solves the baseline MILP and
asserts the optimizer's objective value matches the post-solve reported
persuasion-adjusted contacts within 0.5% (plus PL-construction invariants).

Exit 0 with [PASS] when the gate holds.
"""

from __future__ import annotations

import subprocess
import sys

TEST_TARGET = "module_b_resource_allocation/tests/test_objective_identity.py"


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "pytest", TEST_TARGET, "-q", "--no-header", "-p", "no:warnings"],
        capture_output=True,
        text=True,
    )
    tail = "\n".join(proc.stdout.strip().splitlines()[-5:])
    if proc.returncode == 0:
        print(tail)
        print("[PASS] F-037: MILP objective is identity-consistent with reported contacts.")
        return 0
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    print("[FAIL] F-037: objective-identity gate failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
