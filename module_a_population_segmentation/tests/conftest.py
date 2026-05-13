"""Shared pytest fixtures for Module A (single config load per session)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "generation.yaml"
SAMPLE_SIZE = 50_000


@pytest.fixture(scope="session")
def config() -> dict:  # type: ignore[type-arg]
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["sample_size"] = SAMPLE_SIZE
    return cfg


@pytest.fixture(scope="session")
def generated_population(config: dict) -> pd.DataFrame:  # type: ignore[type-arg]
    """Synthetic population from the generator only (no flaw injection)."""
    from population_segmentation.data.generator import generate_population

    return generate_population(config, seed=42)


@pytest.fixture(scope="session")
def clean_population(generated_population: pd.DataFrame) -> pd.DataFrame:
    """Pre-flaw baseline rows — same as ``generated_population`` (inject input)."""
    return generated_population


@pytest.fixture(scope="session")
def raw_population(config: dict, clean_population: pd.DataFrame) -> pd.DataFrame:  # type: ignore[type-arg]
    from population_segmentation.data.raw_injector import inject_flaws

    return inject_flaws(clean_population, config, seed=42)
