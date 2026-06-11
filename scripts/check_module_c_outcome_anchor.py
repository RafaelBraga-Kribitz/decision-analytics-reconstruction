#!/usr/bin/env python3
"""Verify the m-star outcome anchor is structural in Module C (F-036).

Runs the anchor sensitivity suite: tight anchor pins the terminal posterior
margin to the active series' m-star, unanchored fits follow the polls, the
anchor is series-aware (A|B), and anchor strength behaves monotonically.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

TESTS = ["module_c_forecasting_scenarios/tests/test_outcome_anchor.py"]


def main() -> int:
    env = dict(os.environ, MC_FAST="1")
    proc = subprocess.run(
        ["poetry", "run", "pytest", "-q", *TESTS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=2400,
        env=env,
    )
    passed = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    summary = tail[-1] if tail else "no output"
    return gate("F-036", Path(__file__).name, passed, summary)


if __name__ == "__main__":
    sys.exit(main())
