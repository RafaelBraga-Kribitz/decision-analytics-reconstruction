"""Shock score s from poll margin, transparency, and herd proxy."""

from __future__ import annotations

from datetime import date

import yaml

from module_c_forecasting_scenarios.features.herding_weights import rho_herd_for_row
from module_c_forecasting_scenarios.paths import module_config_dir

# shock_params.yaml schema (IMP-C04 acceptance criterion 4): types, bounds, and
# the closed set of recognized top-level keys. Loading aborts (ValueError) on
# an out-of-bounds value or an unrecognized key so a typo or a slipped-in
# constant can never silently bypass the provenance ledger.
_KNOWN_SHOCK_PARAM_KEYS: frozenset[str] = frozenset(
    {
        "lambda1",
        "lambda2",
        "lambda3",
        "m_star_extreme_pp",
        "phi_opaque_threshold",
        "rho_herd_threshold",
        "outcome_event_date",
        "clip_days_before_outcome",
        "shock_multiplier",
        "baseline_shock_zero",
        "bucket_priors",
        "provenance",
    }
)

# (key, lower_bound_exclusive, upper_bound_inclusive) for every bounded scalar.
_BOUNDED_SCALAR_KEYS: tuple[tuple[str, float, float], ...] = (
    ("lambda1", 0.0, 1.0),
    ("lambda2", 0.0, 1.0),
    ("lambda3", 0.0, 1.0),
    ("m_star_extreme_pp", 0.0, 30.0),
    ("phi_opaque_threshold", 0.0, 1.0),
    ("rho_herd_threshold", 0.0, 1.0),
)


def validate_shock_params(params: dict[str, object]) -> None:
    """Validate a loaded ``shock_params.yaml`` document against its schema.

    Enforces the closed set of recognized top-level keys and the bounds
    ``lambda1``/``lambda2``/``lambda3``/``phi_opaque_threshold``/
    ``rho_herd_threshold`` in (0, 1] and ``m_star_extreme_pp`` in (0, 30].

    Args:
        params: The parsed ``shock_params.yaml`` document.

    Returns:
        None. Raises on the first violation found.

    Raises:
        ValueError: If ``params`` declares an unrecognized top-level key, or
            any bounded scalar is missing, non-numeric, or outside its
            documented bound.

    Example:
        >>> validate_shock_params({"lambda1": 0.08, "lambda2": 0.35, "lambda3": 0.12,
        ...     "m_star_extreme_pp": 12.0, "phi_opaque_threshold": 0.35,
        ...     "rho_herd_threshold": 0.4})
    """
    unknown = set(params.keys()) - _KNOWN_SHOCK_PARAM_KEYS
    if unknown:
        raise ValueError(
            f"shock_params.yaml has unknown key(s) {sorted(unknown)}; "
            f"known keys are {sorted(_KNOWN_SHOCK_PARAM_KEYS)}"
        )
    for key, lo, hi in _BOUNDED_SCALAR_KEYS:
        if key not in params:
            raise ValueError(f"shock_params.yaml missing required key {key!r}")
        value = params[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"shock_params.yaml[{key!r}] must be numeric, got {value!r}")
        fvalue = float(value)  # type: ignore[arg-type]  # narrowed to int|float above
        if not (lo < fvalue <= hi):
            raise ValueError(f"shock_params.yaml[{key!r}]={fvalue} out of bounds ({lo}, {hi}]")


def load_shock_params() -> dict[str, object]:
    """Load and schema-validate ``config/shock_params.yaml``.

    Returns:
        The parsed and validated YAML document.

    Raises:
        FileNotFoundError: If ``config/shock_params.yaml`` is missing.
        ValueError: If the document fails :func:`validate_shock_params`.

    Example:
        >>> params = load_shock_params()
        >>> 0 < params["lambda1"] <= 1
        True
    """
    path = module_config_dir() / "shock_params.yaml"
    with open(path) as f:
        params = yaml.safe_load(f)
    validate_shock_params(params)
    return params


