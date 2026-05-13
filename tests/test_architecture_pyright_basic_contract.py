"""Regression: Pyright basic mode clean on Makefile typecheck roots."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_pyright_basic_on_module_a_and_b_src_exits_zero() -> None:
    """Matches root Makefile ``typecheck`` target (Module A + B ``src/`` only)."""
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "pyright",
            "module_a_population_segmentation/src",
            "module_b_resource_allocation/src",
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    assert proc.returncode == 0
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert "0 errors" in combined, f"expected pyright summary with 0 errors, got:\n{combined}"
