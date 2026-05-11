"""Synthetic population generator.

Produces a DataFrame of N synthetic entities calibrated to TSJE/DGEEC
verified demographic anchors. Uses IPF/raking logic to enforce marginals.
All random operations use an explicitly seeded numpy Generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

# ─── Media penetration lookup ─────────────────────────────────────────────────
# Department-level TV penetration; from DGEEC/media survey; national ~0.89
_TV_BY_DEPT: dict[str, float] = {
    "Asuncion": 0.98,
    "Central": 0.97,
    "Alto Parana": 0.92,
    "Itapua": 0.87,
    "Caaguazu": 0.83,
    "San Pedro": 0.75,
    "Cordillera": 0.82,
    "Paraguari": 0.80,
    "Misiones": 0.85,
    "Guaira": 0.84,
    "Amambay": 0.88,
    "Canindeyu": 0.74,
    "Caazapa": 0.73,
    "Neembucu": 0.82,
    "Concepcion": 0.81,
    "Presidente Hayes": 0.70,
    "Boqueron": 0.65,
    "Alto Paraguay": 0.62,
}
_RADIO_BY_DEPT: dict[str, float] = {
    "Asuncion": 0.90,
    "Central": 0.89,
    "Alto Parana": 0.85,
    "Itapua": 0.82,
    "Caaguazu": 0.80,
    "San Pedro": 0.78,
    "Cordillera": 0.80,
    "Paraguari": 0.79,
    "Misiones": 0.82,
    "Guaira": 0.81,
    "Amambay": 0.83,
    "Canindeyu": 0.77,
    "Caazapa": 0.76,
    "Neembucu": 0.80,
    "Concepcion": 0.80,
    "Presidente Hayes": 0.74,
    "Boqueron": 0.70,
    "Alto Paraguay": 0.68,
}
_NBI_RURAL_BY_DEPT: dict[str, float] = {
    "Asuncion": 0.15,
    "Central": 0.20,
    "Alto Parana": 0.55,
    "Itapua": 0.60,
    "Caaguazu": 0.65,
    "San Pedro": 0.78,
    "Cordillera": 0.62,
    "Paraguari": 0.63,
    "Misiones": 0.58,
    "Guaira": 0.61,
    "Amambay": 0.57,
    "Canindeyu": 0.80,
    "Caazapa": 0.82,
    "Neembucu": 0.66,
    "Concepcion": 0.72,
    "Presidente Hayes": 0.75,
    "Boqueron": 0.73,
    "Alto Paraguay": 0.76,
}
_NBI_URBAN_BY_DEPT: dict[str, float] = {
    d: max(0.10, v * 0.35) for d, v in _NBI_RURAL_BY_DEPT.items()
}

# Structural dependency elevated in high-NBI rural departments
_STRUCTURAL_DEP_ELEVATED: frozenset[str] = frozenset(
    {
        "San Pedro",
        "Caazapa",
        "Canindeyu",
        "Concepcion",
        "Paraguari",
    }
)


def _load_config(config_path: str | Path) -> dict[str, Any]:
    with open(config_path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def generate_population(
    config: dict[str, Any],
    seed: int | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Generate a synthetic population DataFrame.

    Args:
        config: Generation configuration dict (from generation.yaml).
        seed:   Random seed. If None, reads RANDOM_SEED env var.
        output_path: Optional parquet path to write output.

    Returns:
        DataFrame with one row per entity; columns match
        schema_contracts/population_master_raw.yaml.
    """
    rng = make_rng(seed)
    n = int(config["sample_size"])

    dept_weights_raw: dict[str, float] = config["department_weights"]
    dept_names = list(dept_weights_raw.keys())
    dept_probs = np.array([dept_weights_raw[d] for d in dept_names], dtype=float)
    dept_probs /= dept_probs.sum()

    dept_urban_share: dict[str, float] = config["department_urban_share"]

    # ── entity_id ──────────────────────────────────────────────────────────────
    entity_ids = np.arange(1, n + 1, dtype=np.int64)

    # ── department ─────────────────────────────────────────────────────────────
    dept_indices = rng.choice(len(dept_names), size=n, p=dept_probs)
    departments = np.array(dept_names, dtype=object)[dept_indices]

    # ── rural_flag (preliminary — derived from department urban share) ─────────
    rural_flags = np.zeros(n, dtype=bool)
    for i, dept in enumerate(dept_names):
        mask = dept_indices == i
        urban_p = dept_urban_share.get(dept, 0.617)
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

    # ── Rake rural_flag to national anchor (38.3%) ────────────────────────────
    rural_flags = _rake_binary(rural_flags, target=0.383, rng=rng)

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
    ict = config.get("media_penetration_defaults", {})
    urban_inet = float(ict.get("whatsapp_urban", 0.74))
    # Approximate internet access from ICT anchors
    inet_prob = np.where(rural_flags, 0.279, 0.734)
    internet_access_flags = rng.random(n) < inet_prob

    # ── media penetration ──────────────────────────────────────────────────────
    tv_pen = np.array([_TV_BY_DEPT.get(d, 0.89) for d in departments], dtype=np.float32)
    radio_pen = np.array([_RADIO_BY_DEPT.get(d, 0.82) for d in departments], dtype=np.float32)
    whatsapp_pen = np.where(rural_flags, urban_inet * 0.42, urban_inet).astype(np.float32)

    # ── nbi_stress_prior ───────────────────────────────────────────────────────
    nbi_vals = np.where(
        rural_flags,
        np.array([_NBI_RURAL_BY_DEPT.get(d, 0.659) for d in departments]),
        np.array([_NBI_URBAN_BY_DEPT.get(d, 0.252) for d in departments]),
    ).astype(np.float32)
    nbi_noise = rng.normal(0, 0.03, size=n).astype(np.float32)
    nbi_vals = np.clip(nbi_vals + nbi_noise, 0.0, 1.0).astype(np.float32)

    # ── structural_dependency_proxy ────────────────────────────────────────────
    base_dep_prob = np.where(rural_flags, 0.35, 0.12)
    elevated_mask = np.array([d in _STRUCTURAL_DEP_ELEVATED for d in departments])
    dep_prob = np.where(elevated_mask & rural_flags, 0.60, base_dep_prob)
    structural_dependency = rng.random(n) < dep_prob

    # ── ballot blanks ──────────────────────────────────────────────────────────
    ballot_blank_pres = rng.random(n) < 0.0241
    ballot_blank_parl = rng.random(n) < 0.0848

    # ── enc_source_raw ─────────────────────────────────────────────────────────
    # Raw layer uses enc_source_raw; cleaner renames to enc_source in step 2.
    enc_sources = rng.choice(
        ["windows1252", "utf8", "unknown"],
        size=n,
        p=[0.45, 0.50, 0.05],
    )

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
    """Rake a categorical array to target marginal proportions via random reassignment."""
    arr = arr.copy()
    n = len(arr)
    labels = list(targets.keys())
    target_counts = {k: int(round(v * n)) for k, v in targets.items()}
    # Adjust to ensure counts sum to n
    delta = n - sum(target_counts.values())
    if delta != 0:
        target_counts[labels[0]] += delta

    current_counts = {k: int((arr == k).sum()) for k in labels}
    for label, target_count in target_counts.items():
        diff = target_count - current_counts.get(label, 0)
        if diff > 0:
            # Need more of this label — steal from over-represented labels
            over = [k for k in labels if current_counts.get(k, 0) > target_counts[k]]
            for donor in over:
                available = int((arr == donor).sum()) - target_counts[donor]
                to_move = min(diff, available)
                if to_move <= 0:
                    continue
                donor_idx = rng.choice(np.where(arr == donor)[0], size=to_move, replace=False)
                arr[donor_idx] = label
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
    args = parser.parse_args()

    cfg = _load_config(args.config)
    out = args.output or Path("data/raw/population_raw.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)

    df = generate_population(cfg, seed=args.seed, output_path=out)
    print(f"Generated {len(df):,} entities → {out}")
    print(f"Columns: {list(df.columns)}")
