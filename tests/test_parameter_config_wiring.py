"""Regression: config values loaded from YAML files match parameter_registry.yaml.

Each test verifies that a constant exported by a module equals the value in its
canonical source config file. Any drift between the config file and module-level
constants fails here before it reaches production.

Tests are intentionally fast (no pymc/arviz sampling) — they read YAML and import
constants.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]

# ──────────────────────────────────────────────────────────────────────────────
# Config file paths
# ──────────────────────────────────────────────────────────────────────────────
_SAMPLER_CFG = _REPO / "module_c_forecasting_scenarios" / "config" / "pymc_sampler.yaml"
_BUDGET_CFG = _REPO / "module_b_resource_allocation" / "config" / "budget_envelope.yaml"
_MODEL_PARAMS_CFG = _REPO / "module_a_population_segmentation" / "config" / "model_params.yaml"
_CALIBRATION_CFG = (
    _REPO / "module_a_population_segmentation" / "config" / "calibration_anchors.yaml"
)
_REGISTRY = _REPO / "docs" / "parameter_registry.yaml"


def _yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


# ──────────────────────────────────────────────────────────────────────────────
# Module C: shared config loader
# ──────────────────────────────────────────────────────────────────────────────


def test_module_c_shared_config_loader_returns_dict() -> None:
    from module_c_forecasting_scenarios.config import load_sampler_config

    cfg = load_sampler_config()
    assert isinstance(cfg, dict), "load_sampler_config() must return a dict"
    assert "hdi_prob" in cfg, "pymc_sampler.yaml must contain hdi_prob"
    assert "predictive_seed" in cfg, "pymc_sampler.yaml must contain predictive_seed"


def test_module_c_hdi_prob_loaded_from_config() -> None:
    """HDI_PROB in hierarchical.py must equal pymc_sampler.yaml hdi_prob."""
    yaml_value = float(_yaml(_SAMPLER_CFG)["hdi_prob"])
    # Import without triggering heavy pymc/arviz — read the module-level constant.
    from module_c_forecasting_scenarios.models.tracking.hierarchical import HDI_PROB

    assert (
        abs(HDI_PROB - yaml_value) < 1e-9
    ), f"hierarchical.HDI_PROB={HDI_PROB} != pymc_sampler.yaml hdi_prob={yaml_value}"


def test_module_c_hdi_prob_exit_model_synced() -> None:
    """HDI_PROB in exit_model.py must equal pymc_sampler.yaml hdi_prob."""
    yaml_value = float(_yaml(_SAMPLER_CFG)["hdi_prob"])
    from module_c_forecasting_scenarios.models.exit.exit_model import HDI_PROB

    assert (
        abs(HDI_PROB - yaml_value) < 1e-9
    ), f"exit_model.HDI_PROB={HDI_PROB} != pymc_sampler.yaml hdi_prob={yaml_value}"


def test_module_c_hdi_prob_heatmap_synced() -> None:
    """_HDI_PROB in heatmap.py must equal pymc_sampler.yaml hdi_prob."""
    yaml_value = float(_yaml(_SAMPLER_CFG)["hdi_prob"])
    from module_c_forecasting_scenarios.geo.heatmap import _HDI_PROB

    assert (
        abs(_HDI_PROB - yaml_value) < 1e-9
    ), f"heatmap._HDI_PROB={_HDI_PROB} != pymc_sampler.yaml hdi_prob={yaml_value}"


def test_module_c_predictive_seed_loaded_from_config() -> None:
    """_PREDICTIVE_SEED in walk_forward.py must equal pymc_sampler.yaml predictive_seed."""
    yaml_value = int(_yaml(_SAMPLER_CFG)["predictive_seed"])
    from module_c_forecasting_scenarios.validation.walk_forward import (
        _PREDICTIVE_SEED,
    )

    assert yaml_value == _PREDICTIVE_SEED, (
        f"walk_forward._PREDICTIVE_SEED={_PREDICTIVE_SEED} "
        f"!= pymc_sampler.yaml predictive_seed={yaml_value}"
    )


def test_heatmap_does_not_import_from_tracking_hierarchical() -> None:
    """heatmap.py must NOT import from tracking.hierarchical (avoids pulling in pymc)."""
    heatmap_src = (
        _REPO
        / "module_c_forecasting_scenarios"
        / "src"
        / "module_c_forecasting_scenarios"
        / "geo"
        / "heatmap.py"
    )
    source = heatmap_src.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "tracking.hierarchical" not in node.module, (
                "heatmap.py imports from tracking.hierarchical — "
                "use module_c_forecasting_scenarios.config instead "
                "to avoid pulling in pymc/arviz in geo code"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Module B: budget constants
# ──────────────────────────────────────────────────────────────────────────────


def test_module_b_campaign_budget_loaded_from_config() -> None:
    """CAMPAIGN_BUDGET_USD must equal budget_envelope.yaml budget.total_envelope_usd."""
    yaml_value = float(_yaml(_BUDGET_CFG)["budget"]["total_envelope_usd"])
    from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD

    assert abs(CAMPAIGN_BUDGET_USD - yaml_value) < 1e-2, (
        f"constants.CAMPAIGN_BUDGET_USD={CAMPAIGN_BUDGET_USD} "
        f"!= budget_envelope.yaml budget.total_envelope_usd={yaml_value}"
    )


def test_module_b_budget_tolerance_loaded_from_config() -> None:
    yaml_value = float(_yaml(_BUDGET_CFG)["budget"]["tolerance_pct"])
    from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_TOLERANCE

    assert abs(CAMPAIGN_BUDGET_TOLERANCE - yaml_value) < 1e-9


def test_module_b_coverage_lower_bound_loaded_from_config() -> None:
    yaml_value = float(_yaml(_BUDGET_CFG)["budget"]["coverage_lower_bound_pct"])
    from module_b_resource_allocation.constants import COVERAGE_LOWER_BOUND_PCT

    assert abs(COVERAGE_LOWER_BOUND_PCT - yaml_value) < 1e-9


def test_module_b_bcp_corridor_loaded_from_config() -> None:
    yaml_value = float(_yaml(_BUDGET_CFG)["budget"]["bcp_corridor_max_pct"])
    from module_b_resource_allocation.constants import BCP_CORRIDOR_MAX_PCT

    assert abs(BCP_CORRIDOR_MAX_PCT - yaml_value) < 1e-9


def test_module_b_fx_band_loaded_from_config() -> None:
    yaml_value = float(_yaml(_BUDGET_CFG)["budget"]["fx_band_max_pct_vs_bcp"])
    from module_b_resource_allocation.constants import FX_BAND_MAX_PCT_VS_BCP

    assert abs(FX_BAND_MAX_PCT_VS_BCP - yaml_value) < 1e-9


# ──────────────────────────────────────────────────────────────────────────────
# Module A: segmentation model params
# ──────────────────────────────────────────────────────────────────────────────


def test_module_a_kmeans_default_k_loaded_from_config() -> None:
    """KMeansSegmenter.k default must equal model_params.yaml kmeans.default_k."""
    yaml_value = int(_yaml(_MODEL_PARAMS_CFG)["kmeans"]["default_k"])
    from population_segmentation.pipeline.models.segmentation import KMeansSegmenter

    default_k = KMeansSegmenter().k
    assert (
        default_k == yaml_value
    ), f"KMeansSegmenter().k={default_k} != model_params.yaml kmeans.default_k={yaml_value}"


def test_module_a_kmeans_random_state_loaded_from_config() -> None:
    yaml_value = int(_yaml(_MODEL_PARAMS_CFG)["kmeans"]["random_state"])
    from population_segmentation.pipeline.models.segmentation import KMeansSegmenter

    assert KMeansSegmenter().random_state == yaml_value


def test_module_a_pca_n_components_loaded_from_config() -> None:
    """_matrix() default n_pca_components must equal model_params.yaml pca.n_components."""
    yaml_value = int(_yaml(_MODEL_PARAMS_CFG)["pca"]["n_components"])
    # Directly inspect _MODEL_PARAMS to avoid instantiating a DataFrame.
    from population_segmentation.pipeline.models.segmentation import _MODEL_PARAMS

    loaded = int(_MODEL_PARAMS.get("pca", {}).get("n_components", -1))
    assert loaded == yaml_value, (
        f"segmentation._MODEL_PARAMS pca.n_components={loaded} "
        f"!= model_params.yaml pca.n_components={yaml_value}"
    )


def test_module_a_pca_random_state_loaded_from_config() -> None:
    yaml_value = int(_yaml(_MODEL_PARAMS_CFG)["pca"]["random_state"])
    from population_segmentation.pipeline.models.segmentation import _MODEL_PARAMS

    loaded = int(_MODEL_PARAMS.get("pca", {}).get("random_state", -1))
    assert loaded == yaml_value


def test_module_a_model_params_loaded_once_at_module_level() -> None:
    """_MODEL_PARAMS must be a dict (loaded at import time, not per-call)."""
    from population_segmentation.pipeline.models.segmentation import _MODEL_PARAMS

    assert isinstance(_MODEL_PARAMS, dict), "_MODEL_PARAMS must be a dict"
    assert "pca" in _MODEL_PARAMS, "_MODEL_PARAMS must contain pca section"
    assert "kmeans" in _MODEL_PARAMS, "_MODEL_PARAMS must contain kmeans section"


# ──────────────────────────────────────────────────────────────────────────────
# Parameter registry: registry file is valid YAML and references real config files
# ──────────────────────────────────────────────────────────────────────────────


def test_parameter_registry_is_valid_yaml() -> None:
    registry = _yaml(_REGISTRY)
    assert isinstance(registry, dict), "parameter_registry.yaml must parse to a dict"
    assert "module_c_pymc_sampler" in registry
    assert "module_b_budget" in registry
    assert "module_a_pca" in registry
    assert "module_a_kmeans" in registry
    assert "verified_outcome_anchors" in registry


def test_parameter_registry_source_files_exist() -> None:
    registry = _yaml(_REGISTRY)
    sections = [
        "module_c_pymc_sampler",
        "module_b_budget",
        "module_a_pca",
        "module_a_kmeans",
        "verified_outcome_anchors",
    ]
    missing: list[str] = []
    for section in sections:
        block = registry.get(section, {})
        if not isinstance(block, dict):
            continue
        for param, meta in block.items():
            if not isinstance(meta, dict):
                continue
            src = meta.get("source_file")
            if src and not (_REPO / src).exists():
                missing.append(f"{section}.{param}: {src}")
    assert not missing, "Registry source_files not found:\n" + "\n".join(missing)
