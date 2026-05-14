# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedFunction=false
"""Posterior predictive check smoke tests (MC_FAST PyMC fit)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


def _synthetic_tracking(n: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows: list[dict[str, object]] = []
    for i in range(n):
        pub = date(2018, 2, 1) + timedelta(days=i * 14)
        a = 50.0 + (3.7 + float(rng.normal(0, 0.5))) / 2
        b = 50.0 - (3.7 + float(rng.normal(0, 0.5))) / 2
        rows.append(
            {
                "poll_wave_id": f"wave_ppc_{i}",
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


def test_fit_tracking_hierarchical_sample_ppc_produces_posterior_predictive() -> None:
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )

    tracking = _synthetic_tracking(n=4)
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        sample_ppc=True,
    )
    assert hasattr(idata, "posterior_predictive"), "posterior_predictive group missing"
    pp = idata.posterior_predictive["obs"]  # type: ignore[union-attr]
    assert pp is not None
    samples = np.asarray(pp.values).reshape(-1, len(tracking))
    assert samples.shape[1] == len(tracking)
    assert samples.shape[0] > 0


def test_generate_ppc_plot_writes_png(tmp_path: Path) -> None:
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )
    from module_c_forecasting_scenarios.viz.ppc_plot import generate_ppc_plot

    tracking = _synthetic_tracking(n=4)
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        sample_ppc=True,
    )
    png_path = tmp_path / "ppc_plot.png"
    result = generate_ppc_plot(idata, tracking, png_path)
    assert result.exists()
    assert result.stat().st_size > 1000


def test_generate_ppc_plot_raises_without_ppc_group() -> None:
    from module_c_forecasting_scenarios.models.tracking.hierarchical import (
        fit_tracking_hierarchical,
    )
    from module_c_forecasting_scenarios.viz.ppc_plot import generate_ppc_plot

    tracking = _synthetic_tracking(n=4)
    idata = fit_tracking_hierarchical(
        tracking,
        outcome_event_date=date(2018, 4, 22),
        calibration_series="A",
        sample_ppc=False,
    )
    import pytest as _pytest

    with _pytest.raises(ValueError, match="posterior_predictive"):
        generate_ppc_plot(idata, tracking, Path("/tmp/should_not_exist.png"))
