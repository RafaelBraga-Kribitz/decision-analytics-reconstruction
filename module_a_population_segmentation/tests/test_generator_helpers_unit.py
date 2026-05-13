"""Unit tests for private helpers in ``population_segmentation.data.generator``.

Integration coverage for ``generate_population`` lives in ``test_generator.py``.
"""

from __future__ import annotations

import numpy as np
import pytest
from population_segmentation.data.generator import (
    _DEFAULT_ENC_SOURCE_PROBS,
    _DEFAULT_STRUCT_ELEVATED_DEPTS,
    _MAIN_MUNICIPALITIES,
    _assign_language,
    _assign_municipalities,
    _elevated_departments_frozenset,
    _enc_source_labels_and_probs,
    _generator_dept_media_nbi_tables,
    _nbi_urban_stress_from_rural,
    _rake_binary,
    _rake_categorical,
)
from population_segmentation.utils.seeds import make_rng


def _minimal_generator_dept_media_nbi() -> dict[str, object]:
    return {
        "tv_by_department": {"Central": 0.9},
        "radio_by_department": {"Central": 0.8},
        "nbi_rural_stress_by_department": {"Central": 0.5},
        "nbi_urban_from_rural": {"floor": 0.1, "scale": 0.35},
        "nbi_noise_std": 0.03,
        "nbi_rural_unknown_department": 0.659,
        "nbi_urban_unknown_department": 0.252,
    }


@pytest.mark.parametrize(
    ("floor", "scale", "rural", "expected_central"),
    [
        (0.1, 0.35, {"Central": 0.5}, max(0.1, 0.5 * 0.35)),
        (0.2, 0.5, {"Central": 0.3}, max(0.2, 0.3 * 0.5)),
        (0.5, 0.1, {"Central": 0.2}, max(0.5, 0.2 * 0.1)),
    ],
)
def test_nbi_urban_stress_from_rural_formula(
    floor: float, scale: float, rural: dict[str, float], expected_central: float
) -> None:
    out = _nbi_urban_stress_from_rural(rural, floor, scale)
    assert out["Central"] == pytest.approx(expected_central)


def test_elevated_departments_frozenset_empty_or_missing_uses_default() -> None:
    assert _elevated_departments_frozenset({}) == _DEFAULT_STRUCT_ELEVATED_DEPTS
    assert (
        _elevated_departments_frozenset({"elevated_departments": []})
        == _DEFAULT_STRUCT_ELEVATED_DEPTS
    )


def test_elevated_departments_frozenset_non_empty_list() -> None:
    raw = ["Central", "Alto Parana"]
    assert _elevated_departments_frozenset({"elevated_departments": raw}) == frozenset(
        {"Central", "Alto Parana"}
    )


@pytest.mark.parametrize(
    ("dist", "expected_sum"),
    [
        ({}, 1.0),
        ({"windows1252": 0.0, "utf8": 0.0, "unknown": 0.0}, 1.0),
        ({"windows1252": 1.0, "utf8": 1.0, "unknown": 1.0}, 1.0),
    ],
)
def test_enc_source_labels_and_probs_empty_or_zero_sum_uses_default(
    dist: dict[str, float], expected_sum: float
) -> None:
    labels, probs = _enc_source_labels_and_probs({"generator_enc_source_raw_distribution": dist})
    assert labels == ["windows1252", "utf8", "unknown"]
    assert probs.sum() == pytest.approx(expected_sum)
    if not dist or sum(dist.values()) <= 0:
        assert tuple(float(p) for p in probs) == pytest.approx(_DEFAULT_ENC_SOURCE_PROBS)


