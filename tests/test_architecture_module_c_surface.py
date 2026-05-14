"""Regression: Module C methodology artifacts, pipeline paths, and lightweight imports."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MOD_C = _REPO_ROOT / "module_c_forecasting_scenarios"
_SRC = _MOD_C / "src" / "module_c_forecasting_scenarios"

_LEGACY_NOT_SHIPPED = [
    _MOD_C / "src" / "forecast_model.py",
]

_REQUIRED = [
    _MOD_C / "reports" / "C_research_proof_table.md",
    _MOD_C / "METHODOLOGY.md",
    _SRC / "models" / "tracking" / "hierarchical.py",
    _SRC / "pipeline" / "run_all.py",
    _SRC / "data" / "contract_validate.py",
    _MOD_C / "config" / "calibration.yaml",
    _MOD_C / "portfolio" / "quarto" / "post_mortem.qmd",
]


def test_module_c_canonical_paths_and_methodology_artifacts_exist() -> None:
    for legacy in _LEGACY_NOT_SHIPPED:
        assert (
            not legacy.exists()
        ), f"Unexpected legacy-only path (checklist stale): {legacy.relative_to(_REPO_ROOT)}"
    for path in _REQUIRED:
        assert path.is_file(), f"Missing Module C artifact: {path.relative_to(_REPO_ROOT)}"
    proof = (_MOD_C / "reports" / "C_research_proof_table.md").read_text(encoding="utf-8")
    assert len(proof) >= 200, "C_research_proof_table.md unexpectedly short"


def test_module_c_lightweight_import_surface() -> None:
    from module_c_forecasting_scenarios.data.contract_validate import load_contract
    from module_c_forecasting_scenarios.paths import module_config_dir, repo_root

    assert callable(repo_root)
    assert callable(module_config_dir)
    assert callable(load_contract)
    assert (_REPO_ROOT / "schema_contracts").is_dir()
    cfg_dir = module_config_dir()
    assert (cfg_dir / "calibration.yaml").is_file()
