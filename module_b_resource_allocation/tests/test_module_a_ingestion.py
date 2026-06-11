"""A→B ingestion gates (F-038).

Module B's feature frame must consume Module A's measured reachability and
propensity artifacts when present — not just YAML priors — and must degrade
gracefully (priors + uniform propensity weight) when absent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from module_b_resource_allocation.features.module_a_ingestion import (
    CHANNEL_PENETRATION_SOURCE,
    DEFAULT_REACHABILITY_CSV,
    department_media_profile,
    load_segment_department_reachability,
)
from module_b_resource_allocation.models.feature_join import build_allocation_features


def _synthetic_seg_dept() -> pd.DataFrame:
    """Two departments, two segments each, with hand-computable weighted means."""
    return pd.DataFrame(
        [
            # Central: weights 3/1 → tv = (0.9*3 + 0.5*1)/4 = 0.8
            {
                "segment_label": "rural_committed",
                "department": "Central",
                "segment_size": 3,
                "mean_participation_propensity": 0.8,
                "pct_internet_access": 0.6,
                "mean_tv_penetration": 0.9,
                "mean_radio_penetration": 0.7,
                "mean_whatsapp_penetration": 0.5,
            },
            {
                "segment_label": "youth_volatile",
                "department": "Central",
                "segment_size": 1,
                "mean_participation_propensity": 0.4,
                "pct_internet_access": 0.8,
                "mean_tv_penetration": 0.5,
                "mean_radio_penetration": 0.5,
                "mean_whatsapp_penetration": 0.9,
            },
            # Boqueron: single populated cell.
            {
                "segment_label": "rural_committed",
                "department": "Boqueron",
                "segment_size": 5,
                "mean_participation_propensity": 0.55,
                "pct_internet_access": 0.3,
                "mean_tv_penetration": 0.6,
                "mean_radio_penetration": 0.7,
                "mean_whatsapp_penetration": 0.35,
            },
            # Empty dense-grid cell must not poison the averages.
            {
                "segment_label": "youth_volatile",
                "department": "Boqueron",
                "segment_size": 0,
                "mean_participation_propensity": float("nan"),
                "pct_internet_access": float("nan"),
                "mean_tv_penetration": float("nan"),
                "mean_radio_penetration": float("nan"),
                "mean_whatsapp_penetration": float("nan"),
            },
        ]
    )


def test_department_media_profile_weighted_means() -> None:
    profile = department_media_profile(_synthetic_seg_dept())
    assert profile.loc["Central", "tv_penetration"] == pytest.approx(0.8)
    assert profile.loc["Central", "whatsapp_penetration"] == pytest.approx(0.6)
    assert profile.loc["Central", "mean_participation_propensity"] == pytest.approx(0.7)
    # Single-cell department passes through; NaN cell excluded.
    assert profile.loc["Boqueron", "tv_penetration"] == pytest.approx(0.6)
    assert profile.loc["Boqueron", "mean_participation_propensity"] == pytest.approx(0.55)


def test_loader_returns_none_when_artifact_missing(tmp_path: Path) -> None:
    assert load_segment_department_reachability(tmp_path / "nope.csv") is None


def test_loader_rejects_malformed_artifact(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"department": ["Central"]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_segment_department_reachability(bad)


def test_feature_frame_ingests_module_a_overrides(tmp_path: Path) -> None:
    csv = tmp_path / "seg_dept.csv"
    _synthetic_seg_dept().to_csv(csv, index=False)
    df = build_allocation_features(module_a_reachability=csv)

    central_tv = df[(df["department"] == "Central") & (df["channel"] == "tv_spots")].iloc[0]
    assert central_tv["reach_cap_share"] == pytest.approx(0.8)
    assert central_tv["provenance"] == "MODULE_A"
    assert central_tv["dept_mean_propensity"] == pytest.approx(0.7)

    # reachable_audience must be recomputed from the measured cap.
    assert central_tv["reachable_audience"] > 0

    # Channels Module A does not measure keep their YAML priors.
    central_sms = df[(df["department"] == "Central") & (df["channel"] == "sms")].iloc[0]
    assert central_sms["provenance"] != "MODULE_A"

    # Departments absent from the artifact keep priors but get the uniform weight.
    itapua_tv = df[(df["department"] == "Itapua") & (df["channel"] == "tv_spots")].iloc[0]
    assert itapua_tv["provenance"] != "MODULE_A"
    assert itapua_tv["dept_mean_propensity"] == pytest.approx(1.0)


def test_feature_frame_fallback_without_module_a() -> None:
    df = build_allocation_features(use_module_a=False)
    assert (df["dept_mean_propensity"] == 1.0).all()
    assert not (df["provenance"] == "MODULE_A").any()


@pytest.mark.skipif(
    not DEFAULT_REACHABILITY_CSV.exists(),
    reason="Module A artifact not generated (run `dvc repro module_a`)",
)
def test_default_feature_frame_uses_real_module_a_artifact() -> None:
    df = build_allocation_features()
    module_a_rows = df[df["provenance"] == "MODULE_A"]
    assert set(module_a_rows["channel"].unique()) == set(CHANNEL_PENETRATION_SOURCE)
    # Propensity weights must be measured (not the uniform fallback) and sane.
    assert df["dept_mean_propensity"].between(0.3, 1.0).all()
    assert (df["dept_mean_propensity"] < 1.0).any()
