"""Unit tests for ``module_b_resource_allocation.models.feature_join`` private helpers."""

from __future__ import annotations

from module_b_resource_allocation.constants import CHANNEL_NAMES, DEPARTMENTS
from module_b_resource_allocation.models.feature_join import (
    _channel_unit_costs_pyg,
    _department_population,
    _load_yaml,
)


def test_load_yaml_reads_known_config() -> None:
    cfg = _load_yaml("channel_unit_costs_pyg.yaml")
    assert "channels" in cfg
    assert "tv_spots" in cfg["channels"]


def test_channel_unit_costs_pyg_matches_channels() -> None:
    costs = _channel_unit_costs_pyg()
    assert set(costs.keys()) == set(CHANNEL_NAMES)
    for _ch, (pyg, tier) in costs.items():
        assert pyg > 0
        assert tier in {"REF", "RETAIL"}


def test_department_population_covers_all_departments() -> None:
    pop = _department_population()
    assert set(pop.keys()) == set(DEPARTMENTS)
    assert all(v > 0 for v in pop.values())
