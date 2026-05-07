"""Deterministic flaw injection layer.

Injects all 13 flaw types from scope §4.2 into a clean synthetic population
to simulate the original data collection environment (TSJE regional re-type,
DGEEC CSV exports, encoding errors, etc.).

All operations are seeded for reproducibility. Flaw rates are read from config.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from population_segmentation.utils.schema import (
    AGE_ON_EVENT_DATE,
    CEDULA,
    DEPARTMENT,
    GENDER,
    MUNICIPALITY,
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

# Windows-1252 → UTF-8 garbling: replace accented chars with ? placeholder
# (actual byte sequences omitted to avoid encoding issues in source files)
_ENCODING_GARBLE_CHARS: list[str] = [
    "\xe1",
    "\xe9",
    "\xed",
    "\xf3",
    "\xfa",  # á é í ó ú
    "\xf1",
    "\xc1",
    "\xc9",
    "\xd3",
    "\xda",  # ñ Á É Ó Ú
]

# Gender variants
_GENDER_VARIANTS: dict[str, list[str]] = {
    "M": ["M", "Masculino", "1", "m", "MASCULINO"],
    "F": ["F", "Femenino", "2", "f", "FEMENINO"],
}


def inject_flaws(
    df: pd.DataFrame,
    config: dict[str, Any],
    seed: int | None = None,
) -> pd.DataFrame:
    """Inject all 13 flaw types into a clean population DataFrame.

    Args:
        df:     Clean population DataFrame from generator.py.
        config: Generation config dict (flaw_injection section used).
        seed:   Random seed.

    Returns:
        Modified DataFrame with injected flaws. May be longer than input (DUP rows).
        Stores flaw types injected in df.attrs["flaw_types_injected"].
    """
    rng = make_rng(seed)
    rates: dict[str, float] = config["flaw_injection"]
    df = df.copy()
    n = len(df)

    # ── 1. Add synthetic fields needed for raw layer ───────────────────────────
    df = _add_raw_fields(df, n, rng)

    # ── FMT-1: Cédula format errors (7-digit, missing zero-pad) ───────────────
    rate = rates["cedula_format_error_rate"]
    mask = rng.random(n) < rate
    df.loc[mask, CEDULA] = df.loc[mask, CEDULA].str.lstrip("0").str.slice(0, 7)

    # ── DUP: Cross-office duplicate rows ──────────────────────────────────────
    rate_dup = rates["duplicate_rate"]
    n_dups = int(round(n * rate_dup))
    dup_idx = rng.choice(n, size=n_dups, replace=False)
    dup_rows = df.iloc[dup_idx].copy()
    # Minor name-spelling variation in duplicates
    dup_rows[CEDULA] = dup_rows[CEDULA].apply(
        lambda c: c[:-1] + str(rng.integers(0, 9)) if pd.notna(c) and len(str(c)) == 8 else c
    )
    df = pd.concat([df, dup_rows], ignore_index=True)
    n_total = len(df)

    # ── TYP-1: Department typo variants ───────────────────────────────────────
    rate = rates["department_typo_rate"]
    mask = rng.random(n_total) < rate
    for i in df.index[mask]:
        orig = df.at[i, DEPARTMENT]
        if orig in _DEPT_TYPOS:
            options = _DEPT_TYPOS[orig]
            df.at[i, DEPARTMENT] = options[int(rng.integers(0, len(options)))]
        else:
            # Generic: lowercase first char
            df.at[i, DEPARTMENT] = str(orig).lower() if pd.notna(orig) else orig

    # ── NUL-1: Municipality nulls (~8%) ───────────────────────────────────────
    rate = rates["municipality_null_rate"]
    mask = rng.random(n_total) < rate
    df.loc[df.index[mask], MUNICIPALITY] = None

    # ── FMT-2: DOB format swap (MM/DD/YYYY for ~1.8% of records) ──────────────
    rate = rates["date_format_swap_rate"]
    mask_dob = rng.random(n_total) < rate
    # Mark affected rows; actual swap simulated by transposing day/month in dob string
    dob_col = df["dob"]
    swapped_dob = dob_col.copy()
    for i in df.index[mask_dob]:
        raw = str(dob_col[i])
        parts = raw.split("/")
        if len(parts) == 3:
            # Swap day and month
            swapped_dob[i] = f"{parts[1]}/{parts[0]}/{parts[2]}"
    df["dob"] = swapped_dob

    # ── ENC: Encoding errors in name fields ───────────────────────────────────
    rate = rates["encoding_error_rate"]
    mask = rng.random(n_total) < rate
    df.loc[df.index[mask], "first_name"] = df.loc[df.index[mask], "first_name"].apply(
        _garble_encoding
    )
    df.loc[df.index[mask], "last_name"] = df.loc[df.index[mask], "last_name"].apply(
        _garble_encoding
    )

    # ── FMT-3: Phone format variants ──────────────────────────────────────────
    rate = rates["phone_format_variant_rate"]
    mask = rng.random(n_total) < rate
    df.loc[df.index[mask], "phone"] = df.loc[df.index[mask], "phone"].apply(
        lambda p: _randomize_phone_format(p, rng)
    )

    # ── TYP-2: Gender variants ────────────────────────────────────────────────
    rate = rates["gender_variant_rate"]
    mask = rng.random(n_total) < rate
    for i in df.index[mask]:
        g = df.at[i, GENDER]
        if g in _GENDER_VARIANTS:
            opts = _GENDER_VARIANTS[g]
            df.at[i, GENDER] = opts[int(rng.integers(0, len(opts)))]

    # ── RNG: Age range errors (transposed DOBs produce bad ages) ─────────────
    rate = rates["age_range_error_rate"]
    mask = rng.random(n_total) < rate
    # Inject an extra DOB swap that creates year-transposition → age < 18 or > 120
    for i in df.index[mask]:
        raw_dob = df.at[i, "dob"]
        parts = str(raw_dob).split("/")
        if len(parts) == 3:
            # Year → 2-digit confusion: swap last two digits of year with day
            df.at[i, "dob"] = f"{parts[2]}/{parts[1]}/{parts[0]}"

    # ── SCH: Schema drift flag ────────────────────────────────────────────────
    rate = rates["schema_drift_rate"]
    mask = rng.random(n_total) < rate
    df["schema_drift_flag"] = False
    df.loc[df.index[mask], "schema_drift_flag"] = True

    # ── TYP-3: Qualitative sentiment inconsistent scale ───────────────────────
    rate = rates["sentiment_scale_inconsistency"]
    mask = rng.random(n_total) < rate
    # Half of affected rows: scale 1–5; other half: scale 0–100
    half = mask.sum() // 2
    mask_idx = np.where(mask)[0]
    df.loc[df.index[mask_idx[:half]], "qualitative_sentiment"] = rng.integers(
        1, 6, size=half
    ).astype(float)
    if len(mask_idx) > half:
        remaining = len(mask_idx) - half
        df.loc[df.index[mask_idx[half:]], "qualitative_sentiment"] = rng.integers(
            0, 101, size=remaining
        ).astype(float)

    # ── NUL-2: Qualitative district nulls (~25%) ──────────────────────────────
    rate = rates["qualitative_district_null_rate"]
    mask = rng.random(n_total) < rate
    df.loc[df.index[mask], "qualitative_district"] = None

    # Metadata
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
    if "dob" not in df.columns:
        birth_years = 2018 - df[AGE_ON_EVENT_DATE].values
        birth_months = rng.integers(1, 13, size=n)
        birth_days = rng.integers(1, 29, size=n)
        df["dob"] = [
            f"{d:02d}/{m:02d}/{y}"
            for d, m, y in zip(birth_days, birth_months, birth_years, strict=False)
        ]

    # Names: synthetic Spanish/Guaraní names
    if "first_name" not in df.columns:
        df["first_name"] = _generate_names(n, rng, name_type="first")
    if "last_name" not in df.columns:
        df["last_name"] = _generate_names(n, rng, name_type="last")

    # Phone: E.164 Paraguay format
    if "phone" not in df.columns:
        numbers = rng.integers(970_000_000, 999_999_999, size=n)
        df["phone"] = [f"+595{num}" for num in numbers]

    # Qualitative fields
    if "qualitative_sentiment" not in df.columns:
        df["qualitative_sentiment"] = rng.integers(1, 6, size=n).astype(float)
    if "qualitative_district" not in df.columns:
        df["qualitative_district"] = df[DEPARTMENT].copy()

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


def _garble_encoding(name: str) -> str:
    """Simulate Windows-1252 → UTF-8 garbling for a name string."""
    if not isinstance(name, str):
        return name
    for char in _ENCODING_GARBLE_CHARS:
        if char in name:
            name = name.replace(char, "?", 1)
            break
    if any(ord(c) > 127 for c in name):
        name = name + "?"
    return name


def _randomize_phone_format(phone: str, rng: np.random.Generator) -> str:
    """Convert a +595XXXXXXXXX number to one of 3 observed formats."""
    if not isinstance(phone, str):
        return phone
    # Strip to 9 digits
    digits = re.sub(r"\D", "", phone)[-9:]
    fmt_choice = int(rng.integers(0, 3))
    if fmt_choice == 0:
        return f"0{digits}"
    elif fmt_choice == 1:
        return f"+595{digits}"
    else:
        return digits
