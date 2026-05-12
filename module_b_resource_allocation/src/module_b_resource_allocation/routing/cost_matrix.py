"""Department × department routing cost matrix (Phase 8).

Builds a symmetric inter-department travel-time matrix tagged with surface
class, weather impassability probability, and shift-cap feasibility under one
of three scenarios:

* ``dry_standard`` — baseline Jan–Apr 2018 weekday conditions.
* ``wet_election_week`` — campaign-week rain spike (Oriente unpaved edges
  experience reduced feasibility; Chaco edges become impassable more often).
* ``chaco_stress`` — chaco-only stress scenario; >=90% of Chaco-touching
  edges resolve to unpaved/earth_track surface.

Anchors (PRIOR provenance):

* National paved-road share ≈ 8.7%.
* National earth-track share ≈ 86%.
* Oriental-corridor straight-line distances inferred from departmental
  centroids (synthetic anchored prior).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Final

import pandas as pd

from module_b_resource_allocation.constants import CHACO_DEPARTMENTS, DEPARTMENTS, region_for

# Synthetic centroid coordinates (lat, lon) for departments — PRIOR anchors
# good enough to drive a stable distance prior.  Replace with verified
# DGEEC/INE centroids during portfolio hardening.
_CENTROIDS: Final[dict[str, tuple[float, float]]] = {
    "Asuncion": (-25.30, -57.63),
    "Concepcion": (-23.40, -57.43),
    "San Pedro": (-24.10, -56.60),
    "Cordillera": (-25.32, -56.83),
    "Guaira": (-25.78, -56.45),
    "Caaguazu": (-25.45, -56.05),
    "Caazapa": (-26.15, -56.30),
    "Itapua": (-27.10, -55.85),
    "Misiones": (-26.85, -57.10),
    "Paraguari": (-25.62, -57.15),
    "Alto Parana": (-25.50, -54.85),
    "Central": (-25.40, -57.45),
    "Neembucu": (-26.92, -58.20),
    "Amambay": (-22.55, -56.05),
    "Canindeyu": (-24.20, -55.30),
    "Presidente Hayes": (-23.30, -59.30),
    "Boqueron": (-21.50, -60.40),
    "Alto Paraguay": (-20.20, -59.40),
}

_SHIFT_CAP_MINUTES: Final[int] = 8 * 60


_SCENARIOS: Final[frozenset[str]] = frozenset({"dry_standard", "wet_election_week", "chaco_stress"})


@dataclass(frozen=True)
class SurfaceMix:
    """Per-edge proportions of paved / unpaved-tertiary / earth-track surface."""

    paved: float
    unpaved_tertiary: float
    earth_track: float


def _great_circle_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Haversine distance in km between two (lat, lon) tuples."""
    r = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(h))


def _surface_mix(origin: str, dest: str, scenario: str, rng: random.Random) -> SurfaceMix:
    """Return surface mix shares per scenario.

    Oriente↔Oriente edges: high paved share on the Asunción–Ciudad del Este
    corridor (Itapua, Alto Parana, Central, Asuncion, Caaguazu); other Oriente
    pairs mix unpaved/earth.

    Chaco-touching edges: dominated by unpaved/earth tracks; stressed
    further by ``chaco_stress``.
    """
    o_chaco = origin in CHACO_DEPARTMENTS
    d_chaco = dest in CHACO_DEPARTMENTS
    corridor = {"Asuncion", "Central", "Caaguazu", "Alto Parana", "Itapua"}

    if origin == dest:
        return SurfaceMix(1.0, 0.0, 0.0)

    if o_chaco or d_chaco:
        if scenario == "chaco_stress":
            return SurfaceMix(0.02, 0.10, 0.88)
        if scenario == "wet_election_week":
            return SurfaceMix(0.05, 0.10, 0.85)
        return SurfaceMix(0.08, 0.12, 0.80)

    if origin in corridor and dest in corridor:
        return SurfaceMix(0.90, 0.08, 0.02)
    return SurfaceMix(0.20, 0.45, 0.35)


def _weather_p_fail(origin: str, dest: str, scenario: str) -> float:
    base = 70.0 / 365.0
    chaco = origin in CHACO_DEPARTMENTS or dest in CHACO_DEPARTMENTS
    if scenario == "dry_standard":
        return base * 0.50 if not chaco else base * 1.20
    if scenario == "wet_election_week":
        return base * 2.30 if not chaco else base * 4.50
    if scenario == "chaco_stress":
        return base * 1.00 if not chaco else base * 6.50
    return base


