# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Deterministic flaw injection layer.

Injects all 13 flaw types from scope §4.2 into a clean synthetic population
to simulate the original data collection environment (TSJE regional re-type,
DGEEC CSV exports, encoding errors, etc.).

All operations are seeded for reproducibility. Flaw rates are read from config.
"""

from __future__ import annotations

import re
from typing import Any, Final

import numpy as np
import pandas as pd

from population_segmentation.utils.schema import (
    AGE_ON_EVENT_DATE,
    CEDULA,
    DEPARTMENT,
    DOB,
    FIRST_NAME,
    GENDER,
    LAST_NAME,
    MUNICIPALITY,
    PHONE,
    QUALITATIVE_DISTRICT,
    QUALITATIVE_SENTIMENT,
    SCHEMA_DRIFT_FLAG,
)
from population_segmentation.utils.seeds import make_rng

# ─── Department typo variants (common transcription errors) ───────────────────
_DEPT_TYPOS: dict[str, list[str]] = {
    "Cordillera": ["Cordilera", "Cordillera ", "cordillera"],
    "Caaguazu": ["Caaguazú", "Caguazu", "Caaguaçu"],
    "Misiones": ["Misione", "Misiones ", "misions"],
    "Caazapa": ["Cazapa", "Caasapa", "Caazapá"],
    "Canindeyu": ["Canidenyu", "Canindeyu ", "Caindeyú"],
    "Concepcion": ["Concepción", "Consepcion", "concepcion"],
    "Paraguari": ["Paraguarí", "Paraguarry", "paraguari"],
    "Itapua": ["Itapúa", "Itapuá", "itapua"],
    "Neembucu": ["Ñeembucú", "Neembuku", "neembucu"],
    "Amambay": ["Amambai", "amambay", "Amambáy"],
}

# Replace only the first matching character per name string: realistic partial
# corruption (a field garbled once, not every accented character replaced).
GARBLE_FIRST_MATCH_ONLY: Final[bool] = True

# Windows-1252 bytes reinterpreted as Latin-1 → mojibake visible in UTF-8 output.
_ENCODING_GARBLES: dict[str, str] = {
    "á": "Ã¡",
    "é": "Ã©",
    "í": "Ã­",
    "ó": "Ã³",
    "ú": "Ãº",
    "ñ": "Ã±",
    "Á": "Ã\x81",
    "É": "Ã‰",
    "Ó": "Ã\u201c",
    "Ú": "Ãš",
    "Ü": "Ã\x9c",
    "ü": "Ã¼",
}

# Gender variants
_GENDER_VARIANTS: dict[str, list[str]] = {
    "M": ["M", "Masculino", "1", "m", "MASCULINO"],
    "F": ["F", "Femenino", "2", "f", "FEMENINO"],
}


def _inject_cedula_format_errors(
    df: pd.DataFrame, rate: float, n: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n) < rate
    df.loc[mask, CEDULA] = df.loc[mask, CEDULA].str.lstrip("0").str.slice(0, 7)


def _inject_duplicate_rows(
    df: pd.DataFrame, rate_dup: float, n: int, rng: np.random.Generator
) -> pd.DataFrame:
    n_dups = int(round(n * rate_dup))
    dup_idx = rng.choice(n, size=n_dups, replace=False)
    dup_rows = df.iloc[dup_idx].copy()
    dup_rows[CEDULA] = dup_rows[CEDULA].apply(
        lambda c: c[:-1] + str(rng.integers(0, 9)) if pd.notna(c) and len(str(c)) == 8 else c
    )
    return pd.concat([df, dup_rows], ignore_index=True)


def _inject_department_typos(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n_total) < rate
    for i in df.index[mask]:
        orig = df.at[i, DEPARTMENT]
        if orig in _DEPT_TYPOS:
            options = _DEPT_TYPOS[orig]
            df.at[i, DEPARTMENT] = options[int(rng.integers(0, len(options)))]
        else:
            df.at[i, DEPARTMENT] = str(orig).lower() if pd.notna(orig) else orig


def _inject_dob_swaps(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask_dob = rng.random(n_total) < rate
    dob_col = df[DOB]
    swapped_dob = dob_col.copy()
    for i in df.index[mask_dob]:
        raw = str(dob_col[i])
        parts = raw.split("/")
        if len(parts) == 3:
            swapped_dob[i] = f"{parts[1]}/{parts[0]}/{parts[2]}"
    df[DOB] = swapped_dob


def _inject_encoding_errors(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n_total) < rate
    df.loc[df.index[mask], FIRST_NAME] = df.loc[df.index[mask], FIRST_NAME].apply(_garble_encoding)
    df.loc[df.index[mask], LAST_NAME] = df.loc[df.index[mask], LAST_NAME].apply(_garble_encoding)


def _inject_gender_variants(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n_total) < rate
    for i in df.index[mask]:
        g = df.at[i, GENDER]
        if g in _GENDER_VARIANTS:
            opts = _GENDER_VARIANTS[g]
            df.at[i, GENDER] = opts[int(rng.integers(0, len(opts)))]


def _inject_age_range_errors(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n_total) < rate
    for i in df.index[mask]:
        raw_dob = df.at[i, DOB]
        parts = str(raw_dob).split("/")
        if len(parts) == 3:
            df.at[i, DOB] = f"{parts[2]}/{parts[1]}/{parts[0]}"


def _inject_sentiment_scale_inconsistency(
    df: pd.DataFrame, rate: float, n_total: int, rng: np.random.Generator
) -> None:
    mask = rng.random(n_total) < rate
    half = mask.sum() // 2
    mask_idx = np.where(mask)[0]
    df.loc[df.index[mask_idx[:half]], QUALITATIVE_SENTIMENT] = rng.integers(1, 6, size=half).astype(
        float
    )
    if len(mask_idx) > half:
        remaining = len(mask_idx) - half
        df.loc[df.index[mask_idx[half:]], QUALITATIVE_SENTIMENT] = rng.integers(
            0, 101, size=remaining
        ).astype(float)


def inject_flaws(
    df: pd.DataFrame,
    config: dict[str, Any],
    seed: int | None = None,
) -> pd.DataFrame:
    """Inject all 13 flaw types into a clean population DataFrame.

    Args:
        df:     Clean population DataFrame from generator.py.
        config: Generation config dict (flaw_injection section used).
        seed: Explicit RNG seed forwarded to :func:`population_segmentation.utils.seeds.make_rng`.
            Same ``df``, ``config``, and integer ``seed`` reproduce the flawed output
            exactly (including duplicate rows and attrs).

    Returns:
        Modified DataFrame with injected flaws. May be longer than input (DUP rows).
        Stores flaw types injected in df.attrs["flaw_types_injected"].

    Raises:
        KeyError: If ``config`` lacks ``flaw_injection`` or expected rate keys.

    Example:
        After generating a clean frame::

            dirty = inject_flaws(clean_df, config, seed=7)
    """
    rng = make_rng(seed)
    rates: dict[str, float] = config["flaw_injection"]
    df = df.copy()
    n = len(df)

    # ── 1. Add synthetic fields needed for raw layer ───────────────────────────
    df = _add_raw_fields(df, n, rng)

    _inject_cedula_format_errors(df, rates["cedula_format_error_rate"], n, rng)
    df = _inject_duplicate_rows(df, rates["duplicate_rate"], n, rng)
    n_total = len(df)

    _inject_department_typos(df, rates["department_typo_rate"], n_total, rng)

    mask = rng.random(n_total) < rates["municipality_null_rate"]
    df.loc[df.index[mask], MUNICIPALITY] = None

    _inject_dob_swaps(df, rates["date_format_swap_rate"], n_total, rng)
    _inject_encoding_errors(df, rates["encoding_error_rate"], n_total, rng)

    mask = rng.random(n_total) < rates["phone_format_variant_rate"]
    df.loc[df.index[mask], PHONE] = df.loc[df.index[mask], PHONE].apply(
        lambda p: _randomize_phone_format(p, rng)
    )

    _inject_gender_variants(df, rates["gender_variant_rate"], n_total, rng)
    _inject_age_range_errors(df, rates["age_range_error_rate"], n_total, rng)

    mask = rng.random(n_total) < rates["schema_drift_rate"]
    df[SCHEMA_DRIFT_FLAG] = False
    df.loc[df.index[mask], SCHEMA_DRIFT_FLAG] = True

    _inject_sentiment_scale_inconsistency(df, rates["sentiment_scale_inconsistency"], n_total, rng)

    mask = rng.random(n_total) < rates["qualitative_district_null_rate"]
    df.loc[df.index[mask], QUALITATIVE_DISTRICT] = None

    df.attrs["flaw_types_injected"] = [
        "FMT_cedula",
        "DUP",
        "TYP_department",
        "NUL_municipality",
        "FMT_dob",
        "ENC",
        "FMT_phone",
        "TYP_gender",
        "RNG_age",
        "SCH",
        "TYP_sentiment",
        "NUL_qualitative_district",
        "NUL_rural_flag",  # always derived — counts as flaw type 13
    ]

    return df


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _add_raw_fields(
    df: pd.DataFrame,
    n: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Add fields that exist in the raw layer but not the clean generator output."""
    # cédula: generate 8-digit string
    if CEDULA not in df.columns:
        cedulas = (rng.integers(10_000_000, 99_999_999, size=n)).astype(str)
        df[CEDULA] = cedulas

    # DOB: derive from age_on_event_date (April 22, 2018 reference)
    if DOB not in df.columns:
        birth_years = 2018 - df[AGE_ON_EVENT_DATE].astype(int).to_numpy()
        birth_months = rng.integers(1, 13, size=n)
        birth_days = rng.integers(1, 29, size=n)
        df[DOB] = [
            f"{d:02d}/{m:02d}/{y}"
            for d, m, y in zip(birth_days, birth_months, birth_years, strict=False)
        ]

    # Names: synthetic Spanish/Guaraní names
    if FIRST_NAME not in df.columns:
        df[FIRST_NAME] = _generate_names(n, rng, name_type="first")
    if LAST_NAME not in df.columns:
        df[LAST_NAME] = _generate_names(n, rng, name_type="last")

    # Phone: E.164 Paraguay format
    if PHONE not in df.columns:
        numbers = rng.integers(970_000_000, 999_999_999, size=n)
        df[PHONE] = [f"+595{num}" for num in numbers]

    # Qualitative fields
    if QUALITATIVE_SENTIMENT not in df.columns:
        df[QUALITATIVE_SENTIMENT] = rng.integers(1, 6, size=n).astype(float)
    if QUALITATIVE_DISTRICT not in df.columns:
        df[QUALITATIVE_DISTRICT] = df[DEPARTMENT].copy()

    return df


