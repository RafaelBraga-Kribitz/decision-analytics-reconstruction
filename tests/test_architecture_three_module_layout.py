"""Guardrail: canonical three-module roots match Poetry package."""

from __future__ import annotations

import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

_EXPECTED_ROOTS = frozenset(
    {
        "module_a_population_segmentation",
        "module_b_resource_allocation",
        "module_c_forecasting_scenarios",
    }
)


def _load_poetry_packages() -> list[dict[str, str]]:
    with _PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["packages"]


def test_poetry_packages_point_to_existing_module_roots_with_sources() -> None:
    packages = _load_poetry_packages()
    assert len(packages) == 3, "Expected exactly three Poetry packages (three modules)."

    roots: set[str] = set()
    for pkg in packages:
        assert "include" in pkg and "from" in pkg, pkg
        from_rel = pkg["from"]
        from_path = (_REPO_ROOT / from_rel).resolve()
        assert from_path.is_dir(), f"Missing package path: {from_path}"
        assert (
            from_path.name == "src"
        ), f"Poetry package 'from' should end with src/, got {from_rel!r}"
        roots.add(from_path.parent.name)
        py_files = [p for p in from_path.rglob("*.py") if p.is_file()]
        assert len(py_files) >= 1, f"No Python sources under {from_path}"

    assert roots == _EXPECTED_ROOTS, f"Unexpected module roots {roots}; expected {_EXPECTED_ROOTS}"
