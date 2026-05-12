"""Tests for population_segmentation.data.cleaner (TDD first)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from population_segmentation.utils.schema import (
    CANONICAL_ENC_SOURCE,
    ENC_SOURCE,
    ENC_SOURCE_RAW,
)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "generation.yaml"


@pytest.fixture(scope="module")
def config() -> dict:  # type: ignore[type-arg]
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = 40_000
    return cfg


@pytest.fixture(scope="module")
def raw_population(config: dict) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    base = generate_population(config, seed=42)
    return inject_flaws(base, config, seed=42)


@pytest.fixture(scope="module")
def cleaned_population(
    raw_population: pd.DataFrame,
    config: dict,
    tmp_path_factory: pytest.TempPathFactory,
) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.cleaner import clean_population

    report_dir = tmp_path_factory.mktemp("qa_reports")
    return clean_population(raw_population, config, qa_report_dir=report_dir)


def test_enc_source_promoted_from_raw_layer(cleaned_population: pd.DataFrame) -> None:
    """Clean output must expose enc_source only; values must match raw generator mix."""
    assert ENC_SOURCE_RAW not in cleaned_population.columns
    assert ENC_SOURCE in cleaned_population.columns
    vals = set(cleaned_population[ENC_SOURCE].dropna().unique())
    assert vals.issubset(CANONICAL_ENC_SOURCE)
    utf8_share = (cleaned_population[ENC_SOURCE] == "utf8").mean()
    assert 0.30 < utf8_share < 0.70, f"unexpected utf8 share after promotion: {utf8_share:.3f}"


def test_cleaner_synthetic_internet_flag_uses_config_rates(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """When internet_access_flag is missing, imputation uses YAML rural/urban rates."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.drop(columns=["internet_access_flag"])
    cfg = {
        **config,
        "media_penetration_defaults": {
            **config["media_penetration_defaults"],
            "internet_access_rural_rate": 0.08,
            "internet_access_urban_rate": 0.92,
        },
    }
    out = clean_population(raw, cfg, qa_report_dir=tmp_path)
    rural = out["rural_flag"].astype(bool)
    assert out.loc[rural, "internet_access_flag"].mean() < 0.15
    assert out.loc[~rural, "internet_access_flag"].mean() > 0.85


def test_cedula_standardized(cleaned_population: pd.DataFrame) -> None:
    assert cleaned_population["cedula"].notna().all()
    assert cleaned_population["cedula"].astype(str).str.match(r"^\d{8}$").all()


def test_department_canonical(cleaned_population: pd.DataFrame) -> None:
    from population_segmentation.utils.schema import CANONICAL_DEPARTMENTS

    vals = set(cleaned_population["department"].dropna().unique())
    assert vals.issubset(CANONICAL_DEPARTMENTS)


def test_municipality_null_rate_below_point_one_percent(cleaned_population: pd.DataFrame) -> None:
    assert cleaned_population["municipality"].isna().mean() < 0.001


def test_gender_normalized(cleaned_population: pd.DataFrame) -> None:
    from population_segmentation.utils.schema import CANONICAL_GENDER

    vals = set(cleaned_population["gender"].dropna().unique())
    assert vals.issubset(CANONICAL_GENDER)


def test_age_range_enforced(cleaned_population: pd.DataFrame) -> None:
    assert cleaned_population["age_on_event_date"].between(18, 115).all()


def test_rural_flag_complete(cleaned_population: pd.DataFrame) -> None:
    assert cleaned_population["rural_flag"].isna().sum() == 0


def test_phone_canonicalized(cleaned_population: pd.DataFrame) -> None:
    assert cleaned_population["phone"].astype(str).str.match(r"^\+595\d{9}$").all()


def test_qa_report_generated(raw_population: pd.DataFrame, config: dict, tmp_path: Path) -> None:  # type: ignore[type-arg]
    from population_segmentation.data.cleaner import clean_population

    clean_population(raw_population, config, qa_report_dir=tmp_path)
    reports = list(tmp_path.glob("qa_report_*.md"))
    assert reports, "Expected qa_report_*.md to be generated"
