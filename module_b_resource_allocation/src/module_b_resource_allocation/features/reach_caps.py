"""Reach caps feature builder for Module B (Phase 6).

Produces the 18×11=198-row ``reachability_caps_dept_channel.csv``
from the 2018 media penetration anchors (plan §4.4) and the canonical
department/channel taxonomy.

Every row carries a ``provenance`` tag ∈ {VERIFIED, PRIOR, ESTIMATED} and
satisfies ``reach_cap_share ∈ [0, 1]``.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

from module_b_resource_allocation.constants import (
    CHACO_DEPARTMENTS,
    CHANNEL_NAMES,
    DEPARTMENTS,
    region_for,
)

# ---------------------------------------------------------------------------
# Anchors (plan §4.4)
# ---------------------------------------------------------------------------
_URBAN_INTERNET: Final[float] = 0.734
_RURAL_INTERNET: Final[float] = 0.279
_URBAN_BROADBAND: Final[float] = 0.529
_RURAL_BROADBAND: Final[float] = 0.124
_MOBILE_SAT: Final[float] = 1.0075  # subscriptions per inhabitant (cap at 1.0)

# FTA TV by department (anchored; others interpolated toward national 0.89)
_FTA_TV: Final[dict[str, float]] = {
    "Asuncion": 0.980,
    "Central": 0.980,
    "Alto Parana": 0.910,
    "Itapua": 0.910,
    "San Pedro": 0.775,
    "Concepcion": 0.775,
}
_FTA_TV_NATIONAL: Final[float] = 0.890
_FTA_TV_CHACO_DEFAULT: Final[float] = 0.650  # sparse rural infrastructure

# Salience scalars (plan §4.4): psi_radio, psi_tv (attention relative to direct contact)
_PSI_RADIO: Final[float] = 0.2148
_PSI_TV: Final[float] = 0.1290
_ALPHA_RADIO_AD: Final[float] = 0.57  # attentive radio listeners

# Pay-TV income gate: only these departments have sufficient urban income proxies
_PAY_TV_ELIGIBLE: Final[frozenset[str]] = frozenset({"Asuncion", "Central", "Alto Parana"})

# Rural share by department (PRIOR — to be hardened with DGEEC 2018)
_RURAL_SHARE: Final[dict[str, float]] = {
    "Asuncion": 0.00,
    "Central": 0.15,
    "Alto Parana": 0.35,
    "Itapua": 0.45,
    "San Pedro": 0.72,
    "Concepcion": 0.70,
    "Cordillera": 0.55,
    "Guaira": 0.60,
    "Caaguazu": 0.65,
    "Caazapa": 0.75,
    "Misiones": 0.60,
    "Paraguari": 0.60,
    "Neembucu": 0.65,
    "Amambay": 0.50,
    "Canindeyu": 0.70,
    "Presidente Hayes": 0.80,
    "Boqueron": 0.85,
    "Alto Paraguay": 0.90,
}


def _internet_cap(dept: str) -> float:
    rural = _RURAL_SHARE.get(dept, 0.5)
    return _URBAN_INTERNET * (1 - rural) + _RURAL_INTERNET * rural


def _fta_tv_cap(dept: str) -> float:
    if dept in _FTA_TV:
        return _FTA_TV[dept]
    if dept in CHACO_DEPARTMENTS:
        return _FTA_TV_CHACO_DEFAULT
    return _FTA_TV_NATIONAL


def _mobile_cap(_dept: str) -> float:
    return min(1.0, _MOBILE_SAT)


_CHANNEL_CAP_FUNC: dict[str, object] = {
    "whatsapp_chatbot": _internet_cap,
    "messenger_chatbot": _internet_cap,
    "facebook_ads": _internet_cap,
    "sms": _mobile_cap,
    "email": _internet_cap,
    "tv_spots": _fta_tv_cap,
    "radio_spots": lambda d: 0.85 if d in CHACO_DEPARTMENTS else 0.90,
    "billboards": lambda d: 0.80 if d == "Asuncion" else (0.60 if d in CHACO_DEPARTMENTS else 0.70),
    "rallies_events": lambda d: 0.50,
    "canvassing": lambda d: 0.45,
    "sound_cars": lambda d: 0.40 if d in CHACO_DEPARTMENTS else 0.55,
}

_SALIENCE: dict[str, float] = {
    "radio_spots": _PSI_RADIO,
    "tv_spots": _PSI_TV,
}
_ATTENTION: dict[str, float] = {
    "radio_spots": _ALPHA_RADIO_AD,
}

_PROVENANCE: dict[str, str] = {
    "tv_spots": "PRIOR",  # FTA anchored for key depts, rest interpolated
    "radio_spots": "ESTIMATED",
    "whatsapp_chatbot": "PRIOR",
    "messenger_chatbot": "ESTIMATED",
    "facebook_ads": "PRIOR",
    "sms": "PRIOR",
    "email": "ESTIMATED",
    "billboards": "ESTIMATED",
    "rallies_events": "ESTIMATED",
    "canvassing": "ESTIMATED",
    "sound_cars": "ESTIMATED",
}


def build_reach_caps() -> pd.DataFrame:
    """Build the 198-row reach caps table (18 departments × 11 channels).

    Args:
        None.

    Returns
    -------
    pd.DataFrame
        Columns: department, channel, region, reach_cap_share,
        pay_tv_eligible, salience_multiplier, attention_multiplier,
        network_hostility, provenance.

    Raises:
        None: This builder does not raise for canonical channel metadata.

    Example:
        First join target inside :func:`build_allocation_features`.
    """
    rows = []
    for dept in DEPARTMENTS:
        for channel in CHANNEL_NAMES:
            cap_fn = _CHANNEL_CAP_FUNC[channel]
            cap = float(cap_fn(dept))  # type: ignore[operator]  # _CHANNEL_CAP_FUNC typed dict[str, object]; values are callables at runtime

            rows.append(
                {
                    "department": dept,
                    "channel": channel,
                    "region": region_for(dept),
                    "reach_cap_share": min(1.0, max(0.0, cap)),
                    "pay_tv_eligible": (dept in _PAY_TV_ELIGIBLE) and (channel == "tv_spots"),
                    "salience_multiplier": _SALIENCE.get(channel, 1.0),
                    "attention_multiplier": _ATTENTION.get(channel, 1.0),
                    "network_hostility": 0.70 if channel == "tv_spots" else 1.0,
                    "provenance": _PROVENANCE.get(channel, "ESTIMATED"),
                }
            )
    return pd.DataFrame(rows)
