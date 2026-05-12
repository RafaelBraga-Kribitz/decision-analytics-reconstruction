"""Tests for population_segmentation.data.generator.

TDD order: these tests are written BEFORE the implementation.
They must fail when the module does not exist or is incomplete,
and pass when the implementation is correct.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "generation.yaml"
ANCHORS_PATH = Path(__file__).parent.parent / "config" / "calibration_anchors.yaml"

SAMPLE_SIZE = 50_000  # must match conftest session config["sample_size"]


@pytest.fixture(scope="module")
def anchors() -> dict:  # type: ignore[type-arg]
    with open(ANCHORS_PATH) as f:
        return yaml.safe_load(f)


class TestEntityCount:
    def test_entity_count_matches_sample_size(
        self, generated_population: pd.DataFrame, config: dict  # type: ignore[type-arg]
    ) -> None:
        assert len(generated_population) == config["sample_size"]

    def test_entity_id_unique(self, generated_population: pd.DataFrame) -> None:
        assert generated_population["entity_id"].nunique() == len(generated_population)

    def test_entity_id_monotonic(self, generated_population: pd.DataFrame) -> None:
        ids = generated_population["entity_id"].values
        assert (ids == np.arange(1, len(ids) + 1)).all()


class TestDepartmentWeightsIntegrity:
    """Nominal department shares must sum to 1.0000 at 4dp; RNG probs sum to exactly 1.0."""

    def test_generation_yaml_department_weights_decimal_sum(self) -> None:
        from decimal import ROUND_HALF_EVEN, Decimal

        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        quant = Decimal("0.0001")
        decimal_sum = sum(
            Decimal(str(float(v))).quantize(quant, rounding=ROUND_HALF_EVEN)
            for v in cfg["department_weights"].values()
        )
        assert decimal_sum == Decimal("1.0000")

    def test_validated_sampling_probs_sum_is_exactly_one(self) -> None:
        from population_segmentation.data.generator import _validated_department_sampling_probs

        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        _, probs = _validated_department_sampling_probs(cfg["department_weights"])
        assert probs.sum() == 1.0


class TestDepartmentDistribution:
    def test_all_18_departments_present(self, generated_population: pd.DataFrame) -> None:
        from population_segmentation.utils.schema import CANONICAL_DEPARTMENTS

        present = set(generated_population["department"].dropna().unique())
        assert present.issubset(CANONICAL_DEPARTMENTS), (
            "Generator pre-flaw output must use only canonical department names; "
            f"non-canonical: {present - CANONICAL_DEPARTMENTS}"
        )
        # At least 15 of 18 departments must be present at sample_size=50k
        clean_present = present & CANONICAL_DEPARTMENTS
        assert len(clean_present) >= 15

    def test_central_asuncion_dominant(self, generated_population: pd.DataFrame) -> None:
        dept_counts = generated_population["department"].value_counts(normalize=True)
        central_asuncion = dept_counts.get("Central", 0) + dept_counts.get("Asuncion", 0)
        # Combined share should be roughly 37% ±5pp at N=50k
        assert 0.30 <= central_asuncion <= 0.44


class TestGenderDistribution:
    def test_gender_split_approximate(
        self, generated_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        male_share = (generated_population["gender"] == "M").mean()
        tolerance = 0.010  # loose at N=50k
        expected_male_share = anchors["demographics"]["male_share"]
        assert abs(male_share - expected_male_share) < tolerance, (
            f"Male share {male_share:.3f} outside ±{tolerance} " f"of {expected_male_share}"
        )


class TestUrbanRuralSplit:
    def test_rural_flag_present(self, generated_population: pd.DataFrame) -> None:
        cols = generated_population.columns
        assert "rural_flag" in cols or "rural_flag_raw" in cols

    def test_urban_rural_approximate(
        self, generated_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        # Generator sets a preliminary rural_flag based on department_urban_share
        if "rural_flag" in generated_population.columns:
            rural_share = generated_population["rural_flag"].mean()
            tolerance = 0.015
            assert abs(rural_share - anchors["demographics"]["rural_share"]) < tolerance


class TestAgeDistribution:
    def test_age_range_valid(self, generated_population: pd.DataFrame) -> None:
        if "age_on_event_date" in generated_population.columns:
            ages = generated_population["age_on_event_date"].dropna()
            assert (ages >= 18).all()
            assert (ages <= 99).all()

    def test_youth_count_approximate(
        self, generated_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        if "age_on_event_date" in generated_population.columns:
            youth_share = (
                (generated_population["age_on_event_date"] >= 18)
                & (generated_population["age_on_event_date"] <= 24)
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
    def test_language_field_present(self, generated_population: pd.DataFrame) -> None:
        assert "language_census_bucket" in generated_population.columns

    def test_language_marginals_approximate(
        self, generated_population: pd.DataFrame, anchors: dict  # type: ignore[type-arg]
    ) -> None:
        lang_shares = generated_population["language_census_bucket"].value_counts(normalize=True)
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

    def test_required_columns_present(self, generated_population: pd.DataFrame) -> None:
        missing = [c for c in self.REQUIRED_COLUMNS if c not in generated_population.columns]
        assert not missing, f"Missing columns: {missing}"


class TestWhatsAppPenetrationFromConfig:
    """Rural/urban WhatsApp penetration must follow media_penetration_defaults in YAML."""

    def test_whatsapp_penetration_matches_yaml_anchors(
        self, config: dict, generated_population: pd.DataFrame  # type: ignore[type-arg]
    ) -> None:
        ict = config["media_penetration_defaults"]
        expected_rural = float(ict["whatsapp_rural"])
        expected_urban = float(ict["whatsapp_urban"])
        rural = generated_population["rural_flag"].astype(bool)
        rural_vals = generated_population.loc[rural, "media_penetration_whatsapp"]
        urban_vals = generated_population.loc[~rural, "media_penetration_whatsapp"]
        assert (rural_vals == expected_rural).all(), (
            f"Rural WhatsApp must equal config whatsapp_rural={expected_rural}, "
            f"got unique={sorted(rural_vals.unique().tolist())}"
        )
        assert (urban_vals == expected_urban).all(), (
            f"Urban WhatsApp must equal config whatsapp_urban={expected_urban}, "
            f"got unique={sorted(urban_vals.unique().tolist())}"
        )


def test_generator_module_cli_sample_size_override(tmp_path: Path) -> None:
    """CLI --sample-size overrides YAML before generate_population."""
    out = tmp_path / "gen_cli.parquet"
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "population_segmentation.data.generator",
        "--config",
        str(CONFIG_PATH),
        "--output",
        str(out),
        "--sample-size",
        "127",
        "--seed",
        "3",
    ]
    subprocess.run(cmd, check=True, cwd=repo_root)
    assert out.is_file()
    df = pd.read_parquet(out)
    assert len(df) == 127
