# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Synthetic population generator.

Produces a DataFrame of N synthetic entities calibrated to TSJE/DGEEC
verified demographic anchors. Uses IPF/raking logic to enforce marginals.
All random operations use an explicitly seeded numpy Generator.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from population_segmentation.utils.schema import (
    AGE_ON_EVENT_DATE,
    BALLOT_BLANK_PARLASUR,
    BALLOT_BLANK_PRESIDENT,
    DEPARTMENT,
    ENC_SOURCE_RAW,
    ENTITY_ID,
    GENDER,
    INTERNET_ACCESS_FLAG,
    JOPARA_FLAG,
    LANGUAGE_CENSUS_BUCKET,
    MEDIA_PENETRATION_RADIO,
    MEDIA_PENETRATION_TV,
    MEDIA_PENETRATION_WHATSAPP,
    MUNICIPALITY,
    NBI_STRESS_PRIOR,
    PREFERENCE_PROXY,
    PREFERENCE_PROXY_STRENGTH,
    RURAL_FLAG,
    RURAL_FLAG_DERIVED,
    STRUCTURAL_DEPENDENCY_PROXY,
)
from population_segmentation.utils.seeds import make_rng

# Single default when ``cleaner_synthetic_defaults.rural_flag_true_rate`` is absent from config.
_DEFAULT_NATIONAL_RURAL_ANCHOR: float = 0.383

# Defaults when ``generator_*`` YAML blocks are absent (matches historical generator behaviour).
_DEFAULT_STRUCT_RURAL_BASE: float = 0.35
_DEFAULT_STRUCT_URBAN_BASE: float = 0.12
_DEFAULT_STRUCT_ELEVATED_RURAL: float = 0.60
_DEFAULT_STRUCT_ELEVATED_DEPTS: frozenset[str] = frozenset(
    ("San Pedro", "Caazapa", "Canindeyu", "Concepcion", "Paraguari")
)
_DEFAULT_BALLOT_PRES: float = 0.0241
_DEFAULT_BALLOT_PARL: float = 0.0848
_ENC_SOURCE_LABELS: tuple[str, ...] = ("windows1252", "utf8", "unknown")
_DEFAULT_ENC_SOURCE_PROBS: tuple[float, float, float] = (0.45, 0.50, 0.05)


def _nbi_urban_stress_from_rural(
    nbi_rural: dict[str, float], floor: float, scale: float
) -> dict[str, float]:
    return {d: max(floor, float(v) * scale) for d, v in nbi_rural.items()}


def _generator_dept_media_nbi_tables(
    config: dict[str, Any],
) -> tuple[
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    float,
    float,
    float,
]:
    """Load department TV/radio/NBI tables from ``generator_dept_media_nbi``."""
    gdm = config.get("generator_dept_media_nbi")
    if not isinstance(gdm, dict):
        raise KeyError(
            "generation config must include 'generator_dept_media_nbi' "
            "(department TV/radio/NBI tables; see generation.yaml)"
        )
    for key in ("tv_by_department", "radio_by_department", "nbi_rural_stress_by_department"):
        sub: Any = gdm.get(key)
        if not isinstance(sub, dict) or not sub:
            raise KeyError(f"generator_dept_media_nbi.{key} must be a non-empty mapping")
    tv_by = {str(k): float(v) for k, v in cast(dict[str, Any], gdm["tv_by_department"]).items()}
    radio_by = {
        str(k): float(v) for k, v in cast(dict[str, Any], gdm["radio_by_department"]).items()
    }
    nbi_rural = {
        str(k): float(v)
        for k, v in cast(dict[str, Any], gdm["nbi_rural_stress_by_department"]).items()
    }
    urb_raw: dict[str, Any] = gdm.get("nbi_urban_from_rural") or {}
    nbi_floor = float(urb_raw.get("floor", 0.10))
    nbi_scale = float(urb_raw.get("scale", 0.35))
    nbi_urban = _nbi_urban_stress_from_rural(nbi_rural, nbi_floor, nbi_scale)
    nbi_noise_std = float(cast(Any, gdm.get("nbi_noise_std", 0.03)))
    nbi_rural_fb = float(cast(Any, gdm.get("nbi_rural_unknown_department", 0.659)))
    nbi_urban_fb = float(cast(Any, gdm.get("nbi_urban_unknown_department", 0.252)))
    return tv_by, radio_by, nbi_rural, nbi_urban, nbi_noise_std, nbi_rural_fb, nbi_urban_fb


