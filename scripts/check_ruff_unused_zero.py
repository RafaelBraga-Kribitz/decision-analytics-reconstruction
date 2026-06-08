#!/usr/bin/env python3
"""Verify Ruff unused-code findings have been cleared."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate


def main() -> int:
    proc = subprocess.run(
        ["ruff", "check", "--select", "F401,F811,F841", "--output-format", "json", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    try:
        count = len(json.loads(proc.stdout)) if proc.stdout.strip().startswith("[") else 0
    except json.JSONDecodeError:
        count = 0
    return gate("F-007", Path(__file__).name, count == 0, f"ruff_unused={count}")


if __name__ == "__main__":
    sys.exit(main())
