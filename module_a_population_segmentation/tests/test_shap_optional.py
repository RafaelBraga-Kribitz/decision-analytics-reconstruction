"""SHAP smoke when explainability extra is installed (rubric parity)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("shap", reason="install poetry with --extras explainability for SHAP")


def test_shap_kernel_explainer_small_regression_shape() -> None:
    import shap
    from sklearn.linear_model import LinearRegression

    rng = np.random.default_rng(0)
    x = rng.standard_normal((40, 5))
    y = x[:, 0] * 0.5 + rng.normal(scale=0.1, size=40)
    model = LinearRegression().fit(x, y)
    explainer = shap.KernelExplainer(model.predict, shap.sample(x, 10))
    sv = explainer.shap_values(x[:3], nsamples=50)
    arr = np.asarray(sv)
    assert arr.shape[0] == 3
    assert arr.shape[1] == 5
