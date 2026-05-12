"""Regression: data/raw, data/interim, data/processed exist with tracked .gitkeep."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_GITIGNORE = _REPO / ".gitignore"

_KEEP_PATHS = (
    _REPO / "data" / "raw" / ".gitkeep",
    _REPO / "data" / "interim" / ".gitkeep",
    _REPO / "data" / "processed" / ".gitkeep",
)


def test_data_stage_directories_have_gitkeep() -> None:
    for p in _KEEP_PATHS:
        assert p.is_file(), f"Expected tracked placeholder file: {p}"


def test_gitignore_negates_data_gitkeep() -> None:
    text = _GITIGNORE.read_text(encoding="utf-8")
    for rel in ("!data/raw/.gitkeep", "!data/interim/.gitkeep", "!data/processed/.gitkeep"):
        assert rel in text, f".gitignore must contain {rel!r} so placeholders are committable"
