# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
# pandas-stubs 2.x does not provide complete return-type annotations for
# chained Series operations (.str.*, .fillna, .astype, .groupby().agg) in strict mode.
"""Cleaning pipeline for Module A raw population data."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from population_segmentation.evaluation.schema_validator import validate_clean_population
from population_segmentation.utils.schema import (
    CANONICAL_DEPARTMENTS,
    CANONICAL_ENC_SOURCE,
    ENC_SOURCE,
    ENC_SOURCE_RAW,
)
from population_segmentation.utils.seeds import make_rng

_DEPT_NORMALIZE = {
    "Cordilera": "Cordillera",
    "cordillera": "Cordillera",
    "Caaguazú": "Caaguazu",
    "Caguazu": "Caaguazu",
    "Caaguaçu": "Caaguazu",
    "Misione": "Misiones",
    "misions": "Misiones",
    "Cazapa": "Caazapa",
    "Caasapa": "Caazapa",
    "Caazapá": "Caazapa",
    "Canidenyu": "Canindeyu",
    "Caindeyú": "Canindeyu",
    "Concepción": "Concepcion",
    "Consepcion": "Concepcion",
    "concepcion": "Concepcion",
    "Paraguarí": "Paraguari",
    "Paraguarry": "Paraguari",
    "paraguari": "Paraguari",
    "Itapúa": "Itapua",
    "Itapuá": "Itapua",
    "itapua": "Itapua",
    "Ñeembucú": "Neembucu",
    "Neembuku": "Neembucu",
    "neembucu": "Neembucu",
    "Amambai": "Amambay",
    "amambay": "Amambay",
    "Amambáy": "Amambay",
}

_GENDER_MAP = {
    "M": "M",
    "m": "M",
    "Masculino": "M",
    "MASCULINO": "M",
    "1": "M",
    "F": "F",
    "f": "F",
    "Femenino": "F",
    "FEMENINO": "F",
    "2": "F",
}

# Fallback written for a DOB that cannot be parsed. Every use is flagged in
# ``dob_imputed`` and counted in the QA report (F-087 / IMP-A04), so the
# resulting age spike is never mistaken for real 1980 births.
_DOB_FALLBACK = "01/01/1980"
AGE_MIN, AGE_MAX = 18, 115

_LANGUAGE_IMPUTATION_KEYS = (
    "jopara_bilingual",
    "guarani_only",
    "spanish_only",
    "other",
)


def _language_imputation_labels_and_probs(config: dict[str, Any]) -> tuple[list[str], np.ndarray]:
    """Canonical labels and a normalised probability vector for language bucket imputation."""
    lp: dict[str, Any] = config.get("language_priors") or {}
    probs = np.array(
        [float(lp.get(k, 0.0)) for k in _LANGUAGE_IMPUTATION_KEYS],
        dtype=np.float64,
    )
    total = float(probs.sum())
    if total <= 0.0:
        n_keys = len(_LANGUAGE_IMPUTATION_KEYS)
        probs = np.ones(n_keys, dtype=np.float64) / n_keys
    else:
        probs = probs / total
    return list(_LANGUAGE_IMPUTATION_KEYS), probs


def _apply_encoding_provenance(df: pd.DataFrame) -> pd.DataFrame:
    if ENC_SOURCE_RAW in df.columns:
        raw_tags = df[ENC_SOURCE_RAW].fillna("unknown").astype(str).str.strip().str.lower()
        df[ENC_SOURCE] = raw_tags.where(raw_tags.isin(CANONICAL_ENC_SOURCE), "unknown")
        df = df.drop(columns=[ENC_SOURCE_RAW])
    elif ENC_SOURCE not in df.columns:
        df[ENC_SOURCE] = "utf8"
    return df


def _standardize_cedula_and_gender(df: pd.DataFrame) -> None:
    df["cedula"] = df["cedula"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(8).str[-8:]
    df["cedula_invalid"] = ~df["cedula"].str.match(r"^\d{8}$")
    df["gender"] = df["gender"].replace(_GENDER_MAP).fillna("unknown")


def _normalize_departments_and_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    dept = df["department"].astype(str).str.strip()
    df["department"] = dept.replace(_DEPT_NORMALIZE)
    df.loc[~df["department"].isin(list(CANONICAL_DEPARTMENTS)), "department"] = "Central"
    df = df.sort_values("entity_id").drop_duplicates(subset=["entity_id", "cedula"], keep="first")
    return df.drop_duplicates(subset=["entity_id"], keep="first")


def _derive_age_from_dob(df: pd.DataFrame) -> None:
    dob_series, dob_imputed = _normalize_dob(pd.Series(df["dob"].astype(str)))
    df["dob"] = dob_series
    df["dob_imputed"] = dob_imputed
    event_date = pd.Timestamp("2018-04-22")
    dob_parsed = pd.to_datetime(df["dob"], format="%d/%m/%Y", errors="coerce")
    age = ((event_date - dob_parsed).dt.days / 365.25).fillna(0).astype(int)
    df["age_on_event_date"] = age
    df["dob_ambiguous"] = dob_parsed.isna()
    # Flag before clamping: the [AGE_MIN, AGE_MAX] checks in validator.py and
    # schema_validator.py are post-conditions of this clamp (schema contract),
    # not independent plausibility gates; the pre-clamp rate is in the QA report.
    df["age_out_of_range"] = ~df["age_on_event_date"].between(AGE_MIN, AGE_MAX)
    df.loc[df["age_on_event_date"] < AGE_MIN, "age_on_event_date"] = AGE_MIN
    df.loc[df["age_on_event_date"] > AGE_MAX, "age_on_event_date"] = AGE_MAX


def _impute_municipalities(df: pd.DataFrame) -> None:
    df["municipality_imputed"] = df["municipality"].isna()
    dept_mode = (
        df.dropna(subset=["municipality"])
        .groupby("department")["municipality"]
        .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "Unknown")
    )
    null_idx = df["municipality"].isna()
    df.loc[null_idx, "municipality"] = (
        df.loc[null_idx, "department"].map(dept_mode).fillna("Unknown")
    )


def _canonicalize_phone(df: pd.DataFrame) -> None:
    df["phone"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True)
    df["phone"] = df["phone"].str[-9:]
    df["phone"] = "+595" + df["phone"]
    df["phone_invalid"] = ~df["phone"].str.match(r"^\+595\d{9}$")


def _ensure_rural_flag(df: pd.DataFrame, config: dict[str, Any], rng: np.random.Generator) -> None:
    """Impute a missing ``rural_flag`` per department, as the generator does.

    Each entity is rural with probability ``1 - department_urban_share[dept]``;
    departments absent from the table fall back to the national anchor
    ``cleaner_synthetic_defaults.rural_flag_true_rate``. A flat national draw
    would erase the 1.00 (Asuncion) to 0.24 (Canindeyu) urban-share spread.
    """
    df.attrs["rural_flag_imputed"] = "rural_flag" not in df.columns
    if df.attrs["rural_flag_imputed"]:
        csd: dict[str, Any] = config.get("cleaner_synthetic_defaults") or {}
        national_urban = 1.0 - float(csd.get("rural_flag_true_rate", 0.383))
        urban_share: dict[str, float] = config.get("department_urban_share") or {}
        p_urban = (
            df["department"]
            .map(lambda d: urban_share.get(str(d), national_urban))
            .to_numpy(dtype=float)
        )
        df["rural_flag"] = rng.random(len(df)) >= p_urban
    df["rural_flag"] = df["rural_flag"].fillna(False).astype(bool)
    df["rural_flag_derived"] = True


def _ensure_language_bucket(
    df: pd.DataFrame, config: dict[str, Any], rng: np.random.Generator
) -> None:
    if "language_census_bucket" not in df.columns:
        labels, probs = _language_imputation_labels_and_probs(config)
        df["language_census_bucket"] = rng.choice(labels, size=len(df), p=probs)


def _ensure_structural_dependency(
    df: pd.DataFrame, config: dict[str, Any], rng: np.random.Generator
) -> None:
    if "structural_dependency_proxy" not in df.columns:
        csd: dict[str, Any] = config.get("cleaner_synthetic_defaults") or {}
        sdp = float(csd.get("structural_dependency_true_rate", 0.25))
        df["structural_dependency_proxy"] = rng.random(len(df)) < sdp
    df["structural_dependency_proxy"] = df["structural_dependency_proxy"].astype(bool)


def _ensure_internet_flag(
    df: pd.DataFrame, config: dict[str, Any], rng: np.random.Generator
) -> None:
    if "internet_access_flag" not in df.columns:
        ict = config.get("media_penetration_defaults", {})
        rural_inet_p = float(ict.get("internet_access_rural_rate", 0.279))
        urban_inet_p = float(ict.get("internet_access_urban_rate", 0.734))
        df["internet_access_flag"] = np.where(
            df["rural_flag"],
            rng.random(len(df)) < rural_inet_p,
            rng.random(len(df)) < urban_inet_p,
        )
    df["internet_access_flag"] = df["internet_access_flag"].astype(bool)


def clean_population(
    raw_df: pd.DataFrame,
    config: dict[str, Any],  # generation.yaml nested knobs; single TypedDict deferred
    qa_report_dir: str | Path | None = None,
    seed: int | None = 42,
) -> pd.DataFrame:
    """Apply deterministic cleaning steps and emit an optional QA report.

    Args:
        raw_df: Raw or flawed population table (for example from
            :func:`population_segmentation.data.raw_injector.inject_flaws`).
        config: Generation configuration dict (controls synthetic internet flags,
            ``qa_report`` toggles, etc.).
        qa_report_dir: Directory to write QA sidecars; ``None`` skips report emission.
        seed: RNG seed forwarded to :func:`population_segmentation.utils.seeds.make_rng`
            for any stochastic repair paths. Same ``raw_df``, ``config``, and
            ``seed`` reproduce the clean frame exactly.

    Returns:
        Clean population dataset satisfying the Module A clean contract.

    Raises:
        KeyError: If required input columns are missing from ``raw_df``.

    Example:
        Typical export-stage call::

            clean_df = clean_population(raw_dirty, config, qa_report_dir=out_dir, seed=42)
    """
    rng = make_rng(seed)
    df = raw_df.copy()

    df = _apply_encoding_provenance(df)
    _standardize_cedula_and_gender(df)
    df = _normalize_departments_and_dedupe(df)
    _derive_age_from_dob(df)
    _impute_municipalities(df)
    _canonicalize_phone(df)
    _ensure_rural_flag(df, config, rng)
    _ensure_language_bucket(df, config, rng)
    _ensure_structural_dependency(df, config, rng)
    _ensure_internet_flag(df, config, rng)

    if qa_report_dir is not None:
        _write_qa_report(df, raw_df, Path(qa_report_dir))

    out = df.reset_index(drop=True)
    validate_clean_population(out)
    return out


def _normalize_dob(dob: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Normalize DOB strings to DD/MM/YYYY; return (dob, imputed-with-fallback mask)."""
    out: list[str] = []
    imputed: list[bool] = []
    for raw_item in dob:
        raw: str = str(raw_item)
        parts = raw.split("/")
        imputed.append(True)
        if len(parts) != 3:
            out.append(_DOB_FALLBACK)
            continue
        a, b, c = parts
        # detect likely MM/DD vs DD/MM
        try:
            ai = int(a)
            bi = int(b)
            ci = int(c)
        except ValueError:
            out.append(_DOB_FALLBACK)
            continue
        if ci < 1900 or ci > 2025:
            # malformed year; fallback
            out.append(_DOB_FALLBACK)
            continue
        imputed[-1] = False
        day, month = ai, bi
        if ai <= 12 and bi > 12:
            # likely MM/DD -> swap
            day, month = bi, ai
        day = min(max(day, 1), 28)
        month = min(max(month, 1), 12)
        out.append(f"{day:02d}/{month:02d}/{ci}")
    return pd.Series(out, index=dob.index), pd.Series(imputed, index=dob.index, dtype=bool)