def shock_score_s(
    m_poll_pp: float,
    m_star_pp: float,
    phi: float,
    publication_date: date,
    conglomerate_carrier: str | None,
    params: dict[str, object] | None = None,
) -> float:
    """Continuous demobilisation shock score for one poll row.

    ``s = lambda1 * |m_poll - m_star| + lambda2 * (1 - phi) + lambda3 * rho_herd``,
    linearly clipped to zero as ``publication_date`` moves more than
    ``clip_days_before_outcome`` days before ``outcome_event_date``.

    Args:
        m_poll_pp: Poll margin, percentage points.
        m_star_pp: Calibration-anchor (verified outcome) margin, percentage
            points.
        phi: Transparency index in (0, 1].
        publication_date: The poll's publication date.
        conglomerate_carrier: Raw carrier/media-holding string, or ``None``.
        params: Explicit shock-parameter overrides (bypasses schema
            validation — used by tests to probe individual thresholds).
            Loaded via :func:`load_shock_params` when omitted.

    Returns:
        The shock score ``s`` (unitless, >= 0).

    Raises:
        ValueError: Propagated from :func:`load_shock_params` when ``params``
            is omitted and the on-disk config fails schema validation.

    Example:
        >>> from datetime import date
        >>> shock_score_s(15.0, 3.7, 0.9, date(2018, 1, 1), None) >= 0
        True
    """
    p = params or load_shock_params()
    lam1 = float(p.get("lambda1", 0.08))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    lam2 = float(p.get("lambda2", 0.35))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    lam3 = float(p.get("lambda3", 0.12))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    clip_days = int(p.get("clip_days_before_outcome", 45))  # type: ignore[arg-type]  # dict[str, object] value; runtime is int
    outcome = date.fromisoformat(str(p.get("outcome_event_date", "2018-04-22")))
    if (outcome - publication_date).days > clip_days:
        scale = 1.0
    else:
        scale = max(0.0, (outcome - publication_date).days / max(clip_days, 1))
    rho = rho_herd_for_row(publication_date, conglomerate_carrier)
    s = lam1 * abs(m_poll_pp - m_star_pp) + lam2 * (1.0 - phi) + lam3 * rho
    return float(s * scale)


def scenario_bucket_for_margin(
    m_poll_pp: float,
    m_star_pp: float,
    phi: float,
    rho: float,
    params: dict[str, object] | None = None,
) -> str:
    """Classify a poll row into one of the three canonical scenario buckets.

    A poll is "extreme" when ``|m_poll - m_star| >= m_star_extreme_pp``,
    "opaque" when ``phi < phi_opaque_threshold``, and its herd-covariance
    proxy is "elevated" when ``rho > rho_herd_threshold``. All three
    thresholds are config-driven (``shock_params.yaml``), not hardcoded.

    Args:
        m_poll_pp: Poll margin, percentage points.
        m_star_pp: Calibration-anchor margin, percentage points.
        phi: Transparency index in (0, 1].
        rho: Herd-covariance proxy in [0, 1] (see
            ``features.herding_weights.rho_herd_for_row``).
        params: Explicit shock-parameter overrides (bypasses schema
            validation — used by tests to probe individual thresholds).
            Loaded via :func:`load_shock_params` when omitted.

    Returns:
        One of ``"baseline"``, ``"extreme_tracker"``, ``"compounded_herd"``.

    Raises:
        ValueError: Propagated from :func:`load_shock_params` when ``params``
            is omitted and the on-disk config fails schema validation.

    Example:
        >>> scenario_bucket_for_margin(3.7, 3.7, phi=0.9, rho=0.0)
        'baseline'
    """
    p = params or load_shock_params()
    extreme_pp = float(p.get("m_star_extreme_pp", 12.0))  # type: ignore[arg-type]  # dict[str, object] value; runtime is float
    phi_opaque_threshold = float(p.get("phi_opaque_threshold", 0.35))  # type: ignore[arg-type]
    rho_herd_threshold = float(p.get("rho_herd_threshold", 0.4))  # type: ignore[arg-type]
    extreme = abs(m_poll_pp - m_star_pp) >= extreme_pp
    opaque = phi < phi_opaque_threshold
    if extreme and opaque and rho > rho_herd_threshold:
        return "compounded_herd"
    if extreme:
        return "extreme_tracker"
    return "baseline"
