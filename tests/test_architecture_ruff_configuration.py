"""Regression: Ruff is configured for a clean `ruff check .` on first-party trees."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO / "pyproject.toml"


def test_pyproject_declares_ruff_excludes_for_non_source_trees() -> None:
    """Generated reports and Jupyter sources are excluded from repo-wide Ruff."""
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert "exclude = [" in text, "[tool.ruff] must declare exclude = [...]"
    assert "reports" in text
    assert "**/*.ipynb" in text


# Repo-wide `ruff check .` is covered by `test_architecture_ruff_black_contract.py`.
