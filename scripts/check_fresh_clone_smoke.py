#!/usr/bin/env python3
"""Fresh-clone readiness smoke (Sprint Phase 8).

Verifies the repo exposes the documented release path without requiring an
actual git clone. Run from repository root after ``poetry install``.

Exits 0 with [PASS] when structural gates are present.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _governance_check import REPO_ROOT, gate

REQUIRED_PATHS = (
    "poetry.lock",
    "pyproject.toml",
    "Makefile",
    "CONTRIBUTING.md",
    "reports/NUMERIC_SSOT.md",
    "reports/golden_metrics.json",
    "scripts/check_numeric_ssot.py",
    "scripts/check_pipeline_golden_metrics.py",
)

MAKEFILE_TARGETS = ("test", "verify", "pipeline-full", "graphify")


def main() -> int:
    gaps: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (REPO_ROOT / rel).is_file():
            gaps.append(f"missing {rel}")

    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8", errors="replace")
    for target in MAKEFILE_TARGETS:
        if f"{target}:" not in makefile:
            gaps.append(f"Makefile missing target {target}")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_golden_metrics.py", "-q", "-p", "no:warnings"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 5):  # 5 = all skipped (no pipeline artifacts)
        gaps.append("golden_metrics tests failed unexpectedly")

    ok = not gaps
    return gate(
        "fresh-clone-smoke",
        Path(__file__).name,
        ok,
        "; ".join(gaps) if gaps else "release path artifacts and Makefile targets present",
    )


if __name__ == "__main__":
    sys.exit(main())
