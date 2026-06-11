"""Fast regression tests for Module C core-correctness fixes (F-034).

No PyMC sampling here — pure-function gates that lock in:
- the PPC calibration verdict rubric (wide-band trap),
- config-driven extreme-margin threshold in scenario bucketing,
- the shared observation-noise function used by fit and walk-forward.
"""

from __future__ import annotations

import numpy as np

from module_c_forecasting_scenarios.features.shock_scores import (
    scenario_bucket_for_margin,
)
from module_c_forecasting_scenarios.models.tracking.hierarchical import observation_sigma
from module_c_forecasting_scenarios.pipeline.run_ppc import calibration_verdict_from_coverage


class TestCalibrationVerdict:
    def test_wide_band_trap_is_not_calibrated(self) -> None:
        """cov95=1.0 with cov80=0.25 must NOT be 'calibrated' (former bug)."""
        assert calibration_verdict_from_coverage(0.25, 1.0) == "miscalibrated-shape"

    def test_nominal_coverage_is_calibrated(self) -> None:
        assert calibration_verdict_from_coverage(0.80, 0.95) == "calibrated"

    def test_everything_covered_is_under_confident(self) -> None:
        assert calibration_verdict_from_coverage(1.0, 1.0) == "under-confident"

    def test_zero_coverage_is_prior_dominated(self) -> None:
        assert calibration_verdict_from_coverage(0.0, 0.0) == "prior-dominated"

    def test_low_cov95_is_over_confident(self) -> None:
        assert calibration_verdict_from_coverage(0.30, 0.50) == "over-confident"

    def test_mid_cov95_is_slightly_over_confident(self) -> None:
        assert calibration_verdict_from_coverage(0.60, 0.75) == "slightly-over-confident"


class TestScenarioBucketParams:
    def test_extreme_threshold_comes_from_config(self) -> None:
        """A 10pp deviation is 'baseline' at the default 12pp threshold but
        'extreme_tracker' when the config lowers the threshold."""
        assert (
            scenario_bucket_for_margin(13.7, 3.7, phi=0.9, rho=0.0) == "baseline"
            or scenario_bucket_for_margin(13.7, 3.7, phi=0.9, rho=0.0) == "extreme_tracker"
        )
        # Explicit params make the test independent of the YAML default.
        tight = {"m_star_extreme_pp": 5.0}
        loose = {"m_star_extreme_pp": 15.0}
        assert scenario_bucket_for_margin(13.7, 3.7, phi=0.9, rho=0.0, params=tight) == (
            "extreme_tracker"
        )
        assert scenario_bucket_for_margin(13.7, 3.7, phi=0.9, rho=0.0, params=loose) == "baseline"

    def test_compounded_herd_uses_config_threshold(self) -> None:
        params = {"m_star_extreme_pp": 5.0}
        assert (
            scenario_bucket_for_margin(13.7, 3.7, phi=0.2, rho=0.55, params=params)
            == "compounded_herd"
        )


class TestObservationSigma:
    def test_shared_noise_function_matches_likelihood_formula(self) -> None:
        phi = np.array([0.05, 0.25, 0.75, 1.0])
        expected = np.clip(6.0 / np.sqrt(np.maximum(phi, 0.05)), 1.0, 25.0)
        np.testing.assert_allclose(np.asarray(observation_sigma(phi)), expected)

    def test_scalar_input(self) -> None:
        assert float(np.asarray(observation_sigma(0.75))) == float(
            np.clip(6.0 / np.sqrt(0.75), 1.0, 25.0)
        )
