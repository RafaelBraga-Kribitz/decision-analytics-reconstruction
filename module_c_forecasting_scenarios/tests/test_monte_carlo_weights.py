"""Monte Carlo scenario-bucket importance weighting (IMP-C08 / audit C14).

Equal-thirds stratification is a variance-reduction design; these tests lock
in that every draw carries an importance weight correcting pooled statistics
back to the empirical bucket prevalence, that weighted and unweighted pooled
statistics provably differ when prevalences differ, and the degenerate
single-observed-bucket case behaves sanely (no inf/NaN, no div-by-zero).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from module_c_forecasting_scenarios.data.cleaning_pipeline import clean_raw_polls
from module_c_forecasting_scenarios.data.raw_loader import load_raw_polls_csv
from module_c_forecasting_scenarios.scenarios.monte_carlo import (
    CANONICAL_BUCKETS,
    _design_shares,
    effective_sample_size,
    empirical_bucket_prevalence,
    run_monte_carlo_scenarios,
    weighted_pooled_mean,
    weighted_pooled_quantile,
)


def _tracking(fixture_raw_polls_csv: Path) -> pd.DataFrame:
    raw = load_raw_polls_csv(fixture_raw_polls_csv)
    tracking, _ = clean_raw_polls(raw, "A")
    return tracking


def test_empirical_prevalence_sums_to_one(fixture_raw_polls_csv: Path) -> None:
    tracking = _tracking(fixture_raw_polls_csv)
    prevalence = empirical_bucket_prevalence(tracking)
    assert sum(prevalence.values()) == pytest.approx(1.0)
    assert set(prevalence.keys()) == set(CANONICAL_BUCKETS)


def test_empirical_prevalence_empty_tracking_is_all_zero() -> None:
    prevalence = empirical_bucket_prevalence(pd.DataFrame({"scenario_bucket": []}))
    assert prevalence == {b: 0.0 for b in CANONICAL_BUCKETS}


def test_draw_weight_column_present_and_nonnegative(
    fixture_raw_polls_csv: Path, tmp_path: Path
) -> None:
    tracking = _tracking(fixture_raw_polls_csv)
    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    assert "draw_weight" in draws.columns
    assert (draws["draw_weight"] >= 0).all()


def test_draw_weights_sum_to_total_draws(fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
    """sum(weight) == n when prevalence is a proper distribution over the 3 buckets.

    sum_b design_share(b) * n * (prevalence(b) / design_share(b)) == n * sum(prevalence) == n.
    """
    tracking = _tracking(fixture_raw_polls_csv)
    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
    assert draws["draw_weight"].sum() == pytest.approx(900.0, rel=1e-6)


def test_manifest_records_prevalence_design_share_and_hash(
    fixture_raw_polls_csv: Path, tmp_path: Path
) -> None:
    tracking = _tracking(fixture_raw_polls_csv)
    manifest = run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    assert set(manifest["bucket_prevalence_observed"].keys()) == set(CANONICAL_BUCKETS)  # type: ignore[union-attr]
    assert set(manifest["bucket_design_share"].keys()) == set(CANONICAL_BUCKETS)  # type: ignore[union-attr]
    assert manifest["tracking_data_hash"]
    # Design shares are equal-thirds regardless of the data.
    shares = manifest["bucket_design_share"].values()  # type: ignore[union-attr]
    for s in shares:
        assert s == pytest.approx(1.0 / 3.0, abs=1e-6)


def test_weighted_vs_unweighted_pooled_mean_differ_when_prevalences_differ(
    fixture_raw_polls_csv: Path, tmp_path: Path
) -> None:
    tracking = _tracking(fixture_raw_polls_csv)
    prevalence = empirical_bucket_prevalence(tracking)
    # Sanity: the canonical fixture does NOT have exactly 1/3 prevalence in
    # every bucket (equal thirds would make weighting a no-op).
    assert len(set(round(v, 6) for v in prevalence.values())) > 1

    run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
    draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")

    unweighted_mean = float(draws["shock_scale"].mean())
    weighted_mean = weighted_pooled_mean(draws, "shock_scale")
    assert unweighted_mean != pytest.approx(weighted_mean, rel=1e-9)

    # Forcing weights to 1 must reproduce the plain (unweighted) mean —
    # proving the weight column actually participates in the computation.
    forced = draws.copy()
    forced["draw_weight"] = 1.0
    assert weighted_pooled_mean(forced, "shock_scale") == pytest.approx(unweighted_mean)


def test_weighted_pooled_quantile_matches_unweighted_at_uniform_weight() -> None:
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "draw_weight": [1.0, 1.0, 1.0, 1.0]})
    assert weighted_pooled_quantile(df, "x", 0.5) == pytest.approx(np.quantile(df["x"], 0.5))


def test_weighted_pooled_mean_raises_on_zero_total_weight() -> None:
    df = pd.DataFrame({"x": [1.0, 2.0], "draw_weight": [0.0, 0.0]})
    with pytest.raises(ValueError, match="sums to <= 0"):
        weighted_pooled_mean(df, "x")


def test_weighted_pooled_quantile_rejects_out_of_range_q() -> None:
    df = pd.DataFrame({"x": [1.0, 2.0], "draw_weight": [1.0, 1.0]})
    with pytest.raises(ValueError, match=r"q must be in \[0, 1\]"):
        weighted_pooled_quantile(df, "x", 1.5)


class TestDegenerateSingleBucket:
    """Edge case: every tracking-observed poll lands in one canonical bucket."""

    def _single_bucket_tracking(self, fixture_raw_polls_csv: Path) -> pd.DataFrame:
        tracking = _tracking(fixture_raw_polls_csv)
        out = tracking.copy()
        out["scenario_bucket"] = "baseline"
        return out

    def test_prevalence_is_degenerate(self, fixture_raw_polls_csv: Path) -> None:
        tracking = self._single_bucket_tracking(fixture_raw_polls_csv)
        prevalence = empirical_bucket_prevalence(tracking)
        assert prevalence["baseline"] == pytest.approx(1.0)
        assert prevalence["extreme_tracker"] == 0.0
        assert prevalence["compounded_herd"] == 0.0

    def test_draw_weights_no_nan_or_inf(self, fixture_raw_polls_csv: Path, tmp_path: Path) -> None:
        tracking = self._single_bucket_tracking(fixture_raw_polls_csv)
        run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
        draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
        assert np.isfinite(draws["draw_weight"]).all()
        # The dominant (baseline) bucket carries all the pooled mass: weight ~= 3.0
        # (design_share = 1/3, prevalence = 1.0).
        baseline_weight = draws.loc[draws["scenario_bucket"] == "baseline", "draw_weight"].iloc[0]
        assert baseline_weight == pytest.approx(3.0, rel=1e-6)
        # Zero-prevalence buckets (synthesized from prior) carry weight 0 — they
        # exist for conditional exploration only, not pooled likelihood.
        for bucket in ("extreme_tracker", "compounded_herd"):
            weights = draws.loc[draws["scenario_bucket"] == bucket, "draw_weight"]
            assert (weights == 0.0).all()

    def test_pooled_mean_dominated_by_the_only_observed_bucket(
        self, fixture_raw_polls_csv: Path, tmp_path: Path
    ) -> None:
        tracking = self._single_bucket_tracking(fixture_raw_polls_csv)
        run_monte_carlo_scenarios(tracking, None, out_dir=tmp_path, n_draws=900)
        draws = pd.read_parquet(tmp_path / "monte_carlo_draws.parquet")
        weighted_mean = weighted_pooled_mean(draws, "shock_scale")
        baseline_only_mean = float(
            draws.loc[draws["scenario_bucket"] == "baseline", "shock_scale"].mean()
        )
        assert weighted_mean == pytest.approx(baseline_only_mean, rel=1e-9)


class TestEffectiveSampleSize:
    def test_equal_weights_effective_size_equals_n(self) -> None:
        df = pd.DataFrame({"draw_weight": [1.0] * 100})
        assert effective_sample_size(df) == pytest.approx(100.0)

    def test_concentrated_weights_reduce_effective_size(self) -> None:
        # 99 draws with weight ~0, one draw with all the mass.
        weights = [0.001] * 99 + [100.0]
        df = pd.DataFrame({"draw_weight": weights})
        n_eff = effective_sample_size(df)
        assert n_eff < 100.0
        assert n_eff > 0.0

    def test_all_zero_weights_gives_zero(self) -> None:
        df = pd.DataFrame({"draw_weight": [0.0, 0.0, 0.0]})
        assert effective_sample_size(df) == 0.0


def test_design_shares_equal_thirds() -> None:
    shares = _design_shares(900)
    for b in CANONICAL_BUCKETS:
        assert shares[b] == pytest.approx(1.0 / 3.0)
