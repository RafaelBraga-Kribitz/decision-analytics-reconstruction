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


def test_cleaner_synthetic_rural_flag_uses_department_urban_share(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """Absent rural_flag is imputed per department from department_urban_share (F-087)."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.drop(columns=["rural_flag"])
    out = clean_population(raw, config, qa_report_dir=tmp_path, seed=123)
    rural_by_dept = out.groupby("department")["rural_flag"].agg(["mean", "size"])
    for dept, urban in config["department_urban_share"].items():
        if dept not in rural_by_dept.index or rural_by_dept.loc[dept, "size"] < 400:
            continue
        # Binomial noise at n >= 400 is < 2.5 pp; allow 6 pp.
        assert abs(rural_by_dept.loc[dept, "mean"] - (1.0 - urban)) < 0.06, dept
    assert rural_by_dept.loc["Asuncion", "mean"] == 0.0  # urban share 1.00
    report = next(tmp_path.glob("qa_report_*.md")).read_text(encoding="utf-8")
    assert "rural_flag imputed per department urban share" in report


def test_cleaner_rural_flag_falls_back_to_national_anchor(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """Departments without an urban share use cleaner_synthetic_defaults.rural_flag_true_rate."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.drop(columns=["rural_flag"])
    cfg = {
        **config,
        "department_urban_share": {},
        "cleaner_synthetic_defaults": {
            **(config.get("cleaner_synthetic_defaults") or {}),
            "rural_flag_true_rate": 0.95,
        },
    }
    out = clean_population(raw, cfg, qa_report_dir=tmp_path, seed=123)
    assert out["rural_flag"].astype(bool).mean() > 0.88


def test_malformed_dob_is_flagged_and_counted(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """Malformed DOBs get the fallback date and dob_imputed=True; QA report counts them."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.copy()
    bad = raw.index[:25]
    raw.loc[bad, "dob"] = "not-a-date"
    out = clean_population(raw, config, qa_report_dir=tmp_path, seed=123)
    flagged = out.loc[out["entity_id"].isin(raw.loc[bad, "entity_id"])]
    assert flagged["dob_imputed"].all()
    assert (flagged["dob"] == "01/01/1980").all()
    assert out["dob_imputed"].sum() >= 25
    report = next(tmp_path.glob("qa_report_*.md")).read_text(encoding="utf-8")
    assert "DOB imputed with 01/01/1980 fallback" in report
    assert "before clamping" in report


def test_cleaner_synthetic_language_respects_yaml_priors(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """When language_census_bucket is absent, labels are drawn from normalised language_priors."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.drop(columns=["language_census_bucket"])
    cfg = {
        **config,
        "language_priors": {
            "jopara_bilingual": 1.0,
            "guarani_only": 0.0,
            "spanish_only": 0.0,
            "other": 0.0,
        },
    }
    out = clean_population(raw, cfg, qa_report_dir=tmp_path, seed=7)
    assert (out["language_census_bucket"] == "jopara_bilingual").all()


def test_cleaner_synthetic_structural_dependency_respects_yaml_prior(
    raw_population: pd.DataFrame, config: dict, tmp_path: Path  # type: ignore[type-arg]
) -> None:
    """When structural_dependency_proxy is absent, rate comes from cleaner_synthetic_defaults."""
    from population_segmentation.data.cleaner import clean_population

    raw = raw_population.drop(columns=["structural_dependency_proxy"])
    cfg = {
        **config,
        "cleaner_synthetic_defaults": {
            **(config.get("cleaner_synthetic_defaults") or {}),
            "structural_dependency_true_rate": 0.97,
        },
    }
    out = clean_population(raw, cfg, qa_report_dir=tmp_path, seed=99)
    assert out["structural_dependency_proxy"].astype(bool).mean() > 0.92


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
