"""IMP-B01 / issue #57: objective-coefficient provenance manifest completeness.

Asserts config/allocation_parameter_provenance.yaml stays in lock-step with the
hand-set coefficients the MILP actually optimizes against — the same invariant
scripts/check_allocation_parameter_provenance.py enforces in make verify, pinned
here so the Module B test lane fails on drift too.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from module_b_resource_allocation.constants import (
    COVERAGE_LOWER_BOUND_PCT,
    VALID_PROVENANCE,
)
from module_b_resource_allocation.features.diminishing_returns import (
    _INFLECTION_PCT,
    _K_SHAPE,
    _SAT_SHARE,
)
from module_b_resource_allocation.models.allocation import (
    _SCENARIO_WEEK_WEIGHTS,
    _TIER_PENALTY,
)

_MANIFEST = Path(__file__).resolve().parents[1] / "config" / "allocation_parameter_provenance.yaml"


def _manifest() -> dict:
    return yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))


def test_neutral_is_a_valid_provenance() -> None:
    assert "NEUTRAL" in VALID_PROVENANCE


def test_every_tier_penalty_has_a_matching_entry() -> None:
    values = _manifest()["coefficient_families"]["tier_penalty"]["values"]
    assert set(values) == set(_TIER_PENALTY)
    for tier, val in _TIER_PENALTY.items():
        assert values[tier]["value"] == val
        assert values[tier]["provenance"] in VALID_PROVENANCE


def test_scenario_week_weights_covered() -> None:
    values = _manifest()["coefficient_families"]["scenario_week_weight"]["values"]
    for scen, curve in _SCENARIO_WEEK_WEIGHTS.items():
        for phase in ("early", "late"):
            assert values[f"{scen}.{phase}"]["value"] == curve[phase]


def test_diminishing_returns_triples_covered() -> None:
    channels = _manifest()["coefficient_families"]["diminishing_returns"]["channels"]
    assert set(channels) == set(_SAT_SHARE)
    for ch in _SAT_SHARE:
        assert channels[ch]["sat_share"]["value"] == _SAT_SHARE[ch]
        assert channels[ch]["inflection_pct"]["value"] == _INFLECTION_PCT[ch]
        assert channels[ch]["k_shape"]["value"] == _K_SHAPE[ch]


def test_coverage_lower_bound_covered() -> None:
    cov = _manifest()["coefficient_families"]["coverage_lower_bound_pct"]
    assert cov["value"] == COVERAGE_LOWER_BOUND_PCT
    assert cov["provenance"] in VALID_PROVENANCE


def test_neutral_only_on_identity_values() -> None:
    # A NEUTRAL tag must correspond to the identity multiplier (1.0); a
    # differentiating value dressed up as NEUTRAL would hide an invented number.
    values = _manifest()["coefficient_families"]["tier_penalty"]["values"]
    for tier, entry in values.items():
        if entry["provenance"] == "NEUTRAL":
            assert entry["value"] == 1.0, f"{tier} tagged NEUTRAL but value != 1.0"
