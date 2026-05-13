"""Regression: primary Module A stochastic entry points are seed-stable (line 75 gate)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

_REPO = Path(__file__).resolve().parents[1]
_CONFIG = _REPO / "module_a_population_segmentation" / "config" / "generation.yaml"


@pytest.fixture(scope="module")
def small_generation_config() -> dict:  # type: ignore[type-arg]
    with open(_CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    out = dict(cfg)
    out["sample_size"] = 800
    return out


def test_generate_population_is_reproducible_for_fixed_seed(
    small_generation_config: dict,  # type: ignore[type-arg]
) -> None:
    from population_segmentation.data.generator import generate_population

    a = generate_population(small_generation_config, seed=31415)
    b = generate_population(small_generation_config, seed=31415)
    pd.testing.assert_frame_equal(a, b)


def test_inject_flaws_is_reproducible_for_fixed_seed(
    small_generation_config: dict,  # type: ignore[type-arg]
) -> None:
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    raw = generate_population(small_generation_config, seed=271828)
    a = inject_flaws(raw, small_generation_config, seed=161803)
    b = inject_flaws(raw, small_generation_config, seed=161803)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
    assert a.attrs == b.attrs


def test_clean_population_is_reproducible_for_fixed_seed(
    small_generation_config: dict,  # type: ignore[type-arg]
) -> None:
    from population_segmentation.data.cleaner import clean_population
    from population_segmentation.data.generator import generate_population
    from population_segmentation.data.raw_injector import inject_flaws

    raw = inject_flaws(
        generate_population(small_generation_config, seed=1),
        small_generation_config,
        seed=2,
    )
    a = clean_population(raw, small_generation_config, qa_report_dir=None, seed=999)
    b = clean_population(raw, small_generation_config, qa_report_dir=None, seed=999)
    pd.testing.assert_frame_equal(a, b)


def test_build_segmentation_frame_is_reproducible_for_fixed_random_state() -> None:
    pytest.importorskip("sklearn")
    from population_segmentation.pipeline.models.segmentation import (
        FEATURE_COLUMNS,
        build_segmentation_frame,
    )

    rng = np.random.default_rng(0)
    n = 120
    data: dict[str, object] = {"entity_id": np.arange(1, n + 1, dtype=np.int64)}
    for col in FEATURE_COLUMNS:
        if col in {"rural_flag", "youth_flag", "metro_flag"}:
            data[col] = rng.random(n) > 0.4
        else:
            data[col] = rng.normal(size=n)
    df = pd.DataFrame(data)
    labels_a, metrics_a = build_segmentation_frame(df, k=6, random_state=424242)
    labels_b, metrics_b = build_segmentation_frame(df, k=6, random_state=424242)
    pd.testing.assert_frame_equal(labels_a, labels_b)
    assert metrics_a["silhouette"] == metrics_b["silhouette"]
    assert metrics_a["bootstrap_ari"] == metrics_b["bootstrap_ari"]
    assert metrics_a["noise_rate"] == metrics_b["noise_rate"]
    pd.testing.assert_series_equal(metrics_a["segment_share"], metrics_b["segment_share"])
