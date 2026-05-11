"""Schema definitions and shared type aliases for Module A.

Canonical column names are defined here once and imported everywhere.
Never use bare string literals for column names in src/.
"""

from __future__ import annotations

from typing import Final

# ─── Core entity fields ───────────────────────────────────────────────────────
ENTITY_ID: Final = "entity_id"
CEDULA: Final = "cedula"
CEDULA_INVALID: Final = "cedula_invalid"
FIRST_NAME: Final = "first_name"
LAST_NAME: Final = "last_name"

# ─── Geographic fields ────────────────────────────────────────────────────────
DEPARTMENT: Final = "department"
MUNICIPALITY: Final = "municipality"
MUNICIPALITY_IMPUTED: Final = "municipality_imputed"
RURAL_FLAG: Final = "rural_flag"
RURAL_FLAG_DERIVED: Final = "rural_flag_derived"

# ─── Demographic fields ───────────────────────────────────────────────────────
DOB: Final = "dob"
AGE_ON_EVENT_DATE: Final = "age_on_event_date"
AGE_OUT_OF_RANGE: Final = "age_out_of_range"
DOB_AMBIGUOUS: Final = "dob_ambiguous"
GENDER: Final = "gender"
PHONE: Final = "phone"
PHONE_INVALID: Final = "phone_invalid"

# ─── Language fields ──────────────────────────────────────────────────────────
LANGUAGE_CENSUS_BUCKET: Final = "language_census_bucket"
JOPARA_FLAG: Final = "jopara_flag"

# ─── Behavioral / proxy fields ────────────────────────────────────────────────
PREFERENCE_PROXY: Final = "preference_proxy"
PREFERENCE_PROXY_STRENGTH: Final = "preference_proxy_strength"
STRUCTURAL_DEPENDENCY_PROXY: Final = "structural_dependency_proxy"
PARTICIPATION_PROPENSITY: Final = "participation_propensity"
RAW_LOGIT_SCORE: Final = "raw_logit_score"
DEPARTMENT_RAKE_MULTIPLIER: Final = "department_rake_multiplier"

# ─── Media / reachability fields ──────────────────────────────────────────────
INTERNET_ACCESS_FLAG: Final = "internet_access_flag"
MEDIA_PENETRATION_TV: Final = "media_penetration_tv"
MEDIA_PENETRATION_RADIO: Final = "media_penetration_radio"
MEDIA_PENETRATION_WHATSAPP: Final = "media_penetration_whatsapp"

# ─── Socioeconomic fields ─────────────────────────────────────────────────────
NBI_STRESS_PRIOR: Final = "nbi_stress_prior"

# ─── Segmentation fields ──────────────────────────────────────────────────────
SEGMENT_LABEL: Final = "segment_label"
SEGMENT_ID: Final = "segment_id"
DBSCAN_NOISE_FLAG: Final = "dbscan_noise_flag"

# ─── Ballot fields ────────────────────────────────────────────────────────────
BALLOT_BLANK_PRESIDENT: Final = "ballot_blank_president"
BALLOT_BLANK_PARLASUR: Final = "ballot_blank_parlasur"

# ─── Quality flags ────────────────────────────────────────────────────────────
ENC_SOURCE: Final = "enc_source"
ENC_SOURCE_RAW: Final = "enc_source_raw"

# ─── Canonical allowed values ─────────────────────────────────────────────────
CANONICAL_DEPARTMENTS: Final = frozenset(
    {
        "Asuncion",
        "Concepcion",
        "San Pedro",
        "Cordillera",
        "Guaira",
        "Caaguazu",
        "Caazapa",
        "Itapua",
        "Misiones",
        "Paraguari",
        "Alto Parana",
        "Central",
        "Neembucu",
        "Amambay",
        "Canindeyu",
        "Presidente Hayes",
        "Boqueron",
        "Alto Paraguay",
    }
)

CANONICAL_GENDER: Final = frozenset({"M", "F", "unknown"})

CANONICAL_LANGUAGE: Final = frozenset(
    {
        "jopara_bilingual",
        "guarani_only",
        "spanish_only",
        "other",
    }
)

CANONICAL_PREFERENCE_PROXY: Final = frozenset({"A", "B", "other", "none"})

CANONICAL_SEGMENT_LABELS: Final = frozenset(
    {
        "rural_committed",
        "urban_high_volatility",
        "youth_volatile",
        "structurally_dependent_bloc",
        "rural_low_propensity",
        "committed_opposition",
    }
)

CANONICAL_ENC_SOURCE: Final = frozenset({"windows1252", "utf8", "unknown"})

CANONICAL_REACH_CHANNELS: Final = frozenset({"tv", "radio", "whatsapp", "direct"})

# ─── Engineered feature constants ─────────────────────────────────────────────
# Derived columns produced by features/ and used in model_params.yaml.
# Kept separate from raw constants so schema.py never references
# implementation-specific logic; all names must match model_params.yaml exactly.
AGE_BIN: Final = "age_bin"
AGE_BIN_ENCODED: Final = "age_bin_encoded"
GENDER_ENCODED: Final = "gender_encoded"
YOUTH_FLAG: Final = "youth_flag"
SENIOR_FLAG: Final = "senior_flag"
METRO_FLAG: Final = "metro_flag"
CHACO_FLAG: Final = "chaco_flag"
DEPARTMENT_REGION: Final = "department_region"
PREFERENCE_PROXY_ENCODED: Final = "preference_proxy_encoded"
STRUCTURAL_DEPENDENCY_ENCODED: Final = "structural_dependency_encoded"
LANGUAGE_JOPARA_ENCODED: Final = "language_jopara_encoded"
LANGUAGE_GUARANI_FLAG: Final = "language_guarani_flag"
NBI_STRESS_PRIOR_SCALED: Final = "nbi_stress_prior_scaled"
REACHABILITY_DIGITAL: Final = "reachability_digital"
REACHABILITY_BROADCAST_TV: Final = "reachability_broadcast_tv"
REACHABILITY_BROADCAST_RADIO: Final = "reachability_broadcast_radio"
REACHABILITY_INDEX: Final = "reachability_index"
REACHABILITY_TIER: Final = "reachability_tier"
URBAN_DIGITAL_COMPOUND: Final = "urban_digital_compound"
RURAL_OFFLINE_COMPOUND: Final = "rural_offline_compound"
GENDER_YOUTH_INTERACTION: Final = "gender_youth_interaction"
DEPARTMENT_LOGIT_OFFSET: Final = "department_logit_offset"

SCHEMA_DRIFT_FLAG: Final = "schema_drift_flag"
QUALITATIVE_SENTIMENT: Final = "qualitative_sentiment"
QUALITATIVE_DISTRICT: Final = "qualitative_district"
