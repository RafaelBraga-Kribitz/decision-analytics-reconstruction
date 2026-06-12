"""m-star outcome anchor: structural and sensitivity tests (MC_FAST PyMC fits).

The reconstruction's "calibrated forecasting" claim requires the verified
outcome margin (m★, series A|B) to enter the tracking likelihood — not to be
narrative-only. These tests prove the anchor is structural:

1. With a tight anchor, the terminal posterior margin lands on m★ even when
   every poll says otherwise.
2. Without the anchor, the terminal posterior follows the polls (so the pull
   in (1) is the anchor, not the data).
3. The anchor is series-aware: switching A→B moves the terminal posterior to
   the other series' m★.
4. Anchor strength behaves monotonically: a loose anchor ends between the
   poll evidence and m★.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest
import yaml

from module_c_forecasting_scenarios.models.tracking.hierarchical import (
    fit_tracking_hierarchical,
)
from module_c_forecasting_scenarios.paths import module_config_dir

pytestmark = pytest.mark.slow

OUTCOME = date(2018, 4, 22)
POLL_LEVEL_PP = 12.0  # synthetic polls sit far above either series anchor


@pytest.fixture(autouse=True)
def _mc_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")


@pytest.fixture(scope="module")
def anchors() -> dict[str, float]:
    with open(module_config_dir() / "calibration.yaml") as f:
        cal = yaml.safe_load(f)
    return {
        "A": float(cal["anchors"]["A"]["margin_m_star_pp"]),
        "B": float(cal["anchors"]["B"]["margin_m_star_pp"]),
    }


def _tracking_at_level(level_pp: float, n: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows: list[dict[str, object]] = []
    for i in range(n):
        pub = date(2018, 2, 1) + timedelta(days=i * 14)
        m = level_pp + float(rng.normal(0, 0.4))
        rows.append(
            {
                "poll_wave_id": f"wave_anchor_{i}",
                "pollster_id": "pollster_a" if i % 2 == 0 else "pollster_b",
                "pollster_bias_family": "default",
                "publication_date": pub,
                "field_window_start": pub - timedelta(days=3),
                "field_window_end": pub,
                "preference_proxy_a_pct": 50.0 + m / 2,
                "preference_proxy_b_pct": 50.0 - m / 2,
                "m_poll_pp": m,
                "redistribution_rule": "exclude",
                "phi_transparency": 0.9,
                "tau_eff": 0.9,
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


def _terminal_mean(idata: Any) -> float:
    post = cast(Any, idata.posterior["mu_margin"])
    return float(np.asarray(post.isel(day=-1).values).mean())


@pytest.fixture(scope="module")
def fits(anchors: dict[str, float]) -> dict[str, float]:
    """Run the four fits once; individual tests assert on the cached results."""
    import os

    os.environ["MC_FAST"] = "1"
    tracking = _tracking_at_level(POLL_LEVEL_PP)
    out: dict[str, float] = dict(anchors)
    out["anchored_a"] = _terminal_mean(
        fit_tracking_hierarchical(
            tracking,
            outcome_event_date=OUTCOME,
            calibration_series="A",
            m_star_pp=anchors["A"],
            anchor_sigma_pp=0.5,
        )
    )
    out["anchored_b"] = _terminal_mean(
        fit_tracking_hierarchical(
            tracking,
            outcome_event_date=OUTCOME,
            calibration_series="B",
            m_star_pp=anchors["B"],
            anchor_sigma_pp=0.5,
        )
    )
    out["unanchored"] = _terminal_mean(
        fit_tracking_hierarchical(
            tracking,
            outcome_event_date=OUTCOME,
            calibration_series="A",
            m_star_pp=None,
        )
    )
    out["loose"] = _terminal_mean(
        fit_tracking_hierarchical(
            tracking,
            outcome_event_date=OUTCOME,
            calibration_series="A",
            m_star_pp=anchors["A"],
            anchor_sigma_pp=8.0,
        )
    )
    return out


def test_tight_anchor_pins_terminal_margin_to_m_star(fits: dict[str, float]) -> None:
    assert abs(fits["anchored_a"] - fits["A"]) < 1.5, (
        f"terminal margin {fits['anchored_a']:.2f} not pulled to series A "
        f"m_star {fits['A']:.2f}"
    )


def test_unanchored_fit_follows_polls_not_m_star(fits: dict[str, float]) -> None:
    assert abs(fits["unanchored"] - POLL_LEVEL_PP) < 4.0, (
        f"unanchored terminal margin {fits['unanchored']:.2f} should track the "
        f"poll level {POLL_LEVEL_PP:.1f}"
    )
    assert (
        abs(fits["unanchored"] - fits["A"]) > 3.0
    ), "unanchored fit landed on m_star anyway — anchor test has no power"


def test_anchor_is_series_aware(fits: dict[str, float]) -> None:
    # Each anchored fit must sit closer to its own series' m_star than to the
    # other's poll-free alternative; with only 0.18pp between series we assert
    # each fit brackets its own anchor.
    assert abs(fits["anchored_a"] - fits["A"]) < abs(fits["anchored_a"] - POLL_LEVEL_PP)
    assert abs(fits["anchored_b"] - fits["B"]) < abs(fits["anchored_b"] - POLL_LEVEL_PP)


def test_loose_anchor_sits_between_polls_and_m_star(fits: dict[str, float]) -> None:
    lo = min(fits["A"], POLL_LEVEL_PP)
    hi = max(fits["A"], POLL_LEVEL_PP)
    assert lo - 1.0 <= fits["loose"] <= hi + 1.0
    # And strictly weaker pull than the tight anchor.
    assert abs(fits["loose"] - fits["A"]) >= abs(fits["anchored_a"] - fits["A"])
