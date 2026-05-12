"""Regression: Module B SPEC and canonical allocator paths exist and import."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MOD_B = _REPO_ROOT / "module_b_resource_allocation"
_SPEC = _MOD_B / "SPECIFICATION.md"
_SRC = _MOD_B / "src" / "module_b_resource_allocation"

_REQUIRED_SOURCES = [
    _SRC / "models" / "allocation.py",
    _SRC / "models" / "allocation_lp.py",
    _SRC / "pipeline" / "run_allocation.py",
]


def test_module_b_specification_and_canonical_solver_paths_exist() -> None:
    assert _SPEC.is_file(), "Missing module_b_resource_allocation/SPECIFICATION.md"
    text = _SPEC.read_text(encoding="utf-8")
    assert len(text) >= 200, "SPECIFICATION.md unexpectedly short"
    assert "build_problem" in text, "SPECIFICATION.md should reference build_problem"
    for path in _REQUIRED_SOURCES:
        assert path.is_file(), f"Missing Module B source: {path.relative_to(_REPO_ROOT)}"


def test_module_b_allocation_import_surface() -> None:
    from module_b_resource_allocation.models.allocation import build_problem, solve

    assert callable(build_problem), "build_problem must be callable"
    assert callable(solve), "solve must be callable"