def _elevated_departments_frozenset(gsd: dict[str, Any]) -> frozenset[str]:
    raw: Any = gsd.get("elevated_departments")
    if isinstance(raw, list) and len(raw) > 0:
        return frozenset(str(x) for x in cast(list[object], raw))
    return _DEFAULT_STRUCT_ELEVATED_DEPTS


def _enc_source_labels_and_probs(config: dict[str, Any]) -> tuple[list[str], np.ndarray]:
    dist: dict[str, Any] = config.get("generator_enc_source_raw_distribution") or {}
    labels = list(_ENC_SOURCE_LABELS)
    probs = np.array([float(dist.get(k, 0.0)) for k in labels], dtype=np.float64)
    if float(probs.sum()) <= 0.0:
        probs = np.asarray(_DEFAULT_ENC_SOURCE_PROBS, dtype=np.float64)
    probs = probs / probs.sum()
    return labels, probs


def _load_config(config_path: str | Path) -> dict[str, Any]:
    with open(config_path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def _validated_department_sampling_probs(
    dept_weights_raw: dict[str, float],
) -> tuple[list[str], np.ndarray]:
    """Validate nominal weights and return a probability vector summing *exactly* to 1.0.

    ``generation.yaml`` stores human-facing shares at four decimal places; their
    :class:`decimal.Decimal` sum must be exactly ``1.0000``. Binary ``float`` loads
    can drift (e.g. ``1.0000000000000002``); we normalize then assign the residual
    to the largest-weight department so :meth:`numpy.random.Generator.choice`
    receives a mathematically valid ``p``.

    Args:
        dept_weights_raw: Mapping of department name to positive nominal weight.

    Returns:
        Department names in dict iteration order and a ``float64`` probability array.

    Raises:
        AssertionError: If Decimal(4dp) sum is not ``1.0000`` or float sum is far from 1.0.
        ValueError: If weights are non-finite or non-positive.
    """
    quant = Decimal("0.0001")
    decimal_sum = sum(
        Decimal(str(float(v))).quantize(quant, rounding=ROUND_HALF_EVEN)
        for v in dept_weights_raw.values()
    )
    assert decimal_sum == Decimal("1.0000"), (
        "department_weights must sum to 1.0000 at 4 decimal places "
        f"(Decimal check reflects YAML rounding intent), got {decimal_sum}"
    )

    dept_names = list(dept_weights_raw.keys())
    probs = np.asarray([float(dept_weights_raw[d]) for d in dept_names], dtype=np.float64)
    raw_sum = float(probs.sum())
    if not np.isfinite(raw_sum) or raw_sum <= 0:
        raise ValueError("department_weights must be finite and strictly positive")
    assert abs(raw_sum - 1.0) < 0.001, (
        "department_weights float sum must be within 0.001 of 1.0 before normalization, "
        f"got {raw_sum:.12f}"
    )

    probs /= probs.sum()
    imax = int(np.argmax(probs))
    probs[imax] = 1.0 - float(np.sum(np.delete(probs, imax)))

    assert np.all(probs >= 0.0), probs
    assert probs.sum() == 1.0, float(probs.sum())

    return dept_names, probs


def generate_population(
    config: dict[str, Any],
    seed: int | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Generate a synthetic population DataFrame.

    Args:
        config: Generation configuration dict (from generation.yaml).
        seed: Explicit RNG seed forwarded to :func:`population_segmentation.utils.seeds.make_rng`.
            Same ``config`` and the same integer ``seed`` (or both using the same
            ``RANDOM_SEED`` environment when ``seed`` is ``None``) return an identical
            population dataset across runs.
        output_path: Optional parquet path to write output.

    Returns:
        DataFrame with one row per entity; columns match
        schema_contracts/population_master_raw.yaml.

    Raises:
        KeyError: If ``config`` is missing required keys such as ``sample_size`` or
            ``department_weights``.
        ValueError: If department weights cannot be normalized to a valid distribution.

    Example:
        From a loaded ``generation.yaml`` dict::

            df = generate_population(config, seed=42, output_path="data/interim/raw.parquet")
    """
    rng = make_rng(seed)
    n = int(config["sample_size"])

    dept_weights_raw: dict[str, float] = config["department_weights"]
    dept_names, dept_probs = _validated_department_sampling_probs(dept_weights_raw)

    dept_urban_share: dict[str, float] = config["department_urban_share"]

    csd = config.get("cleaner_synthetic_defaults") or {}
    national_rural_anchor = float(csd.get("rural_flag_true_rate", _DEFAULT_NATIONAL_RURAL_ANCHOR))
    national_urban_fallback = 1.0 - national_rural_anchor

    gsd = config.get("generator_structural_dependency") or {}
    struct_rural_base = float(gsd.get("rural_base_rate", _DEFAULT_STRUCT_RURAL_BASE))
    struct_urban_base = float(gsd.get("urban_base_rate", _DEFAULT_STRUCT_URBAN_BASE))
    struct_elevated_rural = float(gsd.get("elevated_rural_rate", _DEFAULT_STRUCT_ELEVATED_RURAL))
    elevated_departments = _elevated_departments_frozenset(gsd)

    bbr = config.get("generator_ballot_blank_rates") or {}
    p_ballot_pres = float(bbr.get("president", _DEFAULT_BALLOT_PRES))
    p_ballot_parl = float(bbr.get("parlasur", _DEFAULT_BALLOT_PARL))

    ict = config.get("media_penetration_defaults", {})
    tv_nat = float(ict.get("tv_national", 0.89))
    radio_nat = float(ict.get("radio_national", 0.82))
    tv_by, radio_by, nbi_rural, nbi_urban, nbi_noise_std, nbi_rural_fb, nbi_urban_fb = (
        _generator_dept_media_nbi_tables(config)
    )

    # ── entity_id ──────────────────────────────────────────────────────────────
    entity_ids = np.arange(1, n + 1, dtype=np.int64)

    # ── department ─────────────────────────────────────────────────────────────
    dept_indices = rng.choice(len(dept_names), size=n, p=dept_probs)
    departments = np.array(dept_names, dtype=object)[dept_indices]

    # ── rural_flag (preliminary — derived from department urban share) ─────────
    rural_flags = np.zeros(n, dtype=bool)
    for i, dept in enumerate(dept_names):
        mask = dept_indices == i
        urban_p = dept_urban_share.get(dept, national_urban_fallback)
        rural_flags[mask] = rng.random(mask.sum()) > urban_p
    rural_flag_derived = np.ones(n, dtype=bool)

    # ── gender ─────────────────────────────────────────────────────────────────
    gender_split: dict[str, float] = config["gender_split"]
    genders = rng.choice(["M", "F"], size=n, p=[gender_split["M"], gender_split["F"]])

    # ── age_on_event_date ──────────────────────────────────────────────────────
    age_dist = config["age_distribution"]
    bins: list[int] = age_dist["bins"]
    bin_weights: list[float] = age_dist["bin_weights"]
    bin_probs = np.array(bin_weights, dtype=float)
    bin_probs /= bin_probs.sum()
    bin_indices = rng.choice(len(bin_probs), size=n, p=bin_probs)
    ages = np.zeros(n, dtype=np.int16)
    for bi in range(len(bin_probs)):
        mask = bin_indices == bi
        lo, hi = bins[bi], bins[bi + 1]
        ages[mask] = rng.integers(lo, hi, size=int(mask.sum()))

    # ── Rake rural_flag to national anchor (see cleaner_synthetic_defaults.rural_flag_true_rate) ──
    rural_flags = _rake_binary(rural_flags, target=national_rural_anchor, rng=rng)

    # ── municipality (placeholder — filled deterministically from dept) ────────
    # Full municipality lookup is applied in cleaner step 4; here we assign
    # a synthetic placeholder based on department to keep the raw layer simple.
    municipalities = _assign_municipalities(departments, rng)

    # ── language_census_bucket ─────────────────────────────────────────────────
    lang_priors: dict[str, float] = config["language_priors"]
    language_buckets = _assign_language(departments, rural_flags, lang_priors, rng)

    # ── Rake language to national marginals ───────────────────────────────────
    language_buckets = _rake_categorical(
        language_buckets,
        targets=lang_priors,
        rng=rng,
    )

    # ── preference_proxy ───────────────────────────────────────────────────────
    pref_priors: dict[str, float] = config["preference_proxy_priors"]
    pref_labels = list(pref_priors.keys())
    pref_probs = np.array([pref_priors[k] for k in pref_labels], dtype=float)
    pref_probs /= pref_probs.sum()
    preference_proxies = np.array(pref_labels)[rng.choice(len(pref_labels), size=n, p=pref_probs)]
    preference_proxy_strengths = rng.beta(2.0, 2.0, size=n).astype(np.float32)

    # ── internet_access_flag ───────────────────────────────────────────────────
    urban_inet = float(ict.get("whatsapp_urban", 0.74))
    rural_whatsapp = float(ict.get("whatsapp_rural", 0.31))
    inet_rural = float(ict.get("internet_access_rural_rate", 0.279))
    inet_urban = float(ict.get("internet_access_urban_rate", 0.734))
    inet_prob = np.where(rural_flags, inet_rural, inet_urban)
    internet_access_flags = rng.random(n) < inet_prob

    # ── media penetration ──────────────────────────────────────────────────────
    tv_pen = np.array([tv_by.get(str(d), tv_nat) for d in departments], dtype=np.float32)
    radio_pen = np.array([radio_by.get(str(d), radio_nat) for d in departments], dtype=np.float32)
    whatsapp_pen = np.where(rural_flags, rural_whatsapp, urban_inet).astype(np.float32)

    # ── nbi_stress_prior ───────────────────────────────────────────────────────
    nbi_vals = np.where(
        rural_flags,
        np.array([nbi_rural.get(str(d), nbi_rural_fb) for d in departments]),
        np.array([nbi_urban.get(str(d), nbi_urban_fb) for d in departments]),
    ).astype(np.float32)
    nbi_noise = rng.normal(0, nbi_noise_std, size=n).astype(np.float32)
    nbi_vals = np.clip(nbi_vals + nbi_noise, 0.0, 1.0).astype(np.float32)

    # ── structural_dependency_proxy ────────────────────────────────────────────
    base_dep_prob = np.where(rural_flags, struct_rural_base, struct_urban_base)
    elevated_mask = np.array([d in elevated_departments for d in departments])
    dep_prob = np.where(elevated_mask & rural_flags, struct_elevated_rural, base_dep_prob)
    structural_dependency = rng.random(n) < dep_prob

    # ── ballot blanks ──────────────────────────────────────────────────────────
    ballot_blank_pres = rng.random(n) < p_ballot_pres
    ballot_blank_parl = rng.random(n) < p_ballot_parl

    # ── enc_source_raw (raw contract) ───────────────────────────────────────
    # Cleaner step 1 promotes this column to ENC_SOURCE and drops ENC_SOURCE_RAW.
    enc_labels, enc_probs = _enc_source_labels_and_probs(config)
    enc_sources = rng.choice(enc_labels, size=n, p=enc_probs)

    # ── jopara_flag ────────────────────────────────────────────────────────────
    jopara_flags = language_buckets == "jopara_bilingual"

    df = pd.DataFrame(
        {
            ENTITY_ID: entity_ids,
            DEPARTMENT: departments,
            MUNICIPALITY: municipalities,
            GENDER: genders,
            AGE_ON_EVENT_DATE: ages,
            RURAL_FLAG: rural_flags,
            RURAL_FLAG_DERIVED: rural_flag_derived,
            LANGUAGE_CENSUS_BUCKET: language_buckets,
            JOPARA_FLAG: jopara_flags,
            PREFERENCE_PROXY: preference_proxies,
            PREFERENCE_PROXY_STRENGTH: preference_proxy_strengths,
            STRUCTURAL_DEPENDENCY_PROXY: structural_dependency,
            INTERNET_ACCESS_FLAG: internet_access_flags,
            MEDIA_PENETRATION_TV: tv_pen,
            MEDIA_PENETRATION_RADIO: radio_pen,
            MEDIA_PENETRATION_WHATSAPP: whatsapp_pen,
            NBI_STRESS_PRIOR: nbi_vals,
            BALLOT_BLANK_PRESIDENT: ballot_blank_pres,
            BALLOT_BLANK_PARLASUR: ballot_blank_parl,
            ENC_SOURCE_RAW: enc_sources,
        }
    )

    if output_path is not None:
        df.to_parquet(output_path, index=False)

    return df


# ─── Helpers ─────────────────────────────────────────────────────────────────

# Representative main cities per department (clean names; flaws injected later)
_MAIN_MUNICIPALITIES: dict[str, list[str]] = {
    "Asuncion": ["Asuncion"],
    "Central": ["Luque", "San Lorenzo", "Fernando de la Mora", "Lambare", "Capiata"],
    "Alto Parana": ["Ciudad del Este", "Hernandarias", "Minga Guazu"],
    "Itapua": ["Encarnacion", "Coronel Bogado", "Bella Vista"],
    "Caaguazu": ["Coronel Oviedo", "Caaguazu", "Vaqueria"],
    "San Pedro": ["San Pedro del Ycuamandyyu", "Lima", "Guayaibis"],
    "Cordillera": ["Caacupe", "Altos", "Tobati"],
    "Paraguari": ["Paraguari", "Carapegua", "Yaguaron"],
    "Misiones": ["San Juan Bautista", "Santa Rosa", "San Miguel"],
    "Guaira": ["Villarrica", "Borja", "Mbocayaty"],
    "Amambay": ["Pedro Juan Caballero", "Bella Vista Norte", "Capitan Bado"],
    "Canindeyu": ["Salto del Guaira", "Corpus Christi", "Curuguaty"],
    "Caazapa": ["Caazapa", "San Juan Nepomuceno", "Buena Vista"],
    "Neembucu": ["Pilar", "Alberdi", "Desmochados"],
    "Concepcion": ["Concepcion", "Belen", "San Carlos"],
    "Presidente Hayes": ["Villa Hayes", "Benjamin Aceval", "Pozo Colorado"],
    "Boqueron": ["Filadelfia", "Loma Plata", "Mariscal Estigarribia"],
    "Alto Paraguay": ["Fuerte Olimpo", "Bahia Negra", "Carmelo Peralta"],
}


def _assign_municipalities(
    departments: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    result = np.empty(len(departments), dtype=object)
    unique_depts = np.unique(departments)
    for dept in unique_depts:
        mask = departments == dept
        options = _MAIN_MUNICIPALITIES.get(dept, [dept])
        n_mask = int(mask.sum())
        result[mask] = rng.choice(options, size=n_mask)
    return result


def _rake_binary(
    arr: np.ndarray,
    target: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Rake a boolean array to the target True rate via random flipping."""
    arr = arr.copy()
    current = arr.mean()
    n = len(arr)
    if current < target:
        candidates = np.where(~arr)[0]
        n_flip = int(round((target - current) * n))
        n_flip = min(n_flip, len(candidates))
        idx = rng.choice(candidates, size=n_flip, replace=False)
        arr[idx] = True
    elif current > target:
        candidates = np.where(arr)[0]
        n_flip = int(round((current - target) * n))
        n_flip = min(n_flip, len(candidates))
        idx = rng.choice(candidates, size=n_flip, replace=False)
        arr[idx] = False
    return arr


def _rake_categorical(
    arr: np.ndarray,
    targets: dict[str, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """Rake a categorical array to target marginal proportions via random reassignment.

    Uses a single O(n) scan to bucket row indices by current label, then reassigns
    by sampling donor indices from pre-built pools (no per-label full-array ``where``).
    Total work is linear in *n* and the number of label moves.
    """
    arr = arr.copy()
    n = len(arr)
    labels = list(targets.keys())
    target_counts = {k: int(round(v * n)) for k, v in targets.items()}
    # Adjust to ensure counts sum to n
    delta = n - sum(target_counts.values())
    if delta != 0:
        target_counts[labels[0]] += delta

    idx_by_label: dict[str, list[int]] = {k: [] for k in labels}
    for i in range(n):
        lab = str(arr[i])
        if lab in idx_by_label:
            idx_by_label[lab].append(i)

    current_counts = {k: len(idx_by_label[k]) for k in labels}

    for label, target_count in target_counts.items():
        diff = target_count - current_counts.get(label, 0)
        if diff <= 0:
            continue
        over = [k for k in labels if current_counts.get(k, 0) > target_counts.get(k, 0)]
        for donor in over:
            available = current_counts[donor] - target_counts.get(donor, 0)
            to_move = min(diff, available)
            if to_move <= 0:
                continue
            pool = idx_by_label[donor]
            pick = rng.choice(len(pool), size=to_move, replace=False)
            keep = np.ones(len(pool), dtype=bool)
            keep[pick] = False
            idx_by_label[donor] = [pool[i] for i in range(len(pool)) if keep[i]]
            chosen_pos = [pool[int(j)] for j in pick]
            for pos in chosen_pos:
                arr[pos] = label
            idx_by_label[label].extend(chosen_pos)
            current_counts[donor] -= to_move
            current_counts[label] = current_counts.get(label, 0) + to_move
            diff -= to_move
            if diff <= 0:
                break
    return arr


def _assign_language(
    departments: np.ndarray,
    rural_flags: np.ndarray,
    lang_priors: dict[str, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """Assign language buckets calibrated to national priors.

    Rural areas have elevated Guaraní-only; Asunción/Central have elevated Spanish-only.
    IPF raking to national marginals is applied in the cleaner (step 11).
    Here we do a fast proportional draw.
    """
    n = len(departments)
    labels = list(lang_priors.keys())
    probs = np.array([lang_priors[k] for k in labels], dtype=float)
    probs /= probs.sum()

    result = np.empty(n, dtype=object)

    # Rural: elevate guarani_only by +10pp, reduce others proportionally
    rural_probs = probs.copy()
    guarani_idx = labels.index("guarani_only")
    rural_probs[guarani_idx] = min(1.0, rural_probs[guarani_idx] + 0.10)
    remaining = 1.0 - rural_probs[guarani_idx]
    other_mask = np.arange(len(labels)) != guarani_idx
    rural_probs[other_mask] *= remaining / rural_probs[other_mask].sum()

    # Urban Asunción/Central: elevate spanish_only
    metro_probs = probs.copy()
    spanish_idx = labels.index("spanish_only")
    metro_probs[spanish_idx] = min(1.0, metro_probs[spanish_idx] + 0.08)
    remaining_m = 1.0 - metro_probs[spanish_idx]
    other_m = np.arange(len(labels)) != spanish_idx
    metro_probs[other_m] *= remaining_m / metro_probs[other_m].sum()

    metro_mask = np.isin(departments, ["Asuncion", "Central"]) & ~rural_flags
    rural_mask = rural_flags
    default_mask = ~rural_mask & ~metro_mask

    if rural_mask.sum() > 0:
        result[rural_mask] = np.array(labels)[
            rng.choice(len(labels), size=int(rural_mask.sum()), p=rural_probs)
        ]
    if metro_mask.sum() > 0:
        result[metro_mask] = np.array(labels)[
            rng.choice(len(labels), size=int(metro_mask.sum()), p=metro_probs)
        ]
    if default_mask.sum() > 0:
        result[default_mask] = np.array(labels)[
            rng.choice(len(labels), size=int(default_mask.sum()), p=probs)
        ]

    return result


if __name__ == "__main__":
    import argparse

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate synthetic population. Outputs population_raw.parquet."
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to generation.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output parquet path (default: data/raw/population_raw.parquet)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (overrides RANDOM_SEED env var)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Override generation.yaml sample_size (entity count)",
    )
    args = parser.parse_args()

    cfg = _load_config(args.config)
    if args.sample_size is not None:
        cfg["sample_size"] = int(args.sample_size)
    out = args.output or Path("data/raw/population_raw.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)

    df = generate_population(cfg, seed=args.seed, output_path=out)
    print(f"Generated {len(df):,} entities → {out}")
    print(f"Columns: {list(df.columns)}")
