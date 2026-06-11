#!/usr/bin/env python3
"""Verification script for F-038: Module B ingests Module A artifacts.

Runs the A→B ingestion test module, which asserts that:

* measured Module A penetration overrides YAML reach-cap priors
  (provenance MODULE_A) for the channels Module A measures,
* department participation propensity populates the MILP persuasion weight,
* the bridge degrades gracefully when the artifact is absent, and
* the real exported artifact (when present) is actually consumed.

Exit 0 with [PASS] when the gate holds.
"""

from __future__ import annotations

import subprocess
import sys

TEST_TARGET = "module_b_resource_allocation/tests/test_module_a_ingestion.py"


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "pytest", TEST_TARGET, "-q", "--no-header", "-p", "no:warnings"],
        capture_output=True,
        text=True,
    )
    tail = "\n".join(proc.stdout.strip().splitlines()[-5:])
    if proc.returncode == 0:
        print(tail)
        print("[PASS] F-038: Module B consumes Module A reachability/propensity artifacts.")
        return 0
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    print("[FAIL] F-038: A→B ingestion gate failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
