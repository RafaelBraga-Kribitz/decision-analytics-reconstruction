"""Unit tests for ``module_b_resource_allocation.pipeline.run_allocation._parse_args``."""

from __future__ import annotations

from pathlib import Path

from module_b_resource_allocation.pipeline.run_allocation import _parse_args


def test_parse_args_requires_out_dir() -> None:
    ns = _parse_args(["--out-dir", "/tmp/module_b_out"])
    assert ns.scenario == "baseline"
    assert ns.fx_series == "series_b_weekly"
    assert ns.seed == 20180422
    assert ns.out_dir == Path("/tmp/module_b_out")
    assert ns.counterfactual is False


def test_parse_args_overrides() -> None:
    ns = _parse_args(
        [
            "--out-dir",
            "/tmp/out",
            "--scenario",
            "early_lock",
            "--fx-series",
            "series_a_monthly",
            "--seed",
            "99",
            "--counterfactual",
        ]
    )
    assert ns.scenario == "early_lock"
    assert ns.fx_series == "series_a_monthly"
    assert ns.seed == 99
    assert ns.counterfactual is True