def test_enc_source_labels_and_probs_skewed_normalises() -> None:
    dist = {"windows1252": 9.0, "utf8": 1.0, "unknown": 0.0}
    labels, probs = _enc_source_labels_and_probs({"generator_enc_source_raw_distribution": dist})
    assert labels == ["windows1252", "utf8", "unknown"]
    assert probs.sum() == pytest.approx(1.0)
    assert probs[0] == pytest.approx(0.9)
    assert probs[1] == pytest.approx(0.1)
    assert probs[2] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("config", "match_substring"),
    [
        ({}, "generator_dept_media_nbi"),
        ({"generator_dept_media_nbi": {}}, "tv_by_department"),
        (
            {
                "generator_dept_media_nbi": {
                    "tv_by_department": {},
                    "radio_by_department": {"Central": 0.8},
                    "nbi_rural_stress_by_department": {"Central": 0.5},
                }
            },
            "tv_by_department",
        ),
        (
            {
                "generator_dept_media_nbi": {
                    "tv_by_department": {"Central": 0.9},
                    "radio_by_department": {},
                    "nbi_rural_stress_by_department": {"Central": 0.5},
                }
            },
            "radio_by_department",
        ),
        (
            {
                "generator_dept_media_nbi": {
                    "tv_by_department": {"Central": 0.9},
                    "radio_by_department": {"Central": 0.8},
                    "nbi_rural_stress_by_department": {},
                }
            },
            "nbi_rural_stress_by_department",
        ),
    ],
)
def test_generator_dept_media_nbi_tables_keyerror(config: dict, match_substring: str) -> None:
    with pytest.raises(KeyError, match=match_substring):
        _generator_dept_media_nbi_tables(config)


def test_generator_dept_media_nbi_tables_happy_path_minimal() -> None:
    cfg = {"generator_dept_media_nbi": _minimal_generator_dept_media_nbi()}
    tv, radio, nbi_r, nbi_u, noise_std, rural_fb, urban_fb = _generator_dept_media_nbi_tables(cfg)
    assert tv == {"Central": 0.9}
    assert radio == {"Central": 0.8}
    assert nbi_r == {"Central": 0.5}
    assert nbi_u["Central"] == pytest.approx(max(0.1, 0.5 * 0.35))
    assert noise_std == pytest.approx(0.03)
    assert rural_fb == pytest.approx(0.659)
    assert urban_fb == pytest.approx(0.252)


def test_rake_binary_exact_mean_small_deterministic_case() -> None:
    rng = make_rng(12345)
    arr = np.zeros(100, dtype=bool)
    out = _rake_binary(arr, 0.2, rng)
    assert out.mean() == pytest.approx(0.2)
    assert out.sum() == 20


def test_rake_binary_same_seed_reproducible() -> None:
    base = np.zeros(500, dtype=bool)
    a = _rake_binary(base.copy(), 0.35, make_rng(7))
    b = _rake_binary(base.copy(), 0.35, make_rng(7))
    np.testing.assert_array_equal(a, b)


def test_rake_categorical_marginals_large_n() -> None:
    rng = make_rng(99)
    n = 5000
    labels = ["a", "b", "c", "d"]
    arr = rng.choice(labels, size=n)
    targets = {"a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4}
    out = _rake_categorical(arr, targets, rng)
    for lab, p in targets.items():
        assert (out == lab).mean() == pytest.approx(p, abs=0.02)


def test_rake_categorical_same_seed_reproducible() -> None:
    rng_a = make_rng(42)
    rng_b = make_rng(42)
    arr = np.array(["x"] * 200 + ["y"] * 200)
    targets = {"x": 0.25, "y": 0.75}
    out_a = _rake_categorical(arr.copy(), targets, rng_a)
    out_b = _rake_categorical(arr.copy(), targets, rng_b)
    np.testing.assert_array_equal(out_a, out_b)


def test_assign_municipalities_shape_and_subset() -> None:
    rng = make_rng(1)
    departments = np.array(["Central", "Central", "Alto Paraguay", "UnknownDept"])
    out = _assign_municipalities(departments, rng)
    assert len(out) == len(departments)
    assert all(isinstance(x, str) and len(x) > 0 for x in out)
    central_opts = set(_MAIN_MUNICIPALITIES["Central"])
    assert set(out[:2]).issubset(central_opts)
    alto_opts = {"Fuerte Olimpo", "Bahia Negra", "Carmelo Peralta"}
    assert out[2] in alto_opts
    assert out[3] == "UnknownDept"


def test_assign_language_labels_subset_and_shape() -> None:
    rng = make_rng(5)
    n = 200
    lang_priors = {
        "guarani_only": 0.28,
        "spanish_only": 0.42,
        "jopara_bilingual": 0.25,
        "other": 0.05,
    }
    departments = np.array(["Asuncion"] * (n // 2) + ["Guaira"] * (n // 2))
    rural = np.array([False] * (n // 2) + [True] * (n // 2))
    out = _assign_language(departments, rural, lang_priors, rng)
    assert len(out) == n
    allowed = set(lang_priors.keys())
    assert set(out).issubset(allowed)
