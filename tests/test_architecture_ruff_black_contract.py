"""Regression: repo-wide Ruff and Black pass (code quality gate)."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_ruff_check_dot_exits_zero() -> None:
    proc = subprocess.run(
        ["poetry", "run", "ruff", "check", "."],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    assert proc.returncode == 0


def test_black_check_dot_exits_zero() -> None:
    proc = subprocess.run(
        ["poetry", "run", "black", "--check", "."],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    assert proc.returncode == 0
