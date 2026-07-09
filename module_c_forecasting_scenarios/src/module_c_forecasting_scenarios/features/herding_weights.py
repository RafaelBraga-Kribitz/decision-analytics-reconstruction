"""Herd correlation weights rho_herd in [0, 1] for shock score (modeling hypothesis).

Resolution is driven entirely by ``config/herding_groups.yaml`` — an explicit
carrier -> herding-group mapping table plus a (date-window x group) covariance
matrix. There is no substring matching: a carrier either exact-matches a table
entry (case-folded) or it resolves to the documented default group with a
logged warning. See ``config/herding_groups.yaml`` for the provenance ledger
(IMP-C04 / audit C5) backing every covariance value below.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Final

import pandas as pd
import yaml

from module_c_forecasting_scenarios.paths import module_config_dir

logger = logging.getLogger(__name__)

_MARCH_WINDOW_START: Final[date] = date(2018, 3, 15)
_MARCH_WINDOW_END: Final[date] = date(2018, 3, 31)
_APRIL_WINDOW_START: Final[date] = date(2018, 4, 1)
_APRIL_WINDOW_END: Final[date] = date(2018, 4, 15)


@dataclass(frozen=True)
class HerdingGroupResolution:
    """Outcome of resolving a carrier string to its herding group.

    Attributes:
        group: The resolved herding group (e.g. ``"elevated"``, ``"baseline"``).
        matched: ``True`` when the carrier exact-matched a config table entry
            or was null/missing (an expected, non-warning state); ``False``
            when a non-empty carrier fell through to the default group because
            it is absent from the mapping table.
        carrier_normalized: The case-folded, stripped carrier string used for
            lookup, or ``None`` when the input carrier was null/missing.
    """

    group: str
    matched: bool
    carrier_normalized: str | None


def load_herding_config() -> dict[str, object]:
    """Load ``config/herding_groups.yaml``.

    Returns:
        The parsed YAML document: ``default_group``, ``groups`` (carrier ->
        group), ``covariance_matrix`` (date-window -> group -> rho_herd), and
        ``provenance``.

    Raises:
        FileNotFoundError: If ``config/herding_groups.yaml`` is missing.

    Example:
        >>> cfg = load_herding_config()
        >>> cfg["default_group"]
        'baseline'
    """
    path = module_config_dir() / "herding_groups.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _is_carrier_missing(conglomerate_carrier: str | None) -> bool:
    return conglomerate_carrier is None or (
        isinstance(conglomerate_carrier, float) and pd.isna(conglomerate_carrier)
    )


def resolve_herding_group(
    conglomerate_carrier: str | None,
    config: dict[str, object] | None = None,
) -> HerdingGroupResolution:
    """Resolve a carrier string to its explicit herding group.

    Lookup is a case-folded, whitespace-stripped EXACT match against
    ``config/herding_groups.yaml``'s ``groups`` table — never a substring
    match, alias guess, or case-fold coincidence. A carrier absent from the
    table resolves to ``default_group`` and logs a structured warning naming
    the unmapped carrier (the never-silent contract IMP-C04 requires). A
    null/missing carrier also resolves to ``default_group`` but is not treated
    as an unmapped-identity failure (no warning) — it is the expected state
    for polls without conglomerate metadata.

    Args:
        conglomerate_carrier: Raw carrier/media-holding string from the poll
            row, or ``None``/``NaN`` when not recorded.
        config: Pre-loaded ``herding_groups.yaml`` document. Loaded via
            :func:`load_herding_config` when omitted (callers resolving many
            rows should load once and pass it in).

    Returns:
        The resolved :class:`HerdingGroupResolution`.

    Raises:
        KeyError: If ``config`` is missing the required ``default_group`` or
            ``groups`` keys.

    Example:
        >>> resolve_herding_group("Vierci").group
        'elevated'
    """
    cfg = config if config is not None else load_herding_config()
    default_group = str(cfg["default_group"])
    groups = cfg["groups"]
    if not isinstance(groups, dict):
        raise KeyError("herding_groups.yaml 'groups' must be a mapping")

    if _is_carrier_missing(conglomerate_carrier):
        return HerdingGroupResolution(group=default_group, matched=True, carrier_normalized=None)

    normalized = str(conglomerate_carrier).strip().lower()
    if normalized in groups:
        return HerdingGroupResolution(
            group=str(groups[normalized]), matched=True, carrier_normalized=normalized
        )
    logger.warning(
        "herding_weights: unmapped conglomerate_carrier %r (normalized=%r) — "
        "defaulting to group %r. No substring matching is performed; add an "
        "explicit entry to config/herding_groups.yaml if this carrier is real.",
        conglomerate_carrier,
        normalized,
        default_group,
    )
    return HerdingGroupResolution(group=default_group, matched=False, carrier_normalized=normalized)


def _date_window(publication_date: date) -> str:
    if _MARCH_WINDOW_START <= publication_date <= _MARCH_WINDOW_END:
        return "march_window"
    if _APRIL_WINDOW_START <= publication_date <= _APRIL_WINDOW_END:
        return "april_window"
    return "outside_window"


def rho_herd_for_row(
    publication_date: date,
    conglomerate_carrier: str | None,
    config: dict[str, object] | None = None,
) -> float:
    """Herd correlation proxy ``rho_herd`` in [0, 1] for one poll row.

    Looks up the (date-window, herding-group) cell of
    ``config/herding_groups.yaml``'s ``covariance_matrix``. The herding group
    is resolved via :func:`resolve_herding_group` — an explicit config table
    lookup, never substring matching.

    Args:
        publication_date: The poll's publication date.
        conglomerate_carrier: Raw carrier/media-holding string, or
            ``None``/``NaN``.
        config: Pre-loaded ``herding_groups.yaml`` document. Loaded via
            :func:`load_herding_config` when omitted.

    Returns:
        The covariance-proxy value ``rho_herd`` for this row.

    Raises:
        KeyError: If the resolved date window or group is missing from the
            config's ``covariance_matrix``.

    Example:
        >>> from datetime import date
        >>> rho_herd_for_row(date(2018, 3, 20), "Vierci")
        0.55
    """
    cfg = config if config is not None else load_herding_config()
    resolution = resolve_herding_group(conglomerate_carrier, cfg)
    matrix = cfg["covariance_matrix"]
    if not isinstance(matrix, dict):
        raise KeyError("herding_groups.yaml 'covariance_matrix' must be a mapping")
    window = _date_window(publication_date)
    window_row = matrix[window]
    if resolution.group not in window_row:
        raise KeyError(
            f"herding_groups.yaml covariance_matrix[{window!r}] missing group "
            f"{resolution.group!r}"
        )
    return float(window_row[resolution.group])


def count_unmapped_carriers(
    carriers: pd.Series,
    config: dict[str, object] | None = None,
) -> dict[str, int]:
    """Tally carriers in a column that fall through to the default herding group.

    Used to build the "run summary counts unmapped carriers" disclosure
    IMP-C04 requires: a non-empty count means new/renamed carriers are
    silently landing on the default group and should be added to
    ``config/herding_groups.yaml``.

    Args:
        carriers: A pandas Series of raw carrier strings (may contain
            ``None``/``NaN``).
        config: Pre-loaded ``herding_groups.yaml`` document. Loaded via
            :func:`load_herding_config` when omitted.

    Returns:
        Mapping of normalized carrier string -> row count, for every carrier
        that was non-null but absent from the mapping table. Empty when every
        non-null carrier resolved via an explicit table entry.

    Raises:
        KeyError: If ``config`` is missing required keys (propagated from
            :func:`resolve_herding_group`).

    Example:
        >>> import pandas as pd
        >>> count_unmapped_carriers(pd.Series(["Vierci", "New Outlet"]))
        {'new outlet': 1}
    """
    cfg = config if config is not None else load_herding_config()
    counts: dict[str, int] = {}
    for carrier in carriers:
        resolution = resolve_herding_group(carrier, cfg)
        if not resolution.matched and resolution.carrier_normalized is not None:
            key = resolution.carrier_normalized
            counts[key] = counts.get(key, 0) + 1
    return counts
