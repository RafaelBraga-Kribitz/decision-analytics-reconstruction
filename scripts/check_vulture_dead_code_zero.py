#!/usr/bin/env python3
"""Verify high-confidence Vulture dead-code findings have been cleared."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def main() -> int:
    proc = subprocess.run(
        ["vulture", ".", "--min-confidence", "80"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = proc.stdout + proc.stderr
    count = sum(1 for line in output.splitlines() if ":" in line and "unused" in line.lower())
    return gate("F-009", Path(__file__).name, count == 0, f"vulture_dead_code={count}")


if __name__ == "__main__":
    sys.exit(main())
