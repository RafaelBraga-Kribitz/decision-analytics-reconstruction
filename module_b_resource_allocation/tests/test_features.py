"""TDD tests for Module B feature engineering (Phase 6).

Covers: reach caps, salience multipliers, diminishing returns curves,
district tier clustering, and department → region tagging.
"""

from __future__ import annotations

from module_b_resource_allocation.constants import (
    CHANNEL_NAMES,
    DEPARTMENTS,
    N_DEPARTMENTS,
    REACH_CAPS_ROWS,
)

# ---------------------------------------------------------------------------
# Reach caps
# ---------------------------------------------------------------------------


def test_reach_caps_row_count() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert len(df) == REACH_CAPS_ROWS, f"Expected {REACH_CAPS_ROWS} rows (18×11), got {len(df)}"


def test_reach_caps_unique_key() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert not df.duplicated(["department", "channel"]).any()


def test_reach_caps_all_departments_and_channels() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert set(df["department"].unique()) == set(DEPARTMENTS)
    assert set(df["channel"].unique()) == set(CHANNEL_NAMES)


def test_reach_caps_share_in_unit_interval() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert df["reach_cap_share"].between(0.0, 1.0).all()


def test_reach_caps_chaco_tv_below_oriental() -> None:
    """Chaco FTA TV reach must be lower than Asunción (98%)."""
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    chaco_tv = df[(df["department"] == "Presidente Hayes") & (df["channel"] == "tv_spots")][
        "reach_cap_share"
    ].iloc[0]
    asuncion_tv = df[(df["department"] == "Asuncion") & (df["channel"] == "tv_spots")][
        "reach_cap_share"
    ].iloc[0]
    assert chaco_tv < asuncion_tv, f"Chaco TV ({chaco_tv}) should be < Asunción TV ({asuncion_tv})"


def test_reach_caps_pay_tv_only_in_eligible_depts() -> None:
    """Pay TV eligible flag must be True only for Asunción, Central, Alto Parana."""
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    eligible_depts = {"Asuncion", "Central", "Alto Parana"}
    tv_rows = df[df["channel"] == "tv_spots"]
    # Non-eligible departments should have very low or zero effective cap via pay_tv_eligible=False
    non_elig = tv_rows[~tv_rows["department"].isin(eligible_depts)]
    # Verify pay_tv_eligible column exists and is correct
    assert "pay_tv_eligible" in df.columns
    assert tv_rows[tv_rows["department"].isin(eligible_depts)]["pay_tv_eligible"].all()
    assert not non_elig["pay_tv_eligible"].any()


def test_reach_caps_region_column_values() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert set(df["region"].unique()) == {"ORIENTAL", "CHACO"}


def test_reach_caps_provenance_column_values() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    assert "provenance" in df.columns
    assert set(df["provenance"].unique()).issubset({"VERIFIED", "PRIOR", "ESTIMATED"})


# ---------------------------------------------------------------------------
# Salience + attention multipliers
# ---------------------------------------------------------------------------


def test_radio_salience_applied() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    radio_rows = df[df["channel"] == "radio_spots"]
    # Plan §4.4: ψ_radio = 0.2148 (salience relative to TV), α_radio_ad = 0.57
    assert (radio_rows["salience_multiplier"] - 0.2148).abs().lt(0.01).all()
    assert (radio_rows["attention_multiplier"] - 0.57).abs().lt(0.01).all()


def test_tv_salience_applied() -> None:
    from module_b_resource_allocation.features.reach_caps import build_reach_caps

    df = build_reach_caps()
    tv_rows = df[df["channel"] == "tv_spots"]
    assert (tv_rows["salience_multiplier"] - 0.1290).abs().lt(0.01).all()


# ---------------------------------------------------------------------------
# Diminishing returns
# ---------------------------------------------------------------------------


def test_diminishing_returns_row_count() -> None:
    from module_b_resource_allocation.features.diminishing_returns import build_dr_params

    df = build_dr_params()
    assert len(df) == REACH_CAPS_ROWS


def test_diminishing_returns_required_columns() -> None:
    from module_b_resource_allocation.features.diminishing_returns import build_dr_params

    df = build_dr_params()
    for col in ["department", "channel", "k_shape", "inflection_pct", "breakpoints_usd"]:
        assert col in df.columns, f"Missing column: {col}"


def test_diminishing_returns_inflection_in_unit_interval() -> None:
    from module_b_resource_allocation.features.diminishing_returns import build_dr_params

    df = build_dr_params()
    assert df["inflection_pct"].between(0.0, 1.0).all()


def test_diminishing_returns_k_breakpoints_is_6() -> None:
    """Each row must have K=6 breakpoints (plan §6.2)."""
    from module_b_resource_allocation.features.diminishing_returns import build_dr_params

    df = build_dr_params()
    assert df["breakpoints_usd"].map(len).eq(6).all()


# ---------------------------------------------------------------------------
# District tier clustering
# ---------------------------------------------------------------------------


def test_district_tiers_row_count() -> None:
    from module_b_resource_allocation.features.district_tiers import build_district_tiers

    df = build_district_tiers()
    assert len(df) == N_DEPARTMENTS


def test_district_tiers_valid_values() -> None:
    from module_b_resource_allocation.features.district_tiers import build_district_tiers

    df = build_district_tiers()
    allowed = {"stronghold", "swing", "opposition", "negligible"}
    assert set(df["department_tier"].unique()).issubset(allowed)


def test_district_tiers_four_categories_present() -> None:
    from module_b_resource_allocation.features.district_tiers import build_district_tiers

    df = build_district_tiers()
    assert (
        len(df["department_tier"].unique()) == 4
    ), "Expected all 4 tiers (stronghold, swing, opposition, negligible)"


def test_district_tiers_chaco_not_all_stronghold() -> None:
    from module_b_resource_allocation.features.district_tiers import build_district_tiers

    df = build_district_tiers()
    chaco = df[df["department"].isin(["Presidente Hayes", "Boqueron", "Alto Paraguay"])]
    assert not (
        chaco["department_tier"] == "stronghold"
    ).all(), "Chaco departments should not all be stronghold"
