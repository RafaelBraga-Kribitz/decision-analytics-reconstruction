"""Canonical constants for Module B.

These values are the single source of truth for every other Module B module.
Anything that needs the channel taxonomy, department list, Chaco set, or
campaign weekly grid MUST import from this file rather than re-declaring it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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
    persuasion_attention: float  # alpha_*
    salience_psi: float  # psi_*
    hostility_zeta: float  # zeta_network


CHANNELS: Final[tuple[ChannelSpec, ...]] = (
    ChannelSpec("whatsapp_chatbot", "bilateral", "REF", 0.62, 1.00, 1.00),
    ChannelSpec("messenger_chatbot", "bilateral", "REF", 0.58, 0.95, 1.00),
    ChannelSpec("facebook_ads", "broadcast", "REF", 0.41, 0.90, 1.00),
    ChannelSpec("sms", "bilateral", "RETAIL", 0.50, 0.85, 1.00),
    ChannelSpec("email", "bilateral", "REF", 0.28, 0.65, 1.00),
    ChannelSpec("tv_spots", "broadcast", "REF", 0.46, 1.10, 0.70),
    ChannelSpec("radio_spots", "broadcast", "RETAIL", 0.57, 1.05, 1.00),
    ChannelSpec("billboards", "broadcast", "RETAIL", 0.30, 0.75, 1.00),
    ChannelSpec("rallies_events", "in_person", "RETAIL", 0.78, 1.15, 1.00),
    ChannelSpec("canvassing", "in_person", "RETAIL", 0.83, 1.20, 1.00),
    ChannelSpec("sound_cars", "broadcast_to_bilateral", "RETAIL", 0.41, 0.90, 1.00),
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
# Campaign envelope (Jan–Apr 2018 reconstruction): USD 6,000,000 ± 0.5%.
# NOTE [T11-2]: Real ANR 2018 advertising budget was ~USD 44,000,000 (verified
# from investigative audits); current $6M is methodological reconstruction scale.
# Field staff scale: real deployment was 70,000+ (36k mesarios, 12k veedores,
# 1k apoderados + thousands operadores), not 5,000 estimate.
# ---------------------------------------------------------------------------
CAMPAIGN_BUDGET_USD: Final[float] = 6_000_000.0
CAMPAIGN_BUDGET_TOLERANCE: Final[float] = 0.005
COVERAGE_LOWER_BOUND_PCT: Final[float] = 0.80
BCP_CORRIDOR_MAX_PCT: Final[float] = 0.10
FX_BAND_MAX_PCT_VS_BCP: Final[float] = 0.005


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
