"""Tests for population_segmentation.data.validator (TDD first)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

GEN_CONFIG = Path(__file__).parent.parent / "config" / "generation.yaml"
ANCHORS_CONFIG = Path(__file__).parent.parent / "config" / "calibration_anchors.yaml"


@pytest.fixture(scope="module")
def config() -> dict:  # type: ignore[type-arg]
    with open(GEN_CONFIG) as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = 30_000
    return cfg


@pytest.fixture(scope="module")
def cleaned_df(config: dict, tmp_path_factory: pytest.TempPathFactory) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    base = generate_population(config, seed=42)
    raw = inject_flaws(base, config, seed=42)
    out_dir = tmp_path_factory.mktemp("validator_qa")
    return clean_population(raw, config, qa_report_dir=out_dir)


def test_validate_schema_passes(cleaned_df: pd.DataFrame) -> None:
    from population_segmentation.data.validator import validate_schema

    validate_schema(cleaned_df)


def test_validate_anchors_passes(cleaned_df: pd.DataFrame) -> None:
    from population_segmentation.data.validator import validate_calibration_anchors

    with open(ANCHORS_CONFIG) as f:
        anchors = yaml.safe_load(f)
    result = validate_calibration_anchors(cleaned_df, anchors)
    assert result["passed"] is True


def test_raises_on_bad_cedula(cleaned_df: pd.DataFrame) -> None:
    from population_segmentation.data.validator import QAGateFailure, validate_schema

    broken = cleaned_df.copy()
    broken.loc[0, "cedula"] = "ABC"
    with pytest.raises(QAGateFailure):
        validate_schema(broken)


def test_raises_on_missing_department(cleaned_df: pd.DataFrame) -> None:
    from population_segmentation.data.validator import QAGateFailure, validate_schema

    broken = cleaned_df.copy()
    broken.loc[0, "department"] = None
    with pytest.raises(QAGateFailure):
        validate_schema(broken)
