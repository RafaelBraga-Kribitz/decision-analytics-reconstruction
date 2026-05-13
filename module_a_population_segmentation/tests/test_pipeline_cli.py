"""Tests for ``python -m population_segmentation.pipeline`` entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_pipeline_module_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "population_segmentation.pipeline", "-h"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "Module A end-to-end" in r.stdout or "generation" in r.stdout


def test_pipeline_main_returns_nonzero_when_config_missing(tmp_path: Path) -> None:
    from population_segmentation.pipeline.__main__ import main

    assert main(["--config", str(tmp_path / "nope.yaml")]) == 2
