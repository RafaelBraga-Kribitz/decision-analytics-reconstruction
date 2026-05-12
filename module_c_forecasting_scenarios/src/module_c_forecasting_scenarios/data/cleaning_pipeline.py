"""Eight-step cleaning: validate → pollster → prefs → undecided → field window →
transparency → dedupe → split tracking vs exit.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import yaml

from module_c_forecasting_scenarios.data.exceptions import QAGateFailure
from module_c_forecasting_scenarios.data.transparency import (
    compute_phi_transparency,
    compute_tau_eff,
)
from module_c_forecasting_scenarios.features.herding_weights import rho_herd_for_row
from module_c_forecasting_scenarios.features.shock_scores import (
    scenario_bucket_for_margin,
    shock_score_s,
)
from module_c_forecasting_scenarios.features.taxonomy_tables import normalize_pollster_id
from module_c_forecasting_scenarios.paths import module_config_dir

REQUIRED_RAW = (
    "poll_raw_id",
    "publication_date",
    "pollster_display_name",
    "has_ficha",
    "wave_type",
)


def _redistribute_ab(a: float, b: float, und: float | None, rule: str) -> tuple[float, float, str]:
    if und is None or (isinstance(und, float) and pd.isna(und)):
        und = 0.0
    if rule == "exclude":
        return a, b, "exclude"
    if rule == "redistribute_third_party":
        s = a + b + und
        if s <= 0:
            return 50.0, 50.0, "redistribute_third_party"
        return 100.0 * a / s, 100.0 * b / s, "redistribute_third_party"
    # proportional_AB among stated
    s2 = a + b
    if s2 <= 0:
        return 50.0, 50.0, "proportional_AB"
    rem = 100.0 - und
    return rem * a / s2, rem * b / s2, "proportional_AB"


def _load_m_star(calibration_series: str) -> float:
    with open(module_config_dir() / "calibration.yaml") as f:
        cal = yaml.safe_load(f)
    s = str(calibration_series).strip().upper()
    return float(cal["anchors"][s]["margin_m_star_pp"])


def clean_raw_polls(
    raw: pd.DataFrame,
    calibration_series: str,
    *,
    default_redistribution: str = "proportional_AB",
    m_star_pp: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = [c for c in REQUIRED_RAW if c not in raw.columns]
    if missing:
        raise QAGateFailure(f"raw polls missing {missing}")

    m_star = float(m_star_pp) if m_star_pp is not None else _load_m_star(calibration_series)

    rows: list[dict] = []
    for _, r in raw.iterrows():
        pub = r["publication_date"]
        if hasattr(pub, "date"):
            pub = pub.date()
        pollster_id, bias_fam = normalize_pollster_id(str(r["pollster_display_name"]))
        a = float(r["preference_proxy_a_pct"]) if pd.notna(r.get("preference_proxy_a_pct")) else 0.0
        b = float(r["preference_proxy_b_pct"]) if pd.notna(r.get("preference_proxy_b_pct")) else 0.0
        und = r.get("undecided_pct")
        und_f = float(und) if pd.notna(und) else None
        a2, b2, rule = _redistribute_ab(a, b, und_f, default_redistribution)
        fw_known = bool(r.get("field_window_known", False))
        if fw_known and pd.notna(r.get("field_window_start")):
            fws = pd.to_datetime(r["field_window_start"]).date()
            fwe = pd.to_datetime(r["field_window_end"]).date()
        else:
            fwe = pub
            fws = pub - timedelta(days=7)
        sample_size_known = bool(r.get("sample_size_known", False))
        mode_known = bool(r.get("mode_known", False))
        phi = compute_phi_transparency(
            bool(r["has_ficha"]),
            sample_size_known,
            fw_known or True,
            mode_known,
        )
        tau = compute_tau_eff(phi)
        wave = str(r["wave_type"]).strip().lower()
        if wave not in {"tracking", "exit"}:
            raise QAGateFailure(f"invalid wave_type {wave!r}")
        carrier = r.get("conglomerate_carrier")
        carrier_s = None if pd.isna(carrier) else str(carrier)
        oea = r.get("oea_timing_compliant")
        oea_b = bool(oea) if pd.notna(oea) else None
        eu = r.get("eu_release_window_flag")
        eu_b = bool(eu) if pd.notna(eu) else None
        row = {
            "poll_wave_id": str(r["poll_raw_id"]).replace("raw_", "wave_"),
            "pollster_id": pollster_id,
            "pollster_bias_family": bias_fam,
            "publication_date": pub,
            "field_window_start": fws,
            "field_window_end": fwe,
            "preference_proxy_a_pct": a2,
            "preference_proxy_b_pct": b2,
            "m_poll_pp": a2 - b2,
            "redistribution_rule": rule,
            "phi_transparency": phi,
            "tau_eff": tau,
            "calibration_series": calibration_series,
            "series_tag": calibration_series,
            "conglomerate_id": carrier_s,
            "media_holding": carrier_s,
            "sample_size_known": sample_size_known,
            "firm_wave_month": f"{pub.year:04d}-{pub.month:02d}",
            "wave_type": wave,
            "oea_timing_compliant": oea_b,
            "eu_release_window_flag": eu_b,
            "has_ficha": bool(r["has_ficha"]),
        }
        rho = rho_herd_for_row(pub, carrier_s)
        row["scenario_bucket"] = scenario_bucket_for_margin(row["m_poll_pp"], m_star, phi, rho)
        rows.append(row)

    all_df = pd.DataFrame(rows)
    all_df = all_df.drop_duplicates(subset=["pollster_id", "publication_date"], keep="first")
    track_part = all_df[all_df["wave_type"] == "tracking"].drop(columns=["wave_type"]).copy()
    exit_part = all_df[all_df["wave_type"] == "exit"].copy()
    if len(track_part):
        track_part = attach_shock_scores(track_part.reset_index(drop=True), m_star)
    else:
        track_part = pd.DataFrame()
    exit_keep = [
        "poll_wave_id",
        "pollster_id",
        "publication_date",
        "field_window_start",
        "field_window_end",
        "preference_proxy_a_pct",
        "preference_proxy_b_pct",
        "m_poll_pp",
        "oea_timing_compliant",
        "eu_release_window_flag",
        "calibration_series",
    ]
    if len(exit_part):
        exit_df = exit_part[exit_keep].reset_index(drop=True)
    else:
        exit_df = pd.DataFrame.from_records([], columns=exit_keep)
    tracking = track_part.reset_index(drop=True)
    return tracking, exit_df


def attach_shock_scores(tracking: pd.DataFrame, m_star_pp: float) -> pd.DataFrame:
    out = tracking.copy()
    scores = []
    for _, r in out.iterrows():
        pub = pd.Timestamp(r["publication_date"]).date()
        s = shock_score_s(
            float(r["m_poll_pp"]),
            m_star_pp,
            float(r["phi_transparency"]),
            pub,
            r.get("conglomerate_id"),
        )
        scores.append(s)
    out["shock_score_s"] = scores
    return out
