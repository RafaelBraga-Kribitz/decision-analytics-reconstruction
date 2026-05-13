"""Unit tests for ``population_segmentation.pipeline.models.segmentation._matrix``."""

from __future__ import annotations

import numpy as np
import pandas as pd
from population_segmentation.pipeline.models.segmentation import FEATURE_COLUMNS, _matrix


def test_matrix_shape_and_finite() -> None:
    rng = np.random.default_rng(0)
    n = 30
    data = {c: rng.normal(size=n) for c in FEATURE_COLUMNS}
    df = pd.DataFrame(data)
    x = _matrix(df, n_pca_components=5)
    assert x.shape == (n, 5)
    assert np.all(np.isfinite(x))
