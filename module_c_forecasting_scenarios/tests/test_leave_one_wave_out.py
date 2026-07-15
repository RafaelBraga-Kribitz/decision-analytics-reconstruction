"""Leave-one-wave-out validation smoke test (MC_FAST PyMC fit)."""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from module_c_forecasting_scenarios.validation.leave_one_wave_out import (
    _gaussian_log_score,
    leave_one_wave_out_validation,
    summarize_lowo,
)

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def _synthetic_tracking(n: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows: list[dict[str, object]] = []
    for i in range(n):
        pub = date(2018, 2, 1) + timedelta(days=i * 10)
        a = 50.0 + (3.7 + float(rng.normal(0, 0.5))) / 2
        b = 50.0 - (3.7 + float(rng.normal(0, 0.5))) / 2
        rows.append(
            {
                "poll_wave_id": f"wave_synth_{i}",
                "pollster_id": "pollster_a" if i % 2 == 0 else "pollster_b",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=3),
                "field_window_end": pub,
                "preference_proxy_a_pct": a,
                "preference_proxy_b_pct": b,
                "m_poll_pp": a - b,
                "redistribution_rule": "exclude",
                "phi_transparency": 0.75,
                "tau_eff": 0.75,
                "calibration_series": "A",
                "series_tag": "A",
                "conglomerate_id": None,
                "media_holding": None,
                "sample_size_known": True,
                "firm_wave_month": f"{pub.year:04d}-{pub.month:02d}",
                "scenario_bucket": "baseline",
                "shock_score_s": 0.1,
                "has_ficha": True,
            }
        )
    return pd.DataFrame(rows)


_PER_WAVE_COLUMNS = (
    "poll_wave_id",
    "publication_date",
    "n_train",
    "observed_margin_pp",
    "predictive_mean_pp",
    "predictive_sd_pp",
    "hdi94_low_pp",
    "hdi94_high_pp",
    "log_score",
    "covered_94pct",
    "rhat_max",
    "ess_bulk_min",
    "n_divergences",
)


def test_gaussian_log_score_matches_closed_form() -> None:
    # Deterministic check of the scoring rule against scipy-free closed form.
    samples = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=float)
    mean = samples.mean()
    sd = samples.std(ddof=1)
    obs = 2.5
    expected = -0.5 * math.log(2 * math.pi * sd**2) - (obs - mean) ** 2 / (2 * sd**2)
    assert _gaussian_log_score(samples, obs) == pytest.approx(expected)


def test_lowo_holds_out_every_wave_and_reports_metrics() -> None:
    tracking = _synthetic_tracking(n=5)
    result = leave_one_wave_out_validation(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    # LOWO scores EVERY wave (k = n folds), unlike walk-forward's expanding window.
    assert result.per_wave.shape[0] == 5
    assert set(result.per_wave.columns) >= set(_PER_WAVE_COLUMNS)
    # Each fold trains on the other n-1 waves.
    assert (result.per_wave["n_train"] == 4).all()
    m = result.metrics
    assert m["n_waves"] == 5
    assert 0.0 <= m["coverage_94pct"] <= 1.0
    assert m["n_covered"] == pytest.approx(result.per_wave["covered_94pct"].sum())
    assert math.isfinite(m["mean_log_score"])
    # HDI ordering sanity: low <= high on every fold.
    assert (result.per_wave["hdi94_low_pp"] <= result.per_wave["hdi94_high_pp"]).all()
    # Sampler diagnostics are reported for every fold (honest sampler quality).
    assert result.per_wave["rhat_max"].notna().all()
    assert (result.per_wave["ess_bulk_min"] > 0).all()
    assert (result.per_wave["n_divergences"] >= 0).all()
    # Well-specified synthetic data: the 94% interval should cover most waves.
    assert m["coverage_94pct"] >= 3.0 / 5.0
    # Unanchored variant is recorded.
    assert "unanchored" in result.model_variant


def test_lowo_raises_when_too_few_waves() -> None:
    tracking = _synthetic_tracking(n=2)
    with pytest.raises(ValueError, match="leave-one-wave-out"):
        leave_one_wave_out_validation(
            tracking,
            outcome_event_date=date(2018, 4, 22),
            calibration_series="A",
        )


def test_lowo_never_anchors_on_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """Out-of-sample guarantee: LOWO must NEVER pass m_star into any fit.

    The anchored series conditions on the verified election margin (m★ in the
    likelihood) — a retrodiction, not a forecast (F-069). LOWO scores withheld
    waves, so every fit it triggers must be anchor-free. We spy on the fit
    function as referenced inside the shared walk_forward module.
    """
    import module_c_forecasting_scenarios.validation.walk_forward as wf

    real_fit = wf.fit_tracking_hierarchical
    seen_m_star: list[object] = []

    def _spy(*args: object, **kwargs: object) -> object:
        seen_m_star.append(kwargs.get("m_star_pp", "MISSING_KW"))
        return real_fit(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(wf, "fit_tracking_hierarchical", _spy)
    leave_one_wave_out_validation(
        _synthetic_tracking(n=4),
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
    )
    assert seen_m_star, "LOWO never invoked the tracking fit — test has no power"
    assert all(
        v is None for v in seen_m_star
    ), f"LOWO leaked the outcome anchor into a fit: m_star_pp values = {seen_m_star}"


def test_summarize_lowo_handles_empty() -> None:
    empty = pd.DataFrame(columns=["log_score", "covered_94pct"])
    out = summarize_lowo(empty)
    assert out["n_waves"] == 0
    assert np.isnan(out["mean_log_score"])
