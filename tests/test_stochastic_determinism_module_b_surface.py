"""Regression: primary Module B stochastic surfaces are seed-stable (§4 line 75 gate)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from module_b_resource_allocation.data.dirty_generator import DirtyGenConfig, generate_all


def test_build_cost_matrix_reproducible_for_fixed_seed() -> None:
    from module_b_resource_allocation.routing.cost_matrix import build_cost_matrix

    a = build_cost_matrix("dry_standard", seed=12345)
    b = build_cost_matrix("dry_standard", seed=12345)
    pd.testing.assert_frame_equal(a, b)


def test_nearest_insertion_tour_reproducible_for_fixed_seed() -> None:
    from module_b_resource_allocation.routing.nearest_insertion import nearest_insertion_tour

    dist = {(i, j): abs(i - j) * 10.0 for i in range(6) for j in range(6)}
    tour_a, len_a = nearest_insertion_tour(nodes=list(range(6)), dist=dist, seed=777)
    tour_b, len_b = nearest_insertion_tour(nodes=list(range(6)), dist=dist, seed=777)
    assert tour_a == tour_b
    assert len_a == len_b


def test_generate_all_csvs_reproducible_for_fixed_cfg_seed() -> None:
    cfg = DirtyGenConfig(
        n_budget_rows=60,
        n_volunteer_rows=60,
        n_media_rows=60,
        seed=424_242,
        null_rate=0.08,
        duplicate_rate=0.04,
        locale_swap_rate=0.2,
        currency_swap_rate=0.2,
    )

    def bundle_text(root: Path) -> tuple[str, str, str]:
        return (
            (root / "budget_lines_raw.csv").read_text(encoding="utf-8"),
            (root / "volunteer_logs_raw.csv").read_text(encoding="utf-8"),
            (root / "media_buy_sheet_raw.csv").read_text(encoding="utf-8"),
        )

    with TemporaryDirectory() as d1, TemporaryDirectory() as d2:
        p1 = Path(d1)
        p2 = Path(d2)
        generate_all(cfg, p1)
        generate_all(cfg, p2)
        assert bundle_text(p1) == bundle_text(p2)
