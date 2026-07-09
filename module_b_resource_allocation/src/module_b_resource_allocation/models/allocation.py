"""LP/MILP allocation model for Module B (PuLP + CBC).

Decision variables
------------------

* ``x[d, c, w]`` — non-negative spend in USD allocated to (department d,
  channel c, ISO week w).
* ``y[d, c, w]`` — binary indicator that channel c is ACTIVE in
  (d, w) (used for bundle cardinality constraints).

Objective
---------

Maximize total persuasion-adjusted expected contacts subject to:

* ``sum(x) == B`` (total USD envelope, with a small ± tolerance).
* For every (d, c, w):
  ``x[d, c, w] / unit_cost_usd[d, c, w] <= reachable_audience[d, c]``.
* Per-department coverage floor: expected contacts in each department
  ≥ ``COVERAGE_LOWER_BOUND_PCT`` × the department's population proxy
  (largest single-channel reachable audience).
* Bundle constraints (conglomerate ratios + cardinality) for every active week.
* Channel cardinality: at most one bundle membership per (d, w) row, with
  bundle equality/inequality rules per ``channel_bundles.yaml``.
* Tier-eligibility hard locks: ``negligible`` departments may not host
  in-person channels above a 5% population-share spend ceiling.

The model uses piecewise-linear diminishing returns: each (department,
channel, week) cell's spend is split across K-1 chord segments of the exact
``_expected_contacts`` response curve (K=6 reach breakpoints — 0, the
inflection, and an even split of the saturating tail). The curve is concave
for all configured parameters, so segments fill in order without extra
binaries, and the optimizer's objective is the chord interpolant of the SAME
curve the post-solve report evaluates (identity gated in tests).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pulp
import yaml

from module_b_resource_allocation.bundle_definitions import BUNDLE_MIN_USD, CHANNEL_TO_BUNDLE
from module_b_resource_allocation.constants import (
    CAMPAIGN_BUDGET_TOLERANCE,
    CAMPAIGN_BUDGET_USD,
    CHANNEL_NAMES,
    CHANNEL_TYPES,
    COVERAGE_LOWER_BOUND_PCT,
    DEPARTMENTS,
    SCENARIO_BASELINE,
    VALID_SCENARIOS,
    WEEK_INDEX,
    WEEK_LABELS,
)
from module_b_resource_allocation.data.fx import FxLayer, load_fx_layer
from module_b_resource_allocation.models.feature_join import build_allocation_features

_PAY_TV_ELIGIBLE: frozenset[str] = frozenset({"Asuncion", "Central", "Alto Parana"})


class EmptyReachCapsError(ValueError):
    """Raised when :func:`solve` is given an ``AllocationProblem`` whose
    ``reach_caps`` frame has no rows.

    Without at least one (department, channel) row the solver cannot build
    any decision variables, and every ``DEPARTMENTS`` × ``CHANNEL_NAMES``
    cell lookup against the empty frame would otherwise raise an opaque
    ``KeyError`` deep inside :func:`_build_decision_variables`.
    """


def _expected_contacts(
    reachable_audience: float, reach_used: float, k: float, inflection_pct: float
) -> float:
    """Piecewise log-linear diminishing-returns response.

    Linear below the inflection; saturating ``1 - exp(-k * Δ)`` above it.
    """
    if reachable_audience <= 0 or reach_used <= 0:
        return 0.0
    reach_used = min(reach_used, 1.0)
    if reach_used <= inflection_pct:
        return float(reachable_audience) * reach_used
    linear_part = float(reachable_audience) * inflection_pct
    residual = float(reachable_audience) * (1.0 - inflection_pct)
    saturation = 1.0 - math.exp(-k * (reach_used - inflection_pct))
    return linear_part + residual * saturation


_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

#: Number of piecewise-linear breakpoints on the reach axis (K=6 → 5 segments).
_K_REACH_BREAKPOINTS = 6


def _reach_breakpoints(inflection_pct: float, k: int = _K_REACH_BREAKPOINTS) -> list[float]:
    """K breakpoints on the reach axis, exact at 0 and the inflection.

    The first segment covers the linear region [0, inflection]; the remaining
    segments split the saturating tail evenly up to full reach (r = 1).
    """
    infl = min(max(float(inflection_pct), 0.0), 1.0)
    n_above = k - 2
    pts = [0.0, infl] + [infl + (1.0 - infl) * j / n_above for j in range(1, n_above + 1)]
    return sorted({round(p, 6) for p in pts})


def _pl_segments(
    audience: float, uc_usd: float, k_dim: float, inflection: float
) -> list[tuple[float, float]]:
    """Piecewise-linear segments of the response curve in USD space.

    Returns ``[(width_usd, contacts_per_usd), ...]`` chords of
    :func:`_expected_contacts` between reach breakpoints. The curve is concave
    for all configured (k, inflection), so slopes are non-increasing and an
    LP maximization fills segments in order — the objective equals the chord
    interpolant of the same curve the post-solve report evaluates.
    """
    bps = _reach_breakpoints(inflection)
    segments: list[tuple[float, float]] = []
    prev_slope = float("inf")
    for r_lo, r_hi in zip(bps[:-1], bps[1:], strict=True):
        width_usd = (r_hi - r_lo) * audience * uc_usd
        if width_usd <= 0:
            continue
        f_lo = _expected_contacts(audience, r_lo, k_dim, inflection)
        f_hi = _expected_contacts(audience, r_hi, k_dim, inflection)
        slope = (f_hi - f_lo) / width_usd
        # Guard concavity against floating-point noise so greedy filling holds.
        slope = min(slope, prev_slope)
        prev_slope = slope
        segments.append((width_usd, max(slope, 0.0)))
    return segments


@dataclass(frozen=True)
class AllocationProblem:
    budget_usd: float
    budget_tolerance: float
    fx_layer: FxLayer
    reach_caps: pd.DataFrame
    bundles: dict[str, dict[str, Any]]
    scenario_id: str
    solver_seed: int
    bundle_constraints: bool = True
    """If True (default), enforce bundle ratios, ge_2_of_3 cardinality, AND
    global per-bundle minimum-spend floors via bundle-level binary linking
    variables. If False, skip every bundle constraint (LP-relaxation style)."""


@dataclass
class AllocationResult:
    allocation: pd.DataFrame
    binding_constraints: list[str]
    solver_status: str
    solver_seed: int
    scenario_id: str
    fx_series_id: str
    #: CBC shadow prices / status after ``solve`` (keys depend on constraint names).
    lp_diagnostics: dict[str, Any] | None = None

    @property
    def total_budget_usd(self) -> float:
        """Aggregate allocated USD across the MILP decision table.

        Args:
            None.

        Returns:
            Sum of ``budget_allocation_usd`` in ``allocation``.

        Raises:
            KeyError: If ``budget_allocation_usd`` is missing from ``allocation``.

        Example:
            ``result.total_budget_usd`` when comparing scenarios in reports.
        """
        return float(self.allocation["budget_allocation_usd"].sum())

    @property
    def total_persuasion_adjusted_contacts(self) -> float:
        """Aggregate persuasion-adjusted contacts implied by the allocation.

        Args:
            None.

        Returns:
            Sum of ``persuasion_adjusted_contacts`` in ``allocation``.

        Raises:
            KeyError: If ``persuasion_adjusted_contacts`` is missing.

        Example:
            ``result.total_persuasion_adjusted_contacts`` in baseline dashboards.
        """
        return float(self.allocation["persuasion_adjusted_contacts"].sum())


def _load_bundles() -> dict[str, dict[str, Any]]:
    with open(_CONFIG_DIR / "channel_bundles.yaml") as f:
        return yaml.safe_load(f)["bundles"]


def build_problem(
    *,
    scenario_id: str = SCENARIO_BASELINE,
    fx_series_id: str = "series_b_weekly",
    reach_caps: pd.DataFrame | None = None,
    budget_usd: float = CAMPAIGN_BUDGET_USD,
    budget_tolerance: float = CAMPAIGN_BUDGET_TOLERANCE,
    solver_seed: int = 20180422,
    bundle_constraints: bool = True,
) -> AllocationProblem:
    """Assemble frozen inputs for the Module B MILP without global side effects.

    Args:
        scenario_id: Scenario label validated against ``VALID_SCENARIOS``.
        fx_series_id: FX calibration series passed to :func:`load_fx_layer`.
        reach_caps: Optional pre-built reach caps; defaults to
            :func:`build_allocation_features`.
        budget_usd: Total spend envelope before tolerance bands.
        budget_tolerance: Fractional slack applied to ``budget_usd``.
        solver_seed: Deterministic CBC seed stored on the problem.

    Returns:
        :class:`AllocationProblem` ready for :func:`solve`.

    Raises:
        ValueError: If ``scenario_id`` is unknown.

    Example:
        ``build_problem(scenario_id=\"baseline\", solver_seed=20180422)`` mirrors the
        FastAPI ``GET /allocation/baseline`` path.
    """
    if scenario_id not in VALID_SCENARIOS:
        raise ValueError(f"Unknown scenario_id {scenario_id!r}")
    return AllocationProblem(
        budget_usd=float(budget_usd),
        budget_tolerance=float(budget_tolerance),
        fx_layer=load_fx_layer(fx_series_id),  # type: ignore[arg-type]  # fx_series_id is str; load_fx_layer expects SeriesId Literal; caller controls valid values
        reach_caps=reach_caps if reach_caps is not None else build_allocation_features(),
        bundles=_load_bundles(),
        scenario_id=scenario_id,
        solver_seed=int(solver_seed),
        bundle_constraints=bool(bundle_constraints),
    )


def _unit_cost_usd(row: pd.Series, layer: FxLayer, iso_week: str) -> float:
    tier = str(row["fx_tier_default"])
    return float(row["unit_cost_pyg"]) / layer.rate(iso_week, tier)  # type: ignore[arg-type]  # tier is str; layer.rate expects FxTier Literal; str(row[...]) ensures valid value


def _scenario_week_weight(scenario_id: str, week_idx: int) -> float:
    """Per-week emphasis multiplier (priors only; does not change budget envelope)."""
    if scenario_id == "early_lock":
        return 1.15 if week_idx <= 5 else 0.95
    if scenario_id == "late_flex":
        return 0.92 if week_idx <= 7 else 1.20
    return 1.0


def _tier_penalty(tier: str) -> float:
    return {"stronghold": 1.00, "swing": 1.10, "opposition": 0.85, "negligible": 0.55}[tier]


def _propensity_weight(cap_row: pd.Series) -> float:
    """Module A participation-propensity persuasion weight for a cap row.

    Defaults to 1.0 when the feature frame predates the A→B ingestion (no
    ``dept_mean_propensity`` column) or carries a null.
    """
    if "dept_mean_propensity" not in cap_row.index:
        return 1.0
    raw = cap_row["dept_mean_propensity"]
    value = float(raw) if bool(pd.notna(raw)) else 1.0
    return value if value > 0 else 1.0


@dataclass
class _DecisionVars:
    x: dict[tuple[str, str, int], pulp.LpVariable]
    y: dict[tuple[str, str, int], pulp.LpVariable]
    contact_terms: list[pulp.LpAffineExpression]
    coverage_terms: list[pulp.LpAffineExpression]


def _trunc_cents(v: float) -> float:
    # Truncate to cents so the cumulative output never breaches the LP envelope.
    return int(v * 100.0) / 100.0


def _constraint_pi(prob: pulp.LpProblem, name: str) -> float | None:
    cn = prob.constraints.get(name)
    if cn is None:
        return None
    raw = getattr(cn, "pi", None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _solver_status_label(status: int) -> str:
    if status == pulp.LpStatusOptimal:
        return "OPTIMAL"
    if status == pulp.LpStatusUndefined:
        return "UNDEFINED"
    if status == pulp.LpStatusUnbounded:
        return "UNBOUNDED"
    return "FEASIBLE"


def _add_channel_week_cell(
    prob: pulp.LpProblem,
    problem: AllocationProblem,
    layer: FxLayer,
    d: str,
    c: str,
    wi: int,
    w: str,
    cap_row: pd.Series,
    x: dict[tuple[str, str, int], pulp.LpVariable],
    y: dict[tuple[str, str, int], pulp.LpVariable],
    contact_terms: list[pulp.LpAffineExpression],
) -> pulp.LpAffineExpression | None:
    """Add decision variables and per-cell constraints for one (d, c, week)."""
    audience = float(cap_row["reachable_audience"])
    tier = str(cap_row["department_tier"])
    attention = float(cap_row["attention_multiplier"])
    salience = float(cap_row["salience_multiplier"])
    hostility = float(cap_row["network_hostility"])
    propensity_w = _propensity_weight(cap_row)
    inflection = float(cap_row["diminishing_returns_inflection_pct"])
    k_dim = float(cap_row["diminishing_returns_k"])

    uc_usd = _unit_cost_usd(cap_row, layer, w)
    if uc_usd <= 0:
        return None

    scenario_w = _scenario_week_weight(problem.scenario_id, wi)
    tier_w = _tier_penalty(tier)

    x_var = pulp.LpVariable(f"x_{d}_{c}_w{wi}", lowBound=0.0, cat="Continuous")
    y_var = pulp.LpVariable(f"y_{d}_{c}_w{wi}", cat="Binary")
    x[(d, c, wi)] = x_var
    y[(d, c, wi)] = y_var

    max_spend = audience * uc_usd
    prob += x_var <= max_spend * y_var, f"link_{d}_{c}_w{wi}"
    prob += x_var <= max_spend, f"cap_{d}_{c}_w{wi}"

    if c == "tv_spots" and d not in _PAY_TV_ELIGIBLE:
        prob += x_var == 0.0, f"paytv_block_{d}_w{wi}"

    segments = _pl_segments(audience, uc_usd, k_dim, inflection)
    seg_vars: list[pulp.LpVariable] = []
    cell_contacts_terms: list[pulp.LpAffineExpression] = []
    for j, (width_usd, slope) in enumerate(segments):
        s_var = pulp.LpVariable(
            f"xseg_{d}_{c}_w{wi}_s{j}",
            lowBound=0.0,
            upBound=width_usd,
            cat="Continuous",
        )
        seg_vars.append(s_var)
        cell_contacts_terms.append(slope * s_var)
    prob += x_var == pulp.lpSum(seg_vars), f"seg_total_{d}_{c}_w{wi}"

    cell_contacts = pulp.lpSum(cell_contacts_terms)
    persuasion_mult = attention * salience * hostility * scenario_w * tier_w * propensity_w
    contact_terms.append(persuasion_mult * cell_contacts)
    return cell_contacts


def _add_department_variables(
    prob: pulp.LpProblem,
    problem: AllocationProblem,
    layer: FxLayer,
    caps_lookup: pd.DataFrame,
    d: str,
    x: dict[tuple[str, str, int], pulp.LpVariable],
    y: dict[tuple[str, str, int], pulp.LpVariable],
    contact_terms: list[pulp.LpAffineExpression],
    coverage_terms: list[pulp.LpAffineExpression],
) -> None:
    dept_population_proxy = 0.0
    dept_contacts: list[pulp.LpAffineExpression] = []
    for c in CHANNEL_NAMES:
        cap_row = caps_lookup.loc[(d, c)]
        audience = float(cap_row["reachable_audience"])
        for wi, w in enumerate(WEEK_LABELS, start=1):
            cell_contacts = _add_channel_week_cell(
                prob, problem, layer, d, c, wi, w, cap_row, x, y, contact_terms
            )
            if cell_contacts is not None:
                dept_contacts.append(cell_contacts)
        dept_population_proxy = max(dept_population_proxy, audience)

    if dept_population_proxy > 0 and dept_contacts:
        prob += (
            pulp.lpSum(dept_contacts) >= COVERAGE_LOWER_BOUND_PCT * dept_population_proxy,
            f"coverage_{d}",
        )
        coverage_terms.append(pulp.lpSum(dept_contacts))


def _build_decision_variables(
    prob: pulp.LpProblem,
    problem: AllocationProblem,
    layer: FxLayer,
    caps_lookup: pd.DataFrame,
) -> _DecisionVars:
    x: dict[tuple[str, str, int], pulp.LpVariable] = {}
    y: dict[tuple[str, str, int], pulp.LpVariable] = {}
    contact_terms: list[pulp.LpAffineExpression] = []
    coverage_terms: list[pulp.LpAffineExpression] = []
    for d in DEPARTMENTS:
        _add_department_variables(
            prob, problem, layer, caps_lookup, d, x, y, contact_terms, coverage_terms
        )
    return _DecisionVars(x=x, y=y, contact_terms=contact_terms, coverage_terms=coverage_terms)


def _add_budget_envelope(
    prob: pulp.LpProblem,
    problem: AllocationProblem,
    x: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    total_spend = pulp.lpSum(x.values())
    prob += total_spend <= problem.budget_usd * (1.0 + problem.budget_tolerance), "budget_upper"
    prob += total_spend >= problem.budget_usd * (1.0 - problem.budget_tolerance), "budget_lower"


def _add_bundle_equality_constraints(
    prob: pulp.LpProblem,
    bundle_id: str,
    members: list[str],
    ratios: dict[str, Any],
    d: str,
    wi: int,
    x: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    base = members[0]
    if (d, base, wi) not in x:
        return
    base_x = x[(d, base, wi)]
    base_ratio = float(ratios[base])
    for c in members[1:]:
        if (d, c, wi) not in x:
            continue
        c_x = x[(d, c, wi)]
        c_ratio = float(ratios[c])
        if base_ratio > 0 and c_ratio > 0:
            prob += (
                c_x * base_ratio == base_x * c_ratio,
                f"bundle_eq_{bundle_id}_{d}_{c}_w{wi}",
            )


def _add_bundle_cardinality_constraints(
    prob: pulp.LpProblem,
    bundle_id: str,
    bundle: dict[str, Any],
    members: list[str],
    x: dict[tuple[str, str, int], pulp.LpVariable],
    y: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    cardinality = bundle.get("cardinality")
    ratios = bundle["members"]
    for d in DEPARTMENTS:
        for wi in WEEK_INDEX:
            if cardinality == "equality":
                _add_bundle_equality_constraints(prob, bundle_id, members, ratios, d, wi, x)
            elif cardinality == "ge_2_of_3":
                active_count = pulp.lpSum(y[(d, c, wi)] for c in members if (d, c, wi) in y)
                prob += active_count >= 2, f"bundle_card_{bundle_id}_{d}_w{wi}"


def _add_bundle_min_spend_floor(
    prob: pulp.LpProblem,
    bundle_id: str,
    members: list[str],
    x: dict[tuple[str, str, int], pulp.LpVariable],
    y: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    floor = float(BUNDLE_MIN_USD.get(bundle_id, 0.0))
    if floor <= 0:
        return
    z = pulp.LpVariable(f"z_{bundle_id}", cat="Binary")
    big_m = len(members) * len(DEPARTMENTS) * len(WEEK_INDEX)
    sum_y_bundle = pulp.lpSum(
        y[(d, c, wi)] for d in DEPARTMENTS for c in members for wi in WEEK_INDEX if (d, c, wi) in y
    )
    prob += sum_y_bundle <= big_m * z, f"bundle_link_{bundle_id}"
    bundle_total = pulp.lpSum(
        x[(d, c, wi)] for d in DEPARTMENTS for c in members for wi in WEEK_INDEX if (d, c, wi) in x
    )
    prob += bundle_total >= floor * z, f"bundle_min_spend_{bundle_id}"


def _add_bundle_constraints(
    prob: pulp.LpProblem,
    problem: AllocationProblem,
    x: dict[tuple[str, str, int], pulp.LpVariable],
    y: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    for bundle_id, bundle in problem.bundles.items():
        if bundle.get("binding", "hard") != "hard":
            continue
        members = list(bundle["members"].keys())
        _add_bundle_cardinality_constraints(prob, bundle_id, bundle, members, x, y)
        _add_bundle_min_spend_floor(prob, bundle_id, members, x, y)


def _add_negligible_tier_caps(
    prob: pulp.LpProblem,
    layer: FxLayer,
    caps_lookup: pd.DataFrame,
    x: dict[tuple[str, str, int], pulp.LpVariable],
) -> None:
    ground_channels = {
        c for c, t in CHANNEL_TYPES.items() if t in {"in_person", "broadcast_to_bilateral"}
    }
    for d in DEPARTMENTS:
        tier = str(caps_lookup.loc[(d, "tv_spots"), "department_tier"])
        if tier != "negligible":
            continue
        for c in ground_channels:
            for wi in WEEK_INDEX:
                if (d, c, wi) not in x:
                    continue
                cap_row = caps_lookup.loc[(d, c)]
                audience = float(cap_row["reachable_audience"])
                uc_usd = _unit_cost_usd(cap_row, layer, WEEK_LABELS[wi - 1])
                prob += (
                    x[(d, c, wi)] <= 0.05 * audience * uc_usd,
                    f"neg_tier_cap_{d}_{c}_w{wi}",
                )


def _run_allocation_solver(prob: pulp.LpProblem, solver_seed: int) -> int:
    solver = pulp.PULP_CBC_CMD(msg=False, options=[f"randomS {solver_seed}"])
    status = prob.solve(solver)
    if status in (pulp.LpStatusInfeasible, pulp.LpStatusNotSolved):
        raise RuntimeError(f"Module B allocation solve failed with status={pulp.LpStatus[status]}")
    return int(status)


def _collect_cap_dual_rows(prob: pulp.LpProblem) -> list[dict[str, Any]]:
    cap_dual_rows: list[dict[str, Any]] = []
    for cname, _ccon in prob.constraints.items():
        if not str(cname).startswith("cap_"):
            continue
        pi = _constraint_pi(prob, str(cname))
        if pi is not None:
            cap_dual_rows.append({"constraint": str(cname), "pi": float(pi)})
    cap_dual_rows.sort(key=lambda r: abs(r["pi"]), reverse=True)
    return cap_dual_rows


def _build_lp_diagnostics(prob: pulp.LpProblem, status: int) -> dict[str, Any]:
    try:
        status_label = str(pulp.LpStatus[status])
    except Exception:
        status_label = f"code_{int(status)}"
    objective_value = pulp.value(prob.objective)
    return {
        "budget_upper_pi": _constraint_pi(prob, "budget_upper"),
        "budget_lower_pi": _constraint_pi(prob, "budget_lower"),
        "pulp_status_code": int(status),
        "pulp_status_label": status_label,
        "reach_cap_duals_top5": _collect_cap_dual_rows(prob)[:5],
        "objective_value": (
            float(cast(Any, objective_value)) if objective_value is not None else None
        ),
    }


def _collect_global_binding_constraints(prob: pulp.LpProblem) -> list[str]:
    global_prefixes = ("budget_", "coverage_", "bundle_min_spend_")
    binding: list[str] = []
    for cname, con in prob.constraints.items():
        if not str(cname).startswith(global_prefixes):
            continue
        slack = getattr(con, "slack", None)
        try:
            slack_f = float(slack) if slack is not None else None
        except (TypeError, ValueError):
            slack_f = None
        if slack_f is not None and abs(slack_f) <= 1e-4:
            binding.append(str(cname))
    binding.sort()
    return binding


def _row_binding_for_cell(
    d: str,
    c: str,
    dept_tier: str,
    val_usd: float,
    reach_used: float,
    audience: float,
    uc_usd: float,
) -> str | None:
    if c == "tv_spots" and d not in _PAY_TV_ELIGIBLE:
        return "paytv_block"
    if reach_used >= 0.999:
        return "reach_cap"
    if (
        dept_tier == "negligible"
        and CHANNEL_TYPES[c] in {"in_person", "broadcast_to_bilateral"}
        and uc_usd > 0
        and val_usd >= 0.05 * audience * uc_usd - 0.01
        and val_usd > 0
    ):
        return "neg_tier_cap"
    return None


def _build_allocation_row(
    d: str,
    c: str,
    wi: int,
    val_usd: float,
    problem: AllocationProblem,
    layer: FxLayer,
    cap_row: pd.Series,
    row_solver_status: str,
) -> dict[str, Any]:
    w = WEEK_LABELS[wi - 1]
    uc_usd = _unit_cost_usd(cap_row, layer, w)
    audience = float(cap_row["reachable_audience"])
    units = val_usd / uc_usd if uc_usd > 0 else 0.0
    reach_used = units / audience if audience > 0 else 0.0
    contacts = _expected_contacts(
        audience,
        min(reach_used, 1.0),
        float(cap_row["diminishing_returns_k"]),
        float(cap_row["diminishing_returns_inflection_pct"]),
    )
    attention = float(cap_row["attention_multiplier"])
    salience = float(cap_row["salience_multiplier"])
    hostility = float(cap_row["network_hostility"])
    propensity_w = _propensity_weight(cap_row)
    scenario_w = _scenario_week_weight(problem.scenario_id, wi)
    dept_tier = str(cap_row["department_tier"])
    tier_w = _tier_penalty(dept_tier)
    persuasion = contacts * attention * salience * hostility * scenario_w * tier_w * propensity_w
    tier_default = str(cap_row["fx_tier_default"])
    bundle_id = CHANNEL_TO_BUNDLE.get(c)
    row_binding = _row_binding_for_cell(d, c, dept_tier, val_usd, reach_used, audience, uc_usd)
    return {
        "department": d,
        "channel": c,
        "channel_type": CHANNEL_TYPES[c],
        "week_index": int(wi),
        "iso_week": w,
        "department_tier": dept_tier,
        "region": str(cap_row["region"]),
        "budget_allocation_usd": val_usd,
        "budget_allocation_pyg": round(val_usd * layer.rate(w, tier_default), 2),  # type: ignore[arg-type]
        "fx_tier": tier_default,
        "tc_rate_pyg_per_usd": layer.rate(w, tier_default),  # type: ignore[arg-type]
        "expected_contacts": round(contacts, 4),
        "persuasion_adjusted_contacts": round(persuasion, 4),
        "reach_cap_population_proxy": audience,
        "reach_utilization": round(min(reach_used, 1.5), 4),
        "binding_constraint": row_binding,
        "bundle_id": bundle_id,
        "scenario_id": problem.scenario_id,
        "solver_status": row_solver_status,
        "solver_seed": problem.solver_seed,
        "schema_version_used": "1.0.0",
    }


def _build_allocation_rows(
    problem: AllocationProblem,
    layer: FxLayer,
    caps_lookup: pd.DataFrame,
    x: dict[tuple[str, str, int], pulp.LpVariable],
    row_solver_status: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (d, c, wi), x_var in x.items():
        raw_v = pulp.value(cast(Any, x_var))
        val_usd = float(raw_v) if raw_v is not None else 0.0
        val_usd = _trunc_cents(val_usd)
        cap_row = caps_lookup.loc[(d, c)]
        rows.append(
            _build_allocation_row(d, c, wi, val_usd, problem, layer, cap_row, row_solver_status)
        )
    return rows


def solve(problem: AllocationProblem) -> AllocationResult:
    """Construct the PuLP model for ``problem`` and return the solved allocation.

    Args:
        problem: Immutable problem bundle from :func:`build_problem`.

    Returns:
        :class:`AllocationResult` with ``allocation`` plus solver diagnostics.

    Raises:
        RuntimeError: If CBC reports an infeasible or error status (via PuLP).
        EmptyReachCapsError: If ``problem.reach_caps`` has zero rows.

    Example:
        ``solve(build_problem(scenario_id=\"baseline\"))`` is the core API call
        for both CLI and HTTP surfaces.
    """
    if problem.reach_caps.empty:
        raise EmptyReachCapsError(
            "AllocationProblem.reach_caps has zero rows; the solver needs at "
            "least one (department, channel) cell to build decision variables."
        )
    layer = problem.fx_layer
    caps_lookup = problem.reach_caps.set_index(["department", "channel"], drop=False)

    prob = pulp.LpProblem(f"module_b_allocation_{problem.scenario_id}", pulp.LpMaximize)
    dv = _build_decision_variables(prob, problem, layer, caps_lookup)

    prob += pulp.lpSum(dv.contact_terms), "total_persuasion_adjusted_contacts"
    _add_budget_envelope(prob, problem, dv.x)

    if problem.bundle_constraints:
        _add_bundle_constraints(prob, problem, dv.x, dv.y)

    _add_negligible_tier_caps(prob, layer, caps_lookup, dv.x)

    status = _run_allocation_solver(prob, problem.solver_seed)
    row_solver_status = _solver_status_label(status)
    lp_diagnostics = _build_lp_diagnostics(prob, status)
    binding = _collect_global_binding_constraints(prob)
    rows = _build_allocation_rows(problem, layer, caps_lookup, dv.x, row_solver_status)

    allocation = (
        pd.DataFrame(rows)
        .sort_values(["scenario_id", "department", "channel", "week_index"])
        .reset_index(drop=True)
    )

    return AllocationResult(
        allocation=allocation,
        binding_constraints=binding,
        solver_status=row_solver_status,
        solver_seed=problem.solver_seed,
        scenario_id=problem.scenario_id,
        fx_series_id=layer.series_id,
        lp_diagnostics=lp_diagnostics,
    )
