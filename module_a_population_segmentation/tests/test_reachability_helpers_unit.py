"""Unit tests for private helpers in segment reachability aggregate."""

from __future__ import annotations

import pandas as pd
import pytest
from population_segmentation.data.segment_reachability_aggregate import (
    _primary_channel_from_means,
    _primary_reach_channel,
    _region_for,
)


@pytest.mark.parametrize(
    ("dept", "region"),
    [
        ("Asuncion", "ORIENTAL"),
        ("Presidente Hayes", "CHACO"),
        ("Alto Paraguay", "CHACO"),
    ],
)
def test_region_for_chaco_vs_oriental(dept: str, region: str) -> None:
    assert _region_for(dept) == region


@pytest.mark.parametrize(
    ("tv", "radio", "wa", "expected"),
    [
        (0.5, 0.2, 0.1, "tv"),
        (0.1, 0.6, 0.2, "radio"),
        (0.1, 0.1, 0.8, "whatsapp"),
        (0.3, 0.3, 0.3, "direct"),
        (float("nan"), 0.5, 0.5, "direct"),
    ],
)
def test_primary_channel_from_means(tv: float, radio: float, wa: float, expected: str) -> None:
    assert _primary_channel_from_means(tv, radio, wa) == expected


def test_primary_reach_channel_series_row() -> None:
    row = pd.Series(
        {
            "mean_tv_penetration": 0.7,
            "mean_radio_penetration": 0.2,
            "mean_whatsapp_penetration": 0.1,
        }
    )
    assert _primary_reach_channel(row) == "tv"
