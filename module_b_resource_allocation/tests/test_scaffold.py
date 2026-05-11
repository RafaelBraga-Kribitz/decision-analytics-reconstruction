"""Module B scaffold tests.

These lock the package-level invariants every other Module B phase depends
on: the 11-channel taxonomy, the 18-department canon, the Chaco subset, the
14-week Jan–Apr 2018 grid, and the contract-aligned row counts.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def test_module_b_imports() -> None:
    import module_b_resource_allocation
    from module_b_resource_allocation import constants

    assert module_b_resource_allocation.__version__ == "0.1.0"
    assert constants.N_DEPARTMENTS == 18
    assert constants.N_CHANNELS == 11
    assert constants.WEEK_COUNT == 14


def test_channel_taxonomy_is_11_with_unique_names() -> None:
    from module_b_resource_allocation.constants import CHANNEL_NAMES, CHANNELS

    assert len(CHANNELS) == 11
    assert len(set(CHANNEL_NAMES)) == 11
    expected = {
        "whatsapp_chatbot",
        "messenger_chatbot",
        "facebook_ads",
        "sms",
        "email",
        "tv_spots",
        "radio_spots",
        "billboards",
        "rallies_events",
        "canvassing",
        "sound_cars",
    }
    assert set(CHANNEL_NAMES) == expected


def test_channel_types_are_canonical() -> None:
    from module_b_resource_allocation.constants import CHANNEL_TYPES

    allowed = {"bilateral", "broadcast", "broadcast_to_bilateral", "in_person"}
    assert all(t in allowed for t in CHANNEL_TYPES.values())


def test_departments_and_chaco_partition() -> None:
    from module_b_resource_allocation.constants import (
        CHACO_DEPARTMENTS,
        DEPARTMENTS,
        region_for,
    )

    assert len(DEPARTMENTS) == 18
    assert len(set(DEPARTMENTS)) == 18
    assert CHACO_DEPARTMENTS.issubset(set(DEPARTMENTS))
    assert {"Presidente Hayes", "Boqueron", "Alto Paraguay"} == CHACO_DEPARTMENTS
    for d in CHACO_DEPARTMENTS:
        assert region_for(d) == "CHACO"
    for d in set(DEPARTMENTS) - CHACO_DEPARTMENTS:
        assert region_for(d) == "ORIENTAL"


def test_allocation_dimension_math() -> None:
    from module_b_resource_allocation.constants import (
        ALLOCATION_ROWS,
        N_CHANNELS,
        N_DEPARTMENTS,
        REACH_CAPS_ROWS,
        WEEK_COUNT,
    )

    assert REACH_CAPS_ROWS == 18 * 11
    assert ALLOCATION_ROWS == 18 * 11 * 14
    assert REACH_CAPS_ROWS == N_DEPARTMENTS * N_CHANNELS
    assert ALLOCATION_ROWS == N_DEPARTMENTS * N_CHANNELS * WEEK_COUNT


def test_scaffold_configs_load() -> None:
    config_dir = Path(__file__).resolve().parents[1] / "config"
    required = [
        "budget_envelope.yaml",
        "channel_unit_costs_pyg.yaml",
        "fx_retail_spread_prior.yaml",
        "bcp_tc_ref_2018Q1_prior.yaml",
        "channel_bundles.yaml",
    ]
    for name in required:
        path = config_dir / name
        assert path.exists(), f"Module B config missing: {name}"
        with open(path) as f:
            payload = yaml.safe_load(f)
        assert isinstance(payload, dict)


def test_channel_unit_costs_cover_all_11_channels() -> None:
    from module_b_resource_allocation.constants import CHANNEL_NAMES

    path = Path(__file__).resolve().parents[1] / "config" / "channel_unit_costs_pyg.yaml"
    with open(path) as f:
        payload = yaml.safe_load(f)
    cfg = payload["channels"]
    assert set(cfg.keys()) == set(CHANNEL_NAMES)
    for spec in cfg.values():
        assert spec["unit_cost_pyg"] > 0
        assert spec["fx_tier_default"] in {"REF", "RETAIL"}


def test_fx_priors_cover_all_14_weeks() -> None:
    from module_b_resource_allocation.constants import WEEK_LABELS

    spread = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config" / "fx_retail_spread_prior.yaml").read_text()
    )
    ref = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1] / "config" / "bcp_tc_ref_2018Q1_prior.yaml"
        ).read_text()
    )
    assert set(spread["series_b_weekly"].keys()) == set(WEEK_LABELS)
    assert set(ref["weekly_reference_rate"].keys()) == set(WEEK_LABELS)
