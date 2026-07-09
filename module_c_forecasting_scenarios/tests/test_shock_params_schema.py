"""Schema validation + provenance-ledger completeness for shock_params.yaml (IMP-C04).

``load_shock_params`` must reject unknown top-level keys and out-of-bounds
values (acceptance criterion 4), and every hand-set scalar it validates must
carry a ``provenance`` row naming its source and sensitivity reference
(acceptance criterion 1).
"""

from __future__ import annotations

import copy

import pytest

from module_c_forecasting_scenarios.features.shock_scores import (
    _BOUNDED_SCALAR_KEYS,
    load_shock_params,
    validate_shock_params,
)

# Parameters this ledger requires a provenance row for (the hand-set
# calibration/threshold constants named in IMP-C04's acceptance criteria).
REQUIRED_PROVENANCE_KEYS = (
    "lambda1",
    "lambda2",
    "lambda3",
    "m_star_extreme_pp",
    "phi_opaque_threshold",
    "rho_herd_threshold",
    "herding_covariance_march_elevated",
    "herding_covariance_march_baseline",
    "herding_covariance_april",
    "herding_covariance_outside",
    "clip_days_before_outcome",
    "shock_multiplier",
)


def test_load_shock_params_valid_by_default() -> None:
    params = load_shock_params()
    assert 0 < params["lambda1"] <= 1  # type: ignore[operator]


def test_unknown_top_level_key_aborts() -> None:
    params = load_shock_params()
    bad = dict(params)
    bad["totally_unknown_key"] = 1.0
    with pytest.raises(ValueError, match="unknown key"):
        validate_shock_params(bad)


@pytest.mark.parametrize("key", [k for k, _lo, _hi in _BOUNDED_SCALAR_KEYS])
def test_out_of_bounds_scalar_aborts(key: str) -> None:
    params = load_shock_params()
    bad = dict(params)
    bad[key] = -1.0  # below every documented lower bound (all are > 0)
    with pytest.raises(ValueError, match="out of bounds"):
        validate_shock_params(bad)


def test_lambda_above_one_aborts() -> None:
    params = load_shock_params()
    bad = dict(params)
    bad["lambda1"] = 1.5
    with pytest.raises(ValueError, match="out of bounds"):
        validate_shock_params(bad)


def test_m_star_extreme_pp_above_30_aborts() -> None:
    params = load_shock_params()
    bad = dict(params)
    bad["m_star_extreme_pp"] = 31.0
    with pytest.raises(ValueError, match="out of bounds"):
        validate_shock_params(bad)


def test_missing_required_key_aborts() -> None:
    params = load_shock_params()
    bad = copy.deepcopy(params)
    del bad["lambda2"]
    with pytest.raises(ValueError, match="missing required key"):
        validate_shock_params(bad)


def test_non_numeric_scalar_aborts() -> None:
    params = load_shock_params()
    bad = dict(params)
    bad["lambda1"] = "not a number"
    with pytest.raises(ValueError, match="must be numeric"):
        validate_shock_params(bad)


class TestProvenanceLedgerCompleteness:
    def test_every_required_param_has_a_provenance_row(self) -> None:
        params = load_shock_params()
        provenance = params.get("provenance")
        assert isinstance(provenance, dict), "shock_params.yaml must declare a provenance: block"
        missing = [k for k in REQUIRED_PROVENANCE_KEYS if k not in provenance]
        assert not missing, f"shock_params.yaml provenance ledger missing rows for: {missing}"

    @pytest.mark.parametrize("key", REQUIRED_PROVENANCE_KEYS)
    def test_provenance_row_has_source_and_sensitivity_reference(self, key: str) -> None:
        params = load_shock_params()
        row = params["provenance"][key]  # type: ignore[index]
        assert row["source"] in {"estimated", "hypothesis"}
        assert row.get("rationale")
        assert row.get("sensitivity_reference")

    def test_no_estimation_language_for_hypothesis_rows(self) -> None:
        """Negative constraint: hypothesis rows must not claim to be fitted/calibrated."""
        params = load_shock_params()
        provenance = params["provenance"]  # type: ignore[index]
        banned = ("fitted", "calibrated", "learned")
        for key in REQUIRED_PROVENANCE_KEYS:
            row = provenance[key]
            if row["source"] != "hypothesis":
                continue
            rationale_low = str(row["rationale"]).lower()
            for word in banned:
                assert word not in rationale_low, (
                    f"provenance[{key!r}] is source=hypothesis but rationale uses "
                    f"estimation language {word!r}"
                )
