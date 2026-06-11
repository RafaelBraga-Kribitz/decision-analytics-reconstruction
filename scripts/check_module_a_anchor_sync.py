#!/usr/bin/env python3
"""Verify Module A anchor/schema/model-card synchronization (F-035).

Runs the anchor sync tests: schema contract ENFORCED gates must equal the
config anchors, informational gates must match national anchors, and the
model card must quote the current verified values.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

TESTS = ["module_a_population_segmentation/tests/test_anchor_schema_sync.py"]


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "pytest", "-q", *TESTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    passed = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    summary = tail[-1] if tail else "no output"
    return gate("F-035", Path(__file__).name, passed, summary)


if __name__ == "__main__":
    sys.exit(main())
