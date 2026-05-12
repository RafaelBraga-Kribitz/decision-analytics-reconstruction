"""Regression: CI must use full ``poetry install`` so editable packages are on sys.path."""

from __future__ import annotations

from pathlib import Path

import population_segmentation

import module_b_resource_allocation
import module_c_forecasting_scenarios

_REPO = Path(__file__).resolve().parents[1]
_WORKFLOWS = _REPO / ".github" / "workflows"


def test_github_workflows_forbid_poetry_install_no_root() -> None:
    """Reject ``poetry install --no-root``: it skips the root project on sys.path."""
    assert _WORKFLOWS.is_dir()
    for path in sorted(_WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        assert "poetry install --no-root" not in text, (
            f"{path.name}: must not use poetry install --no-root"
        )


def test_poetry_declared_packages_importable() -> None:
    """Editable roots must import (same failure mode CI hits without root install)."""
    assert module_b_resource_allocation.__spec__ is not None
    assert module_c_forecasting_scenarios.__spec__ is not None
    assert population_segmentation.__spec__ is not None
