"""Unit tests for private helpers in ``population_segmentation.data.cleaner``."""

from __future__ import annotations

import pandas as pd
import pytest
from population_segmentation.data.cleaner import (
    _LANGUAGE_IMPUTATION_KEYS,
    _language_imputation_labels_and_probs,
    _normalize_dob,
)


def test_language_imputation_labels_order_and_uniform_fallback() -> None:
    labels, probs = _language_imputation_labels_and_probs({})
    assert labels == list(_LANGUAGE_IMPUTATION_KEYS)
    assert probs.sum() == pytest.approx(1.0)
    assert (probs == 1.0 / len(_LANGUAGE_IMPUTATION_KEYS)).all()


def test_language_imputation_normalises_nonzero_priors() -> None:
    cfg = {
        "language_priors": {
            "guarani_only": 0.5,
            "spanish_only": 0.5,
            "jopara_bilingual": 0.0,
            "other": 0.0,
        }
    }
    labels, probs = _language_imputation_labels_and_probs(cfg)
    assert labels == list(_LANGUAGE_IMPUTATION_KEYS)
    gi = labels.index("guarani_only")
    si = labels.index("spanish_only")
    assert probs[gi] == pytest.approx(0.5)
    assert probs[si] == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("15/03/1990", "15/03/1990"),
        ("03/15/1990", "15/03/1990"),
        ("bad", "01/01/1980"),
        ("1/2/3", "01/01/1980"),
    ],
)
def test_normalize_dob_parsing(raw: str, expected: str) -> None:
    s = pd.Series([raw])
    out = _normalize_dob(s)
    assert out.iloc[0] == expected
