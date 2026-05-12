"""PSI helper tests."""

from __future__ import annotations

import numpy as np
from population_segmentation.evaluation.psi import population_stability_index


def test_psi_zero_when_identical() -> None:
    x = np.random.default_rng(1).random(500)
    psi = population_stability_index(x, x)
    assert psi < 0.01


def test_psi_positive_on_shifted() -> None:
    rng = np.random.default_rng(2)
    exp = rng.beta(2, 5, size=800)
    act = rng.beta(5, 2, size=800)
    psi = population_stability_index(exp, act)
    assert psi > 0.05