def _write_qa_report(clean_df: pd.DataFrame, raw_df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    path = out_dir / f"qa_report_{ts}.md"

    lines = [
        "# QA Report",
        "",
        f"- Input rows: {len(raw_df)}",
        f"- Output rows: {len(clean_df)}",
        f"- Municipality null rate (post-clean): {clean_df['municipality'].isna().mean():.4f}",
        f"- Cedula invalid rate: {clean_df['cedula_invalid'].mean():.4f}",
        f"- Rural flag nulls: {clean_df['rural_flag'].isna().sum()}",
        *_imputation_lines(clean_df),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _imputation_lines(clean_df: pd.DataFrame) -> list[str]:
    """QA lines that make every imputation and clamp observable (F-087)."""
    imputed = clean_df["dob_imputed"].astype(bool)
    ages = pd.Series(clean_df["age_on_event_date"])
    mode_all = int(ages.mode().iat[0]) if len(ages) else 0
    kept = pd.Series(ages[~imputed])
    mode_kept = int(kept.mode().iat[0]) if len(kept) else 0
    lines = [
        f"- DOB imputed with {_DOB_FALLBACK} fallback: {int(imputed.sum())} "
        f"({imputed.mean():.4f}); age mode {mode_all} with imputed rows, {mode_kept} without",
        f"- Age outside [{AGE_MIN}, {AGE_MAX}] before clamping: "
        f"{int(clean_df['age_out_of_range'].sum())} ({clean_df['age_out_of_range'].mean():.4f})"
        " — the post-clean age bound is a schema-contract check, not a quality gate",
    ]
    if clean_df.attrs.get("rural_flag_imputed"):
        by_dept = clean_df.groupby("department")["rural_flag"].mean().sort_index()
        lines.append("- rural_flag imputed per department urban share; rural rate by department:")
        lines += [f"  - {dept}: {rate:.3f}" for dept, rate in by_dept.items()]
    else:
        lines.append("- rural_flag: present in raw input (not imputed)")
    return lines


def _parse_cli() -> argparse.Namespace:
    """Parse CLI for ``python -m population_segmentation.data.cleaner``."""
    p = argparse.ArgumentParser(
        description="Clean raw population parquet into population_master_clean schema."
    )
    p.add_argument("--input", type=Path, required=True, help="Input raw parquet path")
    p.add_argument("--output", type=Path, required=True, help="Output clean parquet path")
    p.add_argument("--config", type=Path, required=True, help="Path to generation.yaml")
    p.add_argument("--seed", type=int, default=None, help="RNG seed (default: RANDOM_SEED or 42)")
    p.add_argument(
        "--qa-report-dir",
        type=Path,
        default=None,
        help="If set, write qa_report_YYYYMMDD.md under this directory",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_cli()
    seed = args.seed
    if seed is None:
        seed = int(os.environ.get("RANDOM_SEED", "42"))
    with open(args.config, encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    raw_df = pd.read_parquet(args.input)
    out_df = clean_population(raw_df, cfg, qa_report_dir=args.qa_report_dir, seed=seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(args.output, index=False)
    print(f"Cleaned {len(raw_df):,} → {len(out_df):,} rows → {args.output}")
