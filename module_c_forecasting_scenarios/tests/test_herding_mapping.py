"""Explicit pollster/carrier -> herding-group mapping table (IMP-C04 / audit C5).

Replaces the former substring-matching resolution in ``herding_weights.py``
with an explicit ``config/herding_groups.yaml`` lookup. These tests lock in:
known-carrier resolution, the unmapped-carrier default + warning, and that no
substring containment ever participates in resolution.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
import pytest

from module_c_forecasting_scenarios.features.herding_weights import (
    count_unmapped_carriers,
    load_herding_config,
    resolve_herding_group,
    rho_herd_for_row,
)

_LOGGER_NAME = "module_c_forecasting_scenarios.features.herding_weights"


def test_known_carrier_resolves_via_table_not_substring() -> None:
    """A carrier present in the mapping table resolves to its configured group."""
    resolution = resolve_herding_group("Vierci")
    assert resolution.group == "elevated"
    assert resolution.matched is True


def test_unknown_carrier_defaults_and_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """A carrier absent from the table gets the default group + a logged warning."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        resolution = resolve_herding_group("Some Brand New Outlet")
    cfg = load_herding_config()
    assert resolution.group == str(cfg["default_group"])
    assert resolution.matched is False
    assert any("unmapped conglomerate_carrier" in rec.message for rec in caplog.records)
    assert any("Some Brand New Outlet" in rec.message for rec in caplog.records)


def test_missing_carrier_defaults_without_warning(caplog: pytest.LogCaptureFixture) -> None:
    """A null/missing carrier is an expected state, not an unmapped-identity failure."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        resolution = resolve_herding_group(None)
    assert resolution.matched is True
    assert resolution.carrier_normalized is None
    assert not any("unmapped conglomerate_carrier" in rec.message for rec in caplog.records)

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        nan_resolution = resolve_herding_group(float("nan"))
    assert nan_resolution.matched is True


@pytest.mark.parametrize(
    "carrier",
    [
        "Comunicaciones Nacionales",  # contains "ica" as a substring, not an exact match
        "Publicaciones del Sur",  # contains "ica" as a substring
        "Vierci Holdings",  # contains "vierci" as a substring, not an exact match
    ],
)
def test_no_substring_fallback_for_near_miss_carriers(carrier: str) -> None:
    """Carriers that merely CONTAIN a mapped name/token must not match it.

    The former implementation used ``"vierci" in carrier`` / ``"ica" in
    carrier`` substring checks; a carrier like "Comunicaciones Nacionales"
    contains "ica" twice and would have silently landed in the elevated group.
    The explicit table requires an exact (case-folded) match.
    """
    resolution = resolve_herding_group(carrier)
    cfg = load_herding_config()
    assert resolution.group == str(cfg["default_group"])
    assert resolution.matched is False


@pytest.mark.parametrize(
    ("pub_date", "carrier", "expected_rho"),
    [
        (date(2018, 3, 20), "Vierci", 0.55),  # march_window, elevated
        (date(2018, 3, 20), "ABC", 0.35),  # march_window, baseline (default)
        (date(2018, 4, 10), "Vierci", 0.25),  # april_window, elevated
        (date(2018, 4, 10), "ABC", 0.25),  # april_window, baseline
        (date(2018, 1, 1), "Vierci", 0.05),  # outside_window, elevated
        (date(2018, 1, 1), "ABC", 0.05),  # outside_window, baseline
    ],
)
def test_rho_herd_for_row_matches_covariance_matrix(
    pub_date: date, carrier: str, expected_rho: float
) -> None:
    assert rho_herd_for_row(pub_date, carrier) == pytest.approx(expected_rho)


def test_rho_herd_april_band_backward_compatible() -> None:
    """Pre-existing behavior (test_pipeline_runners.py) must be unchanged."""
    assert rho_herd_for_row(date(2018, 4, 10), None) == pytest.approx(0.25)


def test_count_unmapped_carriers_tallies_only_non_null_unmapped() -> None:
    carriers = pd.Series(["Vierci", "New Outlet", "New Outlet", None, "ABC"])
    counts = count_unmapped_carriers(carriers)
    assert counts == {"new outlet": 2, "abc": 1}


def test_count_unmapped_carriers_empty_when_all_mapped_or_missing() -> None:
    carriers = pd.Series(["Vierci", "ICA", None])
    assert count_unmapped_carriers(carriers) == {}
