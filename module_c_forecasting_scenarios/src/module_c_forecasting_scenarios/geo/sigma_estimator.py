"""Estimate per-department idiosyncratic sigma for battleground v0.5.

Uses department-level poll-vs-result residuals (weighted by geographic granularity)
and a 2013↔2018 election cross-section floor (IMP-C05 / issue #63).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from module_b_resource_allocation.constants import DEPARTMENTS

from module_c_forecasting_scenarios.paths import repo_root

ESTIMATOR_VERSION = "sigma_estimator_v1"
MAD_SCALE = 1.4826

PROVENANCE_ESTIMATED = "estimated_from_reference"
PROVENANCE_FALLBACK = "estimated_from_election_cross_section_fallback"

_PROXY_WEIGHT_SCHEME = {
    "direct": 1.0,
    "regional_breakdown_only": 0.5,
    "regional_proxy": 0.25,
}

_DEFAULT_REFERENCE_DIR = repo_root() / "data" / "reference" / "battleground"
_TSJE_2018_PKG = (
    repo_root()
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "tsje_2018_department_results.csv"
)


@dataclass(frozen=True)
class SigmaEstimateResult:
    """Per-department sigma_idio estimates and manifest metadata."""

    sigma_by_department: dict[str, float]
    provenance_by_department: dict[str, str]
    n_obs_by_department: dict[str, int]
    reference_data_sha256: str
    sigma_floor_pp: float
    pooled_weighted_mad_pp: float


def battleground_reference_dir() -> Path:
    return _DEFAULT_REFERENCE_DIR


def _sha256_paths(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: x.name):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _dept_margin_pp(df: pd.DataFrame) -> pd.Series:
    total = df["abdo_anr_votes"] + df["alegre_ganar_votes"]
    margins = (df["abdo_anr_votes"] - df["alegre_ganar_votes"]) / total * 100.0
    if "department_ascii" in df.columns:
        return margins.set_axis(df["department_ascii"].astype(str), axis=0)
    return margins


def _load_tsje_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["abdo_anr_votes"] = df["abdo_anr_votes"].astype(int)
    df["alegre_ganar_votes"] = df["alegre_ganar_votes"].astype(int)
    return df


def validate_tsje_2013(df: pd.DataFrame) -> None:
    """National reconciliation gate for 2013 reference table."""
    if int(df["abdo_anr_votes"].sum()) != 1_104_169:
        raise ValueError("2013 TSJE abdo sum != 1,104,169")
    if int(df["alegre_ganar_votes"].sum()) != 889_451:
        raise ValueError("2013 TSJE alegre sum != 889,451")


def _poll_row_weight(notes: str) -> float:
    notes_l = (notes or "").lower()
    if "regional_proxy" in notes_l:
        return _PROXY_WEIGHT_SCHEME["regional_proxy"]
    if "regional_breakdown_only" in notes_l:
        return _PROXY_WEIGHT_SCHEME["regional_breakdown_only"]
    return _PROXY_WEIGHT_SCHEME["direct"]


def _weighted_mad(values: np.ndarray, weights: np.ndarray) -> float:
    if len(values) == 0:
        return float("nan")
    if len(values) == 1:
        return float(abs(values[0]))
    order = np.argsort(np.abs(values))
    v_sorted = np.abs(values)[order]
    w_sorted = weights[order]
    cum = np.cumsum(w_sorted)
    half = cum[-1] / 2.0
    idx = int(np.searchsorted(cum, half, side="left"))
    idx = min(idx, len(v_sorted) - 1)
    return float(v_sorted[idx])


def _election_sigma_floor(tsje_by_year: dict[int, pd.DataFrame]) -> float:
    """MAD of |margin_2018 - margin_2013| across departments present in both cycles."""
    years = sorted(tsje_by_year)
    if len(years) < 2:
        return 1.5
    y0, y1 = years[0], years[-1]
    m0 = _dept_margin_pp(tsje_by_year[y0]).rename("m0")
    m1 = _dept_margin_pp(tsje_by_year[y1]).rename("m1")
    merged = pd.concat([m0, m1], axis=1, join="inner").dropna()
    if merged.empty:
        return 1.5
    deltas = np.abs(merged["m1"].to_numpy() - merged["m0"].to_numpy())
    mad = _weighted_mad(deltas, np.ones(len(deltas)))
    return max(MAD_SCALE * mad, 0.5)


def _realized_margins_by_year(
    tsje_paths: dict[int, Path],
) -> dict[tuple[str, int], float]:
    out: dict[tuple[str, int], float] = {}
    for year, path in tsje_paths.items():
        df = _load_tsje_csv(path)
        if year == 2013:
            validate_tsje_2013(df)
        margins = _dept_margin_pp(df)
        for dept, m in margins.items():
            out[(str(dept), year)] = float(m)
    return out


def _poll_residuals(polls: pd.DataFrame, realized: dict[tuple[str, int], float]) -> pd.DataFrame:
    out = polls.copy()
    out["election_year"] = out["election_year"].astype(int)
    out["residual_pp"] = out.apply(
        lambda r: float(r["margin_pp_poll"])
        - realized.get((str(r["department_ascii"]), int(r["election_year"])), float("nan")),
        axis=1,
    )
    out["weight"] = out["notes"].fillna("").map(_poll_row_weight)
    return out.dropna(subset=["residual_pp"])


def _dept_sigma_from_polls(
    polls: pd.DataFrame,
    sigma_floor: float,
    pooled_mad: float,
) -> tuple[dict[str, float], dict[str, str], dict[str, int]]:
    sigma_by_department: dict[str, float] = {}
    provenance_by_department: dict[str, str] = {}
    n_obs_by_department: dict[str, int] = {}
    for dept in DEPARTMENTS:
        sub = polls[polls["department_ascii"] == dept]
        n_obs = len(sub)
        n_obs_by_department[dept] = n_obs
        if n_obs >= 1:
            w = np.asarray(sub["weight"], dtype=float)
            eff = float(w.sum())
            if eff >= 1.0:
                residuals = np.asarray(sub["residual_pp"], dtype=float)
                sigma_poll = MAD_SCALE * _weighted_mad(residuals, w)
            else:
                sigma_poll = pooled_mad
            sigma = max(sigma_poll, sigma_floor)
            provenance_by_department[dept] = PROVENANCE_ESTIMATED
        else:
            sigma = sigma_floor
            provenance_by_department[dept] = PROVENANCE_FALLBACK
        sigma_by_department[dept] = float(sigma)
    return sigma_by_department, provenance_by_department, n_obs_by_department


def _overall_sigma_provenance(provs: dict[str, str]) -> str:
    if all(p == PROVENANCE_ESTIMATED for p in provs.values()):
        return PROVENANCE_ESTIMATED
    if any(p == PROVENANCE_ESTIMATED for p in provs.values()):
        return "estimated_from_reference_mixed"
    return PROVENANCE_FALLBACK


def estimate_sigma_idio(
    reference_dir: Path | None = None,
) -> SigmaEstimateResult:
    """Compute per-department σ_idio (pp) from reference poll and TSJE data."""
    ref = reference_dir or battleground_reference_dir()
    poll_path = ref / "dept_poll_margins.csv"
    tsje_2013_path = ref / "tsje_2013_department_results.csv"
    if not poll_path.is_file():
        raise FileNotFoundError(f"Missing poll reference: {poll_path}")
    if not tsje_2013_path.is_file():
        raise FileNotFoundError(f"Missing 2013 TSJE reference: {tsje_2013_path}")
    if not _TSJE_2018_PKG.is_file():
        raise FileNotFoundError(f"Missing 2018 TSJE package data: {_TSJE_2018_PKG}")

    tsje_paths = {2013: tsje_2013_path, 2018: _TSJE_2018_PKG}
    tsje_by_year = {y: _load_tsje_csv(p) for y, p in tsje_paths.items()}
    realized = _realized_margins_by_year(tsje_paths)
    sigma_floor = _election_sigma_floor(tsje_by_year)

    polls = _poll_residuals(pd.read_csv(poll_path), realized)
    residuals = np.asarray(polls["residual_pp"], dtype=float)
    weights = np.asarray(polls["weight"], dtype=float)
    pooled_mad = MAD_SCALE * _weighted_mad(residuals, weights)

    sigma_by_department, provenance_by_department, n_obs_by_department = _dept_sigma_from_polls(
        polls, sigma_floor, pooled_mad
    )
    ref_hash = _sha256_paths(poll_path, tsje_2013_path, _TSJE_2018_PKG)

    return SigmaEstimateResult(
        sigma_by_department=sigma_by_department,
        provenance_by_department=provenance_by_department,
        n_obs_by_department=n_obs_by_department,
        reference_data_sha256=ref_hash,
        sigma_floor_pp=sigma_floor,
        pooled_weighted_mad_pp=pooled_mad,
    )


def write_sigma_yaml(result: SigmaEstimateResult, out_path: Path) -> Path:
    """Persist estimator output for heatmap.py and manifest consumers."""
    payload: dict[str, Any] = {
        "estimator_version": ESTIMATOR_VERSION,
        "reference_data_sha256": result.reference_data_sha256,
        "sigma_floor_pp": result.sigma_floor_pp,
        "pooled_weighted_mad_pp": result.pooled_weighted_mad_pp,
        "proxy_weight_scheme": _PROXY_WEIGHT_SCHEME,
        "departments": {
            dept: {
                "sigma_idio_pp": result.sigma_by_department[dept],
                "provenance": result.provenance_by_department[dept],
                "n_poll_obs": result.n_obs_by_department[dept],
            }
            for dept in DEPARTMENTS
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


def load_sigma_yaml(path: Path | None = None) -> dict[str, float]:
    """Load per-department sigma_idio_pp from yaml; fallback to reference dir default."""
    yaml_path = path or (battleground_reference_dir() / "battleground_sigma_idio.yaml")
    if not yaml_path.is_file():
        result = estimate_sigma_idio()
        write_sigma_yaml(result, yaml_path)
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    depts = data.get("departments", {})
    return {str(k): float(v["sigma_idio_pp"]) for k, v in depts.items()}


def load_sigma_manifest_extras(
    path: Path | None = None,
) -> dict[str, Any]:  # Any: yaml manifest blob
    """Return manifest fields derived from the sigma yaml."""
    yaml_path = path or (battleground_reference_dir() / "battleground_sigma_idio.yaml")
    if not yaml_path.is_file():
        result = estimate_sigma_idio()
        write_sigma_yaml(result, yaml_path)
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    provs = {d: info["provenance"] for d, info in data.get("departments", {}).items()}
    overall = _overall_sigma_provenance(provs)
    return {
        "sigma_idio_provenance": overall,
        "sigma_estimator_version": data.get("estimator_version", ESTIMATOR_VERSION),
        "reference_data_sha256": data.get("reference_data_sha256", ""),
        "sigma_floor_pp": data.get("sigma_floor_pp"),
        "proxy_weight_scheme": data.get("proxy_weight_scheme", _PROXY_WEIGHT_SCHEME),
        "n_obs_per_department": {
            d: info.get("n_poll_obs", 0) for d, info in data.get("departments", {}).items()
        },
        "sigma_idio_by_department": {
            d: info.get("sigma_idio_pp") for d, info in data.get("departments", {}).items()
        },
    }


def run_sigma_estimation_and_write(
    reference_dir: Path | None = None,
    out_yaml: Path | None = None,
) -> SigmaEstimateResult:
    """Estimate σ and write battleground_sigma_idio.yaml (pipeline entry)."""
    ref = reference_dir or battleground_reference_dir()
    out = out_yaml or (ref / "battleground_sigma_idio.yaml")
    result = estimate_sigma_idio(ref)
    write_sigma_yaml(result, out)
    return result


if __name__ == "__main__":
    res = run_sigma_estimation_and_write()
    payload = {"sigma_floor_pp": res.sigma_floor_pp, "departments": res.sigma_by_department}
    print(json.dumps(payload, indent=2))
