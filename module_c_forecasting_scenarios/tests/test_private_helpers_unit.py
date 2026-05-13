"""Unit tests for selected private helpers in Module C (Project Action List line 79)."""

from __future__ import annotations

import pytest
from module_c_forecasting_scenarios.data.cleaning_pipeline import _load_m_star, _redistribute_ab
from module_c_forecasting_scenarios.models.tracking.hierarchical import _sampler_kwargs
from module_c_forecasting_scenarios.scenarios.monte_carlo import _mc_n


@pytest.mark.parametrize(
    ("a", "b", "und", "rule", "exp_a", "exp_b", "exp_rule"),
    [
        (40.0, 40.0, None, "exclude", 40.0, 40.0, "exclude"),
        (30.0, 30.0, 40.0, "redistribute_third_party", 30.0, 30.0, "redistribute_third_party"),
        (0.0, 0.0, 0.0, "redistribute_third_party", 50.0, 50.0, "redistribute_third_party"),
        (20.0, 30.0, 10.0, "proportional_AB", 36.0, 54.0, "proportional_AB"),
        (0.0, 0.0, 10.0, "proportional_AB", 50.0, 50.0, "proportional_AB"),
    ],
)
def test_redistribute_ab_rules(
    a: float,
    b: float,
    und: float | None,
    rule: str,
    exp_a: float,
    exp_b: float,
    exp_rule: str,
) -> None:
    ra, rb, rr = _redistribute_ab(a, b, und, rule)
    assert rr == exp_rule
    assert ra == pytest.approx(exp_a, rel=0, abs=1e-9)
    assert rb == pytest.approx(exp_b, rel=0, abs=1e-9)


def test_load_m_star_series_a_and_b_match_calibration_yaml() -> None:
    assert _load_m_star("A") == pytest.approx(3.70)
    assert _load_m_star("B") == pytest.approx(3.88)
    assert _load_m_star("a") == pytest.approx(3.70)


def test_mc_n_respects_mc_fast_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MC_FAST", raising=False)
    assert _mc_n() == 10_000
    monkeypatch.setenv("MC_FAST", "1")
    assert _mc_n() == 200


def test_sampler_kwargs_fast_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MC_FAST", "1")
    kw = _sampler_kwargs()
    assert kw["chains"] == 2
    assert "draws" in kw and "tune" in kw
    assert "random_seed" in kw


def test_sampler_kwargs_default_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MC_FAST", raising=False)
    kw = _sampler_kwargs()
    assert kw["chains"] >= 1
    assert int(kw["draws"]) >= int(kw["tune"])
    assert "target_accept" in kw