_FIRST_NAMES = [
    "Carlos",
    "María",
    "José",
    "Ana",
    "Luis",
    "Rosa",
    "Pedro",
    "Laura",
    "Miguel",
    "Patricia",
    "Jorge",
    "Claudia",
    "Ramón",
    "Sandra",
    "Fernando",
    "Elena",
    "Héctor",
    "Sofía",
    "Ricardo",
    "Verónica",
]
_LAST_NAMES = [
    "García",
    "Martínez",
    "López",
    "González",
    "Rodríguez",
    "Pérez",
    "Sánchez",
    "Ramírez",
    "Torres",
    "Flores",
    "Díaz",
    "Morales",
    "Jiménez",
    "Gutiérrez",
    "Ortiz",
    "Chávez",
    "Reyes",
    "Mendoza",
    "Cabrera",
    "Riveros",
]


def _generate_names(
    n: int,
    rng: np.random.Generator,
    name_type: str = "first",
) -> list[str]:
    pool = _FIRST_NAMES if name_type == "first" else _LAST_NAMES
    idx = rng.integers(0, len(pool), size=n)
    return [pool[i] for i in idx]


def _garble_encoding(name: object) -> object:
    """Replace first matching accented char with mojibake; for-else appends '?' if needed."""
    if not isinstance(name, str):
        return name
    for char, garbled in _ENCODING_GARBLES.items():
        if char in name:
            return name.replace(char, garbled, 1)
    else:
        if any(ord(c) > 127 for c in name):
            return name + "?"
    return name


def _randomize_phone_format(phone: str, rng: np.random.Generator) -> str:
    """Convert a +595XXXXXXXXX number to one of 3 observed formats."""
    # Strip to 9 digits
    digits = re.sub(r"\D", "", phone)[-9:]
    fmt_choice = int(rng.integers(0, 3))
    if fmt_choice == 0:
        return f"0{digits}"
    elif fmt_choice == 1:
        return f"+595{digits}"
    else:
        return digits


if __name__ == "__main__":
    import argparse
    import os
    from pathlib import Path

    import yaml

    p = argparse.ArgumentParser(description="Inject raw-layer flaws; read/write parquet.")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()
    seed = args.seed if args.seed is not None else int(os.environ.get("RANDOM_SEED", "42"))
    with open(args.config, encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    df = pd.read_parquet(args.input)
    n_in = len(df)
    out = inject_flaws(df, cfg, seed=seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)
    flaw_types = out.attrs.get("flaw_types_injected", [])
    print(f"inject_flaws: {n_in:,} → {len(out):,} rows; flaw_types={flaw_types}")
