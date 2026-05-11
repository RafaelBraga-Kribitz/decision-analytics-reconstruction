"""Single source for conglomerate bundle metadata (Module B).

Used by the canonical allocator facade and counterfactual engines. Values
mirror ``config/channel_bundles.yaml`` minimum shares from the plan.
"""

from __future__ import annotations

from typing import Final

from module_b_resource_allocation.constants import CAMPAIGN_BUDGET_USD

# Map channel → bundle id (subset of channels belong to a bundle).
CHANNEL_TO_BUNDLE: Final[dict[str, str]] = {
    "tv_spots": "conglomerate_x",
    "radio_spots": "conglomerate_x",
    "billboards": "conglomerate_x",
    "facebook_ads": "conglomerate_y",
    "whatsapp_chatbot": "conglomerate_y",
    "canvassing": "field_ops_bundle",
    "rallies_events": "field_ops_bundle",
    "sound_cars": "field_ops_bundle",
}

_BUNDLE_MIN_SHARE: Final[dict[str, float]] = {
    "conglomerate_x": 0.04,
    "conglomerate_y": 0.03,
    "field_ops_bundle": 0.05,
}

BUNDLE_MIN_USD: Final[dict[str, float]] = {
    k: v * CAMPAIGN_BUDGET_USD for k, v in _BUNDLE_MIN_SHARE.items()
}

# Back-compat alias for older imports.
_CHANNEL_TO_BUNDLE = CHANNEL_TO_BUNDLE
