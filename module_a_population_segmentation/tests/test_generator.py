"""Tests for population_segmentation.data.generator.

TDD order: these tests are written BEFORE the implementation.
They must fail when the module does not exist or is incomplete,
and pass when the implementation is correct.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "generation.yaml"
ANCHORS_PATH = Path(__file__).parent.parent / "config" / "calibration_anchors.yaml"

SAMPLE_SIZE = 50_000  # fast test size; override via config in full runs


@pytest.fixture(scope="module")
def config() -> dict:  # type: ignore[type-arg]
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = SAMPLE_SIZE
    return cfg


@pytest.fixture(scope="module")
def anchors() -> dict:  # type: ignore[type-arg]
    with open(ANCHORS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def raw_population(config: dict) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.generator import generate_population

    return generate_population(config, seed=42)


class TestEntityCount:
    def test_entity_count_matches_sample_size(
        self, raw_population: pd.DataFrame, config: dict  # type: ignore[type-arg]
    ) -> None:
        assert len(raw_population) == config["sample_size"]

    def test_entity_id_unique(self, raw_population: pd.DataFrame) -> None:
        assert raw_population["entity_id"].nunique() == len(raw_population)

    def test_entity_id_monotonic(self, raw_population: pd.DataFrame) -> None:
        ids = raw_population["entity_id"].values
        assert (ids == np.arange(1, len(ids) + 1)).all()


class TestDepartmentDistribution:
    def test_all_18_departments_present(self, raw_population: pd.DataFrame) -> None:
        from population_segmentation.utils.schema import CANONICAL_DEPARTMENTS

        present = set(raw_population["department"].dropna().unique())
        assert present.issubset(
            CANONICAL_DEPARTMENTS | {"Cordilera", "Caaguazu"}
        ), f"Unexpected departments: {present - CANONICAL_DEPARTMENTS}"
        # At least 15 of 18 departments must be present at sample_size=50k
        clean_present = present & CANONICAL_DEPARTMENTS
        assert len(clean_present) >= 15

    def test_central_asuncion_dominant(self, raw_population: pd.DataFrame) -> None:
        dept_counts = raw_population["department"].value_counts(normalize=True)
        central_asuncion = dept_counts.get("Central", 0) + dept_counts.get("Asuncion", 0)
        # Combined share should be roughly 37% ±5pp at N=50k
        assert 0.30 <= central_asuncion <= 0.44


class TestGenderDistribution:
    def test_gender_split_approximate(
        self, raw_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        male_share = (raw_population["gender"] == "M").mean()
        tolerance = 0.010  # loose at N=50k
        expected_male_share = anchors["demographics"]["male_share"]
        assert abs(male_share - expected_male_share) < tolerance, (
            f"Male share {male_share:.3f} outside ±{tolerance} " f"of {expected_male_share}"
        )


class TestUrbanRuralSplit:
    def test_rural_flag_present(self, raw_population: pd.DataFrame) -> None:
        assert "rural_flag" in raw_population.columns or "rural_flag_raw" in raw_population.columns

    def test_urban_rural_approximate(
        self, raw_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        # Generator sets a preliminary rural_flag based on department_urban_share
        if "rural_flag" in raw_population.columns:
            rural_share = raw_population["rural_flag"].mean()
            tolerance = 0.015
            assert abs(rural_share - anchors["demographics"]["rural_share"]) < tolerance


class TestAgeDistribution:
    def test_age_range_valid(self, raw_population: pd.DataFrame) -> None:
        if "age_on_event_date" in raw_population.columns:
            ages = raw_population["age_on_event_date"].dropna()
            assert (ages >= 18).all()
            assert (ages <= 99).all()

    def test_youth_count_approximate(
        self, raw_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        if "age_on_event_date" in raw_population.columns:
            youth_share = (
                (raw_population["age_on_event_date"] >= 18)
                & (raw_population["age_on_event_date"] <= 24)
            ).mean()
            expected = anchors["national"]["youth_count"] / anchors["national"]["entity_count"]
            tolerance = 0.015
            assert abs(youth_share - expected) < tolerance


class TestReproducibility:
    def test_same_seed_produces_same_output(self, config: dict) -> None:  # type: ignore[type-arg]
        from population_segmentation.data.generator import generate_population

        df1 = generate_population(config, seed=42)
        df2 = generate_population(config, seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seed_produces_different_output(self, config: dict) -> None:  # type: ignore[type-arg]
        from population_segmentation.data.generator import generate_population

        df1 = generate_population(config, seed=42)
        df2 = generate_population(config, seed=99)
        # They should differ in content (with overwhelming probability)
        assert not df1["entity_id"].equals(df2["entity_id"]) or not df1["department"].equals(
            df2["department"]
        )


class TestLanguageDistribution:
    def test_language_field_present(self, raw_population: pd.DataFrame) -> None:
        assert "language_census_bucket" in raw_population.columns

    def test_language_marginals_approximate(
        self, raw_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        lang_shares = raw_population["language_census_bucket"].value_counts(normalize=True)
        tolerance = 0.015
        for bucket, expected in anchors["language"].items():
            observed = lang_shares.get(bucket, 0.0)
            assert (
                abs(observed - expected) < tolerance
            ), f"Language '{bucket}': observed {observed:.3f}, expected {expected:.3f} ±{tolerance}"


class TestRequiredColumns:
    REQUIRED_COLUMNS = [
        "entity_id",
        "department",
        "municipality",
        "gender",
        "rural_flag",
        "language_census_bucket",
        "preference_proxy",
        "preference_proxy_strength",
        "internet_access_flag",
        "media_penetration_tv",
        "media_penetration_radio",
        "media_penetration_whatsapp",
        "nbi_stress_prior",
        "structural_dependency_proxy",
    ]

    def test_required_columns_present(self, raw_population: pd.DataFrame) -> None:
        missing = [c for c in self.REQUIRED_COLUMNS if c not in raw_population.columns]
        assert not missing, f"Missing columns: {missing}"
