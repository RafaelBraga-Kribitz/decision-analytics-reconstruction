"""Strategic district tier clustering for Module B (Phase 6).

Assigns each of the 18 departments to one of four strategic tiers
(plan §Methodology and §Clean schema additions):

  - **stronghold**:  high base propensity, low marginal return on spend.
  - **swing**:       contested; highest marginal return per dollar.
  - **opposition**:  dominated by opposing faction; diminishing returns steep.
  - **negligible**:  very small population share; cap-rate spend only.

Tiers are priors based on 2018 Paraguay electoral context (ESTIMATED).
They should be hardened against TSJE 2018 department-level results in a
follow-up verification cycle.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

from module_b_resource_allocation.constants import DEPARTMENTS, region_for

# Each department assigned to one of 4 strategic tiers (ESTIMATED priors).
# Sources: Paraguayan 2018 outcome event context, department-level
# propensity anchors, historical TSJE departmental margins.
_TIER_MAP: Final[dict[str, str]] = {
    # Stronghold — campaign's base vote; diminishing returns dominate
    "Central": "stronghold",
    "Asuncion": "stronghold",
    "Cordillera": "stronghold",
    "Paraguari": "stronghold",
    # Swing — contested; highest value per dollar
    "Alto Parana": "swing",
    "Itapua": "swing",
    "Caaguazu": "swing",
    "Amambay": "swing",
    "Canindeyu": "swing",
    "San Pedro": "swing",
    # Opposition — dominated by competing faction; small marginal return
    "Concepcion": "opposition",
    "Guaira": "opposition",
    "Caazapa": "opposition",
    "Misiones": "opposition",
    "Neembucu": "opposition",
    # Negligible — tiny population + logistics cost; minimal allocation
    "Presidente Hayes": "negligible",
    "Boqueron": "negligible",
    "Alto Paraguay": "negligible",
}


def build_district_tiers() -> pd.DataFrame:
    """Return the 18-row district tier table.

    Returns
    -------
    pd.DataFrame
        Columns: department, region, department_tier, provenance.
    """
    rows = [
        {
            "department": dept,
            "region": region_for(dept),
            "department_tier": _TIER_MAP[dept],
            "provenance": "ESTIMATED",
        }
        for dept in DEPARTMENTS
    ]
    return pd.DataFrame(rows)
