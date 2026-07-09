"""Guardrail: canonical three-module roots (+ shared contract core) match Poetry packages."""

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

# The one sanctioned non-module package: the shared declarative contract
# validator every module gate layers on (issue #64 / IMP-C07).
_SHARED_ROOT = "shared"
_SHARED_INCLUDE = "contract_core"


def _load_poetry_packages() -> list[dict[str, str]]:
    with _PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["packages"]


def _package_src_dir(pkg: dict[str, str]) -> Path:
    assert "include" in pkg and "from" in pkg, pkg
    from_path = (_REPO_ROOT / pkg["from"]).resolve()
    assert from_path.is_dir(), f"Missing package path: {from_path}"
    assert (
        from_path.name == "src"
    ), f"Poetry package 'from' should end with src/, got {pkg['from']!r}"
    py_files = [p for p in from_path.rglob("*.py") if p.is_file()]
    assert len(py_files) >= 1, f"No Python sources under {from_path}"
    return from_path


def test_poetry_packages_point_to_existing_module_roots_with_sources() -> None:
    packages = _load_poetry_packages()
    assert len(packages) == 4, (
        "Expected exactly four Poetry packages: the three modules plus the "
        f"shared {_SHARED_INCLUDE!r} core. Adding another package is an "
        "architecture change — update ARCHITECTURE.md and this guardrail "
        "deliberately."
    )
    roots = {_package_src_dir(pkg).parent.name for pkg in packages}
    assert roots == _EXPECTED_ROOTS | {_SHARED_ROOT}, f"Unexpected package roots {roots}"


def test_shared_root_packages_only_contract_core() -> None:
    shared_includes = {
        pkg["include"]
        for pkg in _load_poetry_packages()
        if (_REPO_ROOT / pkg["from"]).resolve().parent.name == _SHARED_ROOT
    }
    assert shared_includes == {_SHARED_INCLUDE}, (
        f"Unexpected shared packages {shared_includes}; only {_SHARED_INCLUDE!r} "
        "is sanctioned under shared/src"
    )
