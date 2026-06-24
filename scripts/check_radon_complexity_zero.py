#!/usr/bin/env python3
"""Verify high-complexity blocks have been eliminated."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

MAX_CC = 10


def main() -> int:
    proc = subprocess.run(
        ["radon", "cc", "-j", "-n", "C", "--exclude", "governance/_kit/*", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        data = {}
    count = sum(
        1
        for blocks in data.values()
        for block in blocks
        if isinstance(block, dict) and block.get("complexity", 0) > MAX_CC
    )
    return gate("F-008", Path(__file__).name, count == 0, f"radon_complex_blocks={count}")


if __name__ == "__main__":
    sys.exit(main())
