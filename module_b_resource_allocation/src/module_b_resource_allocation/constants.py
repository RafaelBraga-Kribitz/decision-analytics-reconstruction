"""Canonical constants for Module B.

These values are the single source of truth for every other Module B module.
Anything that needs the channel taxonomy, department list, Chaco set, or
campaign weekly grid MUST import from this file rather than re-declaring it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml


def _load_budget_config() -> dict[str, Any]:
    """Load budget and campaign envelope from centralized config."""
    config_path = Path(__file__).resolve().parents[2] / "config" / "budget_envelope.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Departments (18) — matches schema_contracts/*.yaml allowed_values blocks.
# ---------------------------------------------------------------------------
DEPARTMENTS: Final[tuple[str, ...]] = (
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
)

CHACO_DEPARTMENTS: Final[frozenset[str]] = frozenset(
    {"Presidente Hayes", "Boqueron", "Alto Paraguay"}
)


def region_for(department: str) -> str:
    """Map a department label to the coarse Chaco vs Oriental region bucket.

    Args:
        department: Canonical department name (see ``DEPARTMENTS``).

    Returns:
        ``CHACO`` when ``department`` is in ``CHACO_DEPARTMENTS``; otherwise
        ``ORIENTAL``.

    Raises:
        None: This function does not raise.

    Example:
        >>> region_for("Central")
        'ORIENTAL'
    """
    return "CHACO" if department in CHACO_DEPARTMENTS else "ORIENTAL"


# ---------------------------------------------------------------------------
# Canonical 11-channel taxonomy (production-ready, solver-facing).
# Bilateral / broadcast / broadcast-to-bilateral / in-person classes match
# the spec the user locked in for the LP/MILP allocator.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    channel_type: str  # bilateral | broadcast | broadcast_to_bilateral | in_person
    fx_tier_default: str  # REF | RETAIL
    persuasion_attention: float  # alpha_* — attentive-audience conversion factor
    salience_psi: float  # psi_* — salience relative to direct contact (plan §4.4)
    hostility_zeta: float  # zeta_network in (0, 1]; <1 = hostile editorial stance


# Anchored persuasion stack (plan §4.4): psi_radio = 0.2148, psi_tv = 0.1290,
# alpha_radio_ad = 0.57, zeta_tv = 0.70. Channels without a measured anchor
# carry the neutral 1.0 — they are NOT differentiated by invented multipliers.
# This tuple is the single source consumed by features/reach_caps.py.
CHANNELS: Final[tuple[ChannelSpec, ...]] = (
    ChannelSpec("whatsapp_chatbot", "bilateral", "REF", 1.00, 1.00, 1.00),
    ChannelSpec("messenger_chatbot", "bilateral", "REF", 1.00, 1.00, 1.00),
    ChannelSpec("facebook_ads", "broadcast", "REF", 1.00, 1.00, 1.00),
    ChannelSpec("sms", "bilateral", "RETAIL", 1.00, 1.00, 1.00),
    ChannelSpec("email", "bilateral", "REF", 1.00, 1.00, 1.00),
    ChannelSpec("tv_spots", "broadcast", "REF", 1.00, 0.1290, 0.70),
    ChannelSpec("radio_spots", "broadcast", "RETAIL", 0.57, 0.2148, 1.00),
    ChannelSpec("billboards", "broadcast", "RETAIL", 1.00, 1.00, 1.00),
    ChannelSpec("rallies_events", "in_person", "RETAIL", 1.00, 1.00, 1.00),
    ChannelSpec("canvassing", "in_person", "RETAIL", 1.00, 1.00, 1.00),
    ChannelSpec("sound_cars", "broadcast_to_bilateral", "RETAIL", 1.00, 1.00, 1.00),
)

CHANNEL_NAMES: Final[tuple[str, ...]] = tuple(c.name for c in CHANNELS)
CHANNEL_TYPES: Final[dict[str, str]] = {c.name: c.channel_type for c in CHANNELS}


# ---------------------------------------------------------------------------
# Weekly grid: Jan–Apr 2018 has 14 ISO weeks (W01–W14) when we anchor the
# campaign on the 14-week pre-outcome-event ramp.
# ---------------------------------------------------------------------------
WEEK_COUNT: Final[int] = 14
WEEK_LABELS: Final[tuple[str, ...]] = tuple(f"2018-W{w:02d}" for w in range(1, WEEK_COUNT + 1))
WEEK_INDEX: Final[tuple[int, ...]] = tuple(range(1, WEEK_COUNT + 1))


# ---------------------------------------------------------------------------
# Reach artifact dimensions (must match contracts).
# ---------------------------------------------------------------------------
N_DEPARTMENTS: Final[int] = len(DEPARTMENTS)
N_CHANNELS: Final[int] = len(CHANNEL_NAMES)
N_SEGMENTS: Final[int] = 6

REACH_CAPS_ROWS: Final[int] = N_DEPARTMENTS * N_CHANNELS  # 18 * 11 = 198
ALLOCATION_ROWS: Final[int] = N_DEPARTMENTS * N_CHANNELS * WEEK_COUNT  # 18 * 11 * 14 = 2772


# ---------------------------------------------------------------------------
# Campaign envelope (Jan–Apr 2018): USD 6,000,000 (methodological reconstruction).
# NOTE [T11-2]: Real ANR 2018 advertising budget was ~USD 44,000,000 [VERIFIED].
# Reconstruction uses $6M scale to match reach-cap calibration (synthetic population
# segments). To model full-scale replication, reach_caps_*.csv must be scaled 7.3×.
# Source: TSJE campaign finance declarations + investigative audits
# Field staff scale: 70,000+ (36k mesarios, 12k veedores, 1k apoderados + operadores)
# All values loaded from config/budget_envelope.yaml for centralized control.
# ---------------------------------------------------------------------------
_BUDGET_CFG = _load_budget_config().get("budget", {})
CAMPAIGN_BUDGET_USD: Final[float] = float(_BUDGET_CFG.get("total_envelope_usd", 6_000_000.0))
CAMPAIGN_BUDGET_TOLERANCE: Final[float] = float(_BUDGET_CFG.get("tolerance_pct", 0.005))
COVERAGE_LOWER_BOUND_PCT: Final[float] = float(_BUDGET_CFG.get("coverage_lower_bound_pct", 0.80))
BCP_CORRIDOR_MAX_PCT: Final[float] = float(_BUDGET_CFG.get("bcp_corridor_max_pct", 0.10))
FX_BAND_MAX_PCT_VS_BCP: Final[float] = float(_BUDGET_CFG.get("fx_band_max_pct_vs_bcp", 0.005))


# ---------------------------------------------------------------------------
# Reserved scenario tags.  Module B emits one allocation per scenario.
# ---------------------------------------------------------------------------
SCENARIO_BASELINE: Final[str] = "baseline"
SCENARIO_EARLY_LOCK: Final[str] = "early_lock"
SCENARIO_LATE_FLEX: Final[str] = "late_flex"
SCENARIO_BROADCAST_TO_DIRECT: Final[str] = "broadcast_to_direct"

VALID_SCENARIOS: Final[frozenset[str]] = frozenset(
    {SCENARIO_BASELINE, SCENARIO_EARLY_LOCK, SCENARIO_LATE_FLEX, SCENARIO_BROADCAST_TO_DIRECT}
)

VALID_PROVENANCE: Final[frozenset[str]] = frozenset({"VERIFIED", "PRIOR", "ESTIMATED"})


# ---------------------------------------------------------------------------
# API input bounds & enums
# ---------------------------------------------------------------------------
VALID_FX_SERIES: Final[frozenset[str]] = frozenset({"series_a_monthly", "series_b_weekly"})
VALID_ROUTING_SCENARIOS: Final[frozenset[str]] = frozenset(
    {"dry_standard", "wet_election_week", "chaco_stress"}
)
SEED_MIN: Final[int] = 0
SEED_MAX: Final[int] = 2**31 - 1
SHIFT_SHARE_MIN: Final[float] = 0.0
SHIFT_SHARE_MAX: Final[float] = 1.0
