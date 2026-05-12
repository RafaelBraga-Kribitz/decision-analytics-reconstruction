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


def clean_population(
    raw_df: pd.DataFrame,
    config: dict[str, Any],
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

    # Step 1: encoding provenance — raw contract uses `enc_source_raw`; clean contract
    # uses `enc_source` (see schema_contracts/population_master_{raw,clean}.yaml).
    if ENC_SOURCE_RAW in df.columns:
        raw_tags = df[ENC_SOURCE_RAW].fillna("unknown").astype(str).str.strip().str.lower()
        df[ENC_SOURCE] = raw_tags.where(raw_tags.isin(CANONICAL_ENC_SOURCE), "unknown")
        df = df.drop(columns=[ENC_SOURCE_RAW])
    elif ENC_SOURCE not in df.columns:
        df[ENC_SOURCE] = "utf8"

    # Step 2: cedula standardization to 8 digits
    df["cedula"] = df["cedula"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(8).str[-8:]
    df["cedula_invalid"] = ~df["cedula"].str.match(r"^\d{8}$")

    # Step 3: gender normalization
    df["gender"] = df["gender"].replace(_GENDER_MAP).fillna("unknown")

    # Step 4: department normalization
    dept = df["department"].astype(str).str.strip()
    df["department"] = dept.replace(_DEPT_NORMALIZE)
    df.loc[~df["department"].isin(list(CANONICAL_DEPARTMENTS)), "department"] = "Central"

    # Step 5: deduplication — two passes to enforce entity_id uniqueness.
    # Pass 5a: drop rows with identical (entity_id, cedula) — handles clean re-registrations.
    # Pass 5b: drop remaining duplicate entity_ids (different cedula means one row is a flaw
    # injected by raw_injector; keep the first occurrence, which is the original record).
    # This guarantees the schema contract entity_id: unique: true.
    df = df.sort_values("entity_id").drop_duplicates(subset=["entity_id", "cedula"], keep="first")
    df = df.drop_duplicates(subset=["entity_id"], keep="first")

    # Step 6: date parsing and age derivation
    dob_series = _normalize_dob(pd.Series(df["dob"].astype(str)))
    df["dob"] = dob_series
    event_date = pd.Timestamp("2018-04-22")
    dob_parsed = pd.to_datetime(df["dob"], format="%d/%m/%Y", errors="coerce")
    age = ((event_date - dob_parsed).dt.days / 365.25).fillna(0).astype(int)
    df["age_on_event_date"] = age
    df["dob_ambiguous"] = dob_parsed.isna()

    # Step 7: age range enforcement
    df["age_out_of_range"] = ~df["age_on_event_date"].between(18, 115)
    df.loc[df["age_on_event_date"] < 18, "age_on_event_date"] = 18
    df.loc[df["age_on_event_date"] > 115, "age_on_event_date"] = 115

    # Step 8: municipality imputation
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

    # Step 9: phone canonicalization to +595XXXXXXXXX
    df["phone"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True)
    df["phone"] = df["phone"].str[-9:]
    df["phone"] = "+595" + df["phone"]
    df["phone_invalid"] = ~df["phone"].str.match(r"^\+595\d{9}$")

    # Step 10: ensure rural flag exists and complete
    if "rural_flag" not in df.columns:
        df["rural_flag"] = rng.random(len(df)) < 0.383
    df["rural_flag"] = df["rural_flag"].fillna(False).astype(bool)
    df["rural_flag_derived"] = True

    # Step 11: language raking rough pass
    if "language_census_bucket" not in df.columns:
        df["language_census_bucket"] = rng.choice(
            ["jopara_bilingual", "guarani_only", "spanish_only", "other"],
            size=len(df),
            p=[0.46, 0.34, 0.15, 0.05],
        )

    # Step 12: structural dependency proxy ensure bool
    if "structural_dependency_proxy" not in df.columns:
        df["structural_dependency_proxy"] = rng.random(len(df)) < 0.25
    df["structural_dependency_proxy"] = df["structural_dependency_proxy"].astype(bool)

    # Step 13: internet flag ensure bool
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

    # Step 14: QA report generation
    if qa_report_dir is not None:
        _write_qa_report(df, raw_df, Path(qa_report_dir))

    out = df.reset_index(drop=True)
    validate_clean_population(out)
    return out


def _normalize_dob(dob: pd.Series) -> pd.Series:
    out: list[str] = []
    for raw in dob:
        parts = str(raw).split("/")
        if len(parts) != 3:
            out.append("01/01/1980")
            continue
        a, b, c = parts
        # detect likely MM/DD vs DD/MM
        try:
            ai = int(a)
            bi = int(b)
            ci = int(c)
        except ValueError:
            out.append("01/01/1980")
            continue
        if ci < 1900 or ci > 2025:
            # malformed year; fallback
            out.append("01/01/1980")
            continue
        day, month = ai, bi
        if ai <= 12 and bi > 12:
            # likely MM/DD -> swap
            day, month = bi, ai
        day = min(max(day, 1), 28)
        month = min(max(month, 1), 12)
        out.append(f"{day:02d}/{month:02d}/{ci}")
    return pd.Series(out, index=dob.index)


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
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


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
