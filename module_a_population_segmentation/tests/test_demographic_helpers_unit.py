"""Unit tests for ``population_segmentation.features.demographic._age_bin``."""

from __future__ import annotations

import pytest
from population_segmentation.features.demographic import _age_bin


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (18, "18_24"),
        (24, "18_24"),
        (25, "25_34"),
        (34, "25_34"),
        (49, "35_49"),
        (64, "50_64"),
        (65, "65_plus"),
        (100, "65_plus"),
    ],
)
def test_age_bin_boundaries(age: int, expected: str) -> None:
    assert _age_bin(age) == expected
