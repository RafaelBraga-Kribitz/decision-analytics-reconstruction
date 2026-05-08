"""TDD tests for propensity model (A7/A8/A9/A10 gates)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml


@pytest.fixture(scope="module")
def cfg() -> dict:  # type: ignore[type-arg]
    with open(Path(__file__).parent.parent / "config" / "generation.yaml") as f:
        c = yaml.safe_load(f)
    c["sample_size"] = 15_000
    return c


@pytest.fixture(scope="module")
def anchors() -> dict:  # type: ignore[type-arg]
    with open(Path(__file__).parent.parent / "config" / "calibration_anchors.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def feature_df(cfg: dict) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws
    from population_segmentation.features.behavioral import build_behavioral_features
    from population_segmentation.features.demographic import build_demographic_features
    from population_segmentation.features.reachability import build_reachability_features

    base = generate_population(cfg, seed=42)
    raw = inject_flaws(base, cfg, seed=42)
    clean = clean_population(raw, cfg)
    return build_reachability_features(build_behavioral_features(build_demographic_features(clean)))


def test_propensity_metrics_and_calibration_gates(feature_df: pd.DataFrame, anchors: dict) -> None:  # type: ignore[type-arg]
    from population_segmentation.models.propensity import PropensityModel

    model = PropensityModel(random_state=42)
    out = model.fit_predict(feature_df, anchors)

    assert out["metrics"]["brier_score"] < 0.22  # A7

    assert (
        abs(out["calibration"]["youth_mean"] - anchors["national"]["youth_participation_rate"])
        < 0.005
    )  # A8
    assert (
        abs(out["calibration"]["female_mean"] - anchors["national"]["female_participation_rate"])
        < 0.002
    )  # A9
    assert (
        abs(out["calibration"]["male_mean"] - anchors["national"]["male_participation_rate"])
        < 0.002
    )  # A9

    dept_targets = anchors["department_participation_rates"]
    assert (
        abs(out["calibration"]["dept_means"]["Presidente Hayes"] - dept_targets["Presidente Hayes"])
        < 0.005
    )
    assert (
        abs(out["calibration"]["dept_means"]["Alto Parana"] - dept_targets["Alto Parana"]) < 0.005
    )
    assert abs(out["calibration"]["dept_means"]["Central"] - dept_targets["Central"]) < 0.005
    assert abs(out["calibration"]["dept_means"]["Guaira"] - dept_targets["Guaira"]) < 0.005  # A10
