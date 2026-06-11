#!/usr/bin/env python3
"""Verification script for F-039: profile-derived segment labels.

Runs the interpretation test module, which fits the real segmentation
pipeline and asserts that every canonical segment name is earned by the
content of the cluster carrying it (bijection, determinism, and per-label
semantic guarantees).

Exit 0 with [PASS] when the gate holds.
"""

from __future__ import annotations

import subprocess
import sys

TEST_TARGET = "module_a_population_segmentation/tests/test_segment_label_interpretation.py"


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "pytest", TEST_TARGET, "-q", "--no-header", "-p", "no:warnings"],
        capture_output=True,
        text=True,
    )
    tail = "\n".join(proc.stdout.strip().splitlines()[-5:])
    if proc.returncode == 0:
        print(tail)
        print("[PASS] F-039: segment labels are profile-derived and interpretation-tested.")
        return 0
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    print("[FAIL] F-039: segment label interpretation gate failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