def _surface_class_for(mix: SurfaceMix) -> str:
    """Dominant surface class for the edge."""
    if mix.paved >= max(mix.unpaved_tertiary, mix.earth_track):
        return "paved"
    if mix.unpaved_tertiary >= mix.earth_track:
        return "unpaved_tertiary"
    return "earth_track"


def _time_multiplier(surface_class: str, scenario: str) -> float:
    base = {"paved": 1.0, "unpaved_tertiary": 3.0, "earth_track": 5.0}[surface_class]
    if scenario == "wet_election_week" and surface_class != "paved":
        base *= 1.15
    return base


def build_cost_matrix(scenario: str = "dry_standard", seed: int = 42) -> pd.DataFrame:
    """Build the directed routing cost matrix for ``scenario``.

    Args:
        scenario: Routing scenario label (see module-local ``_SCENARIOS``).
        seed: Integer seed for ``random.Random`` when sampling surface mixes and
            tie breaks. The same ``(scenario, seed)`` pair yields an identical
            DataFrame across runs (stdlib RNG only).

    Returns:
        Edge list with travel times, weather failure probabilities, and feasibility flags.

    Raises:
        ValueError: If ``scenario`` is not a supported routing label.

    Example:
        ``build_cost_matrix(\"dry_standard\", seed=42)`` feeds counterfactual routing checks.
    """
    if scenario not in _SCENARIOS:
        raise ValueError(f"Unknown routing scenario {scenario!r}; valid: {sorted(_SCENARIOS)}")
    rng = random.Random(seed)

    rows: list[dict[str, object]] = []
    for o in DEPARTMENTS:
        for d in DEPARTMENTS:
            if o == d:
                surface_class = "paved"
                mix = SurfaceMix(1.0, 0.0, 0.0)
                travel_time = 0.0
                base_km = 0.0
                p_fail = 0.0
                edge_feasible = True
                time_mult = 1.0
                tau_walk_mean = 0.0
                tau_walk_p95 = 0.0
            else:
                base_km = (
                    _great_circle_km(_CENTROIDS[o], _CENTROIDS[d]) * 1.18
                )  # routing detour factor
                mix = _surface_mix(o, d, scenario, rng)
                surface_class = _surface_class_for(mix)
                time_mult = _time_multiplier(surface_class, scenario)
                # Effective speed is the surface-mix-weighted blend of:
                # paved 80 km/h, unpaved-tertiary 35 km/h, earth-track 22 km/h.
                # The wet_election_week scenario also slows non-paved travel
                # by an additional 15% via _time_multiplier.
                effective_speed = (
                    mix.paved * 80.0 + mix.unpaved_tertiary * 35.0 + mix.earth_track * 22.0
                )
                travel_hours = base_km / effective_speed
                if scenario == "wet_election_week":
                    # Non-paved share gets 15% time penalty.
                    travel_hours *= 1.0 + 0.15 * (1.0 - mix.paved)
                travel_time = travel_hours * 60.0
                p_fail = _weather_p_fail(o, d, scenario)
                tau_walk_mean = 6.0 if surface_class == "earth_track" else 3.0
                tau_walk_p95 = tau_walk_mean * 2.5

                edge_feasible = travel_time <= _SHIFT_CAP_MINUTES and p_fail < 0.45

            rows.append(
                {
                    "origin_department": o,
                    "destination_department": d,
                    "scenario_id": scenario,
                    "region_pair": _region_pair(o, d),
                    "surface_class": surface_class,
                    "surface_share_paved": mix.paved,
                    "surface_share_unpaved": mix.unpaved_tertiary,
                    "surface_share_earth_track": mix.earth_track,
                    "base_distance_km": round(base_km, 3),
                    "time_multiplier": time_mult,
                    "travel_time_minutes": round(travel_time, 3),
                    "weather_p_fail": round(p_fail, 4),
                    "tau_walk_minutes_mean": tau_walk_mean,
                    "tau_walk_minutes_p95": tau_walk_p95,
                    "edge_feasible": bool(edge_feasible),
                }
            )

    return pd.DataFrame(rows)


def _region_pair(origin: str, dest: str) -> str:
    if origin == dest:
        return "SELF"
    o = region_for(origin)
    d = region_for(dest)
    if o == d == "ORIENTAL":
        return "ORIENTAL_ORIENTAL"
    if o == d == "CHACO":
        return "CHACO_CHACO"
    return "ORIENTAL_CHACO"
