"""Walk-forward validation smoke test (MC_FAST PyMC fit)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from module_c_forecasting_scenarios.validation.walk_forward import (
    summarize_walk_forward,
    walk_forward_tracking_validation,
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


_HOLDOUT_COLUMNS = (
    "hdi80_low_pp",
    "hdi80_high_pp",
    "hdi95_low_pp",
    "hdi95_high_pp",
    "prob_margin_positive",
    "observed_positive",
    "in_hdi80",
    "in_hdi95",
)


def _assert_walk_forward_metrics(result) -> None:
    assert result.per_holdout.shape[0] == 3
    assert {"brier_score", "log_loss", "coverage_80pct", "coverage_95pct"} <= set(result.metrics)
    assert set(result.per_holdout.columns) >= set(_HOLDOUT_COLUMNS)
    m = result.metrics
    assert 0.0 <= m["coverage_80pct"] <= 1.0
    assert 0.0 <= m["coverage_95pct"] <= 1.0
    assert m["coverage_95pct"] >= m["coverage_80pct"] - 1e-9
    assert m["brier_score"] >= 0.0 and m["log_loss"] >= 0.0
    # Predictive 95% interval must cover most holdouts on well-specified synthetic data.
    assert m["coverage_95pct"] >= 2.0 / 3.0


def test_walk_forward_runs_and_reports_metrics() -> None:
    tracking = _synthetic_tracking(n=5)
    result = walk_forward_tracking_validation(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        min_train_size=2,
    )
    _assert_walk_forward_metrics(result)


def test_walk_forward_raises_when_too_few_polls() -> None:
    tracking = _synthetic_tracking(n=2)
    with pytest.raises(ValueError, match="walk-forward"):
        walk_forward_tracking_validation(
            tracking,
            outcome_event_date=date(2018, 4, 22),
            calibration_series="A",
            min_train_size=2,
        )


def test_walk_forward_never_anchors_on_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """Out-of-sample guarantee: walk-forward must NEVER pass m_star to the fit.

    The anchored tracking series conditions on the verified outcome (m★ enters the
    likelihood) — that is a retrodiction, not a forecast (F-069). Walk-forward is
    the genuine out-of-sample series, so every fit it triggers must be anchor-free.
    We spy on the fit function as referenced inside the walk_forward module.
    """
    import module_c_forecasting_scenarios.validation.walk_forward as wf

    real_fit = wf.fit_tracking_hierarchical
    seen_m_star: list[object] = []

    def _spy(*args: object, **kwargs: object) -> object:
        seen_m_star.append(kwargs.get("m_star_pp", "MISSING_KW"))
        return real_fit(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(wf, "fit_tracking_hierarchical", _spy)
    walk_forward_tracking_validation(
        _synthetic_tracking(n=5),
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        min_train_size=2,
    )
    assert seen_m_star, "walk-forward never invoked the tracking fit — test has no power"
    assert all(
        v is None for v in seen_m_star
    ), f"walk-forward leaked the outcome anchor into the fit: m_star_pp values = {seen_m_star}"


def test_summarize_walk_forward_handles_empty() -> None:
    empty = pd.DataFrame(
        columns=[
            "prob_margin_positive",
            "observed_positive",
            "in_hdi80",
            "in_hdi95",
        ]
    )
    out = summarize_walk_forward(empty)
    assert out["n_holdouts"] == 0
    assert np.isnan(out["brier_score"])
