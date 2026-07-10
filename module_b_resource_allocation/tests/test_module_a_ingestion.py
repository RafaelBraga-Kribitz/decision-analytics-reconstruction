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


def _synthetic_seg_dept_with_uncertainty() -> pd.DataFrame:
    """The synthetic fixture plus v1.1.0 uncertainty columns (IMP-B02)."""
    df = _synthetic_seg_dept()
    df["participation_propensity_se"] = [0.10, 0.20, 0.05, float("nan")]
    for col in (
        "pct_internet_access_se",
        "mean_tv_penetration_se",
        "mean_radio_penetration_se",
        "mean_whatsapp_penetration_se",
    ):
        df[col] = [0.01, 0.01, 0.01, float("nan")]
    return df


def test_profile_propagates_propensity_uncertainty() -> None:
    """IMP-B02: the department profile carries a propagated interval, not a bare mean."""
    import numpy as np

    profile = department_media_profile(_synthetic_seg_dept_with_uncertainty())
    assert bool(profile["uncertainty_available"].iloc[0])
    assert profile["propensity_ci_low"].notna().all()
    assert profile["propensity_ci_high"].notna().all()
    assert (profile["propensity_ci_low"] <= profile["mean_participation_propensity"]).all()
    assert (profile["mean_participation_propensity"] <= profile["propensity_ci_high"]).all()
    # Hand-check Central: w=[3,1], se=[0.10,0.20] →
    # se_dept = sqrt((3*0.1)^2 + (1*0.2)^2)/4 = sqrt(0.13)/4
    se_dept = np.sqrt(0.13) / 4.0
    assert profile.loc["Central", "propensity_ci_low"] == pytest.approx(
        0.7 - 1.959963984540054 * se_dept, abs=1e-9
    )


def test_profile_degraded_flag_without_uncertainty_columns() -> None:
    """A stale pre-v1.1.0 artifact must be flagged, never treated as zero uncertainty."""
    profile = department_media_profile(_synthetic_seg_dept())
    assert not bool(profile["uncertainty_available"].iloc[0])
    assert profile["propensity_ci_low"].isna().all()
    assert profile["propensity_ci_high"].isna().all()


def test_inverted_interval_rejected() -> None:
    """IMP-B02 NFR: an inverted interval is a contract violation, not a warning."""
    from module_b_resource_allocation.features.module_a_ingestion import (
        validate_department_profile,
    )

    bad = pd.DataFrame(
        {
            "mean_participation_propensity": [0.5],
            "propensity_ci_low": [0.6],  # inverted: low > mean
            "propensity_ci_high": [0.7],
        },
        index=pd.Index(["Central"], name="department"),
    )
    with pytest.raises(ValueError, match="inverted propensity interval"):
        validate_department_profile(bad)


def test_feature_frame_discloses_propensity_source(tmp_path: Path) -> None:
    """The silent fillna(1.0) is gone: every row records its propensity source."""
    csv = tmp_path / "seg_dept.csv"
    _synthetic_seg_dept_with_uncertainty().to_csv(csv, index=False)
    df = build_allocation_features(module_a_reachability=csv)

    central = df[df["department"] == "Central"].iloc[0]
    assert central["dept_mean_propensity_source"] == "MODULE_A"
    assert central["dept_propensity_ci_low"] < central["dept_mean_propensity"]
    assert central["dept_mean_propensity"] < central["dept_propensity_ci_high"]

    itapua = df[df["department"] == "Itapua"].iloc[0]
    assert itapua["dept_mean_propensity_source"] == "NEUTRAL_FALLBACK"
    assert itapua["dept_mean_propensity"] == pytest.approx(1.0)
    assert pd.isna(itapua["dept_propensity_ci_low"])

    # Legacy artifact without uncertainty → degraded source label, never bare MODULE_A.
    legacy_csv = tmp_path / "legacy.csv"
    _synthetic_seg_dept().to_csv(legacy_csv, index=False)
    df_legacy = build_allocation_features(module_a_reachability=legacy_csv)
    central_legacy = df_legacy[df_legacy["department"] == "Central"].iloc[0]
    assert central_legacy["dept_mean_propensity_source"] == "MODULE_A_NO_UNCERTAINTY"

    # No Module A at all → disclosed neutral fallback everywhere.
    df_none = build_allocation_features(use_module_a=False)
    assert (df_none["dept_mean_propensity_source"] == "NEUTRAL_FALLBACK").all()


def _assert_perturbation_row(row: dict) -> None:  # type: ignore[type-arg]
    """One non-baseline diagnostic row: bound, width, region, delta all present."""
    assert row["bound"] in ("low", "high")
    assert row["interval_width"] > 0
    assert row["region"] in ("CHACO", "ORIENTAL")
    assert "dept_budget_delta_usd" in row


def test_input_noise_diagnostic_rows(tmp_path: Path) -> None:
    """IMP-B02: one row per (department with a non-trivial interval, bound) + baseline."""
    from module_b_resource_allocation.reporting.input_noise_sensitivity import (
        compute_input_noise_sensitivity,
    )

    csv = tmp_path / "seg_dept.csv"
    _synthetic_seg_dept_with_uncertainty().to_csv(csv, index=False)
    features = build_allocation_features(module_a_reachability=csv)

    rows = compute_input_noise_sensitivity(
        scenario_id="baseline",
        fx_series_id="series_b_weekly",
        solver_seed=20180422,
        features=features,
    )
    # Central + Boqueron carry intervals; the other 16 departments are
    # NEUTRAL_FALLBACK (no interval) and must be skipped, not zero-filled.
    by_dept = {r["department"] for r in rows}
    assert by_dept == {"baseline", "Central", "Boqueron"}
    assert len(rows) == 1 + 2 * 2
    assert rows[0]["bound"] == "baseline"
    for r in rows[1:]:
        _assert_perturbation_row(r)
    # Boqueron is a Chaco department — the fairness column must say so.
    assert {r["region"] for r in rows if r["department"] == "Boqueron"} == {"CHACO"}
