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


def test_walk_forward_runs_and_reports_metrics() -> None:
    tracking = _synthetic_tracking(n=5)
    result = walk_forward_tracking_validation(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        min_train_size=2,
    )
    assert result.per_holdout.shape[0] == 3
    assert {"brier_score", "log_loss", "coverage_80pct", "coverage_95pct"} <= set(result.metrics)
    for col in (
        "hdi80_low_pp",
        "hdi80_high_pp",
        "hdi95_low_pp",
        "hdi95_high_pp",
        "prob_margin_positive",
        "observed_positive",
        "in_hdi80",
        "in_hdi95",
    ):
        assert col in result.per_holdout.columns
    assert 0.0 <= result.metrics["coverage_80pct"] <= 1.0
    assert 0.0 <= result.metrics["coverage_95pct"] <= 1.0
    assert result.metrics["coverage_95pct"] >= result.metrics["coverage_80pct"] - 1e-9
    assert result.metrics["brier_score"] >= 0.0
    assert result.metrics["log_loss"] >= 0.0


def test_walk_forward_raises_when_too_few_polls() -> None:
    tracking = _synthetic_tracking(n=2)
    with pytest.raises(ValueError, match="walk-forward"):
        walk_forward_tracking_validation(
            tracking,
            outcome_event_date=date(2018, 4, 22),
            calibration_series="A",
            min_train_size=2,
        )


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
