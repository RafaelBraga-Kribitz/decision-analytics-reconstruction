"""Regression: Module A production paths exist and pipeline/export surface imports."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MOD_A = _REPO_ROOT / "module_a_population_segmentation"
_SRC = _MOD_A / "src" / "population_segmentation"

# Shipped Module A surfaces (paths relative to _SRC unless noted).
_REQUIRED_UNDER_SRC = [
    _SRC / "data" / "generator.py",
    _SRC / "data" / "raw_injector.py",
    _SRC / "data" / "cleaner.py",
    _SRC / "data" / "validator.py",
    _SRC / "features" / "demographic.py",
    _SRC / "features" / "behavioral.py",
    _SRC / "features" / "reachability.py",
    _SRC / "models" / "segmentation.py",
    _SRC / "models" / "propensity.py",
    _SRC / "evaluation" / "schema_validator.py",
    _SRC / "pipeline" / "export.py",
    _SRC / "pipeline" / "__main__.py",
]

_DASHBOARD = _MOD_A / "app" / "streamlit_dashboard.py"


def test_module_a_required_source_files_exist() -> None:
    for path in _REQUIRED_UNDER_SRC:
        assert path.is_file(), f"Missing Module A source file: {path.relative_to(_REPO_ROOT)}"
    assert (
        _DASHBOARD.is_file()
    ), f"Missing dashboard app — expected {_DASHBOARD.relative_to(_REPO_ROOT)}"


def test_population_segmentation_pipeline_import_surface() -> None:
    from population_segmentation.pipeline import __main__ as main_mod
    from population_segmentation.pipeline import export as export_mod

    assert callable(export_mod.run_export), "run_export must be callable"
    assert hasattr(main_mod, "main"), "pipeline.__main__ should expose main()"


def test_generator_and_raw_injector_have_cli_entry() -> None:
    gen = (_SRC / "data" / "generator.py").read_text(encoding="utf-8")
    raw = (_SRC / "data" / "raw_injector.py").read_text(encoding="utf-8")
    for label, text in (("generator.py", gen), ("raw_injector.py", raw)):
        assert 'if __name__ == "__main__"' in text, f"{label} must define __main__ guard"
        assert "argparse" in text, f"{label} must use argparse for CLI"
