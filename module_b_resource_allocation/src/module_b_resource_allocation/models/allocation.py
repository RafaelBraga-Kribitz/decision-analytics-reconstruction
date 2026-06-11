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

The model uses piecewise-linear diminishing returns by linearizing each
channel's response curve at a single inflection point — this keeps the model
LP-friendly while preserving the reach-saturation shape Module B's spec
requires.
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


def solve(problem: AllocationProblem) -> AllocationResult:
    """Construct the PuLP model for ``problem`` and return the solved allocation.

    Args:
        problem: Immutable problem bundle from :func:`build_problem`.

    Returns:
        :class:`AllocationResult` with ``allocation`` plus solver diagnostics.

    Raises:
        RuntimeError: If CBC reports an infeasible or error status (via PuLP).

    Example:
        ``solve(build_problem(scenario_id=\"baseline\"))`` is the core API call
        for both CLI and HTTP surfaces.
    """
    layer = problem.fx_layer
    caps_lookup = problem.reach_caps.set_index(["department", "channel"], drop=False)

    prob = pulp.LpProblem(f"module_b_allocation_{problem.scenario_id}", pulp.LpMaximize)

    x: dict[tuple[str, str, int], pulp.LpVariable] = {}
    y: dict[tuple[str, str, int], pulp.LpVariable] = {}
    contact_terms: list[pulp.LpAffineExpression] = []
    coverage_terms: list[pulp.LpAffineExpression] = []

    for d in DEPARTMENTS:
        # Population proxy: the largest single-channel reachable audience in the
        # department. Channel audiences overlap the same population, so summing
        # them (let alone multiplying by weeks) would inflate the coverage
        # denominator by an order of magnitude.
        dept_population_proxy = 0.0
        dept_contacts: list[pulp.LpAffineExpression] = []
        for c in CHANNEL_NAMES:
            cap_row = caps_lookup.loc[(d, c)]
            audience = float(cap_row["reachable_audience"])
            tier = str(cap_row["department_tier"])
            attention = float(cap_row["attention_multiplier"])
            salience = float(cap_row["salience_multiplier"])
            hostility = float(cap_row["network_hostility"])
            inflection = float(cap_row["diminishing_returns_inflection_pct"])
            k_dim = float(cap_row["diminishing_returns_k"])

            # Two linear segments approximating the diminishing-returns curve.
            # Below inflection: 1.0 contact per unit cap; above: avg saturation
            # ≈ (1 - exp(-k * 0.5)) / 0.5 over the residual.
            avg_residual = (1.0 - math.exp(-k_dim * 0.5)) / 0.5  # in (0, 1]
            avg_residual = max(min(avg_residual, 1.0), 0.0)

            for wi, w in enumerate(WEEK_LABELS, start=1):
                uc_usd = _unit_cost_usd(cap_row, layer, w)
                if uc_usd <= 0:
                    continue
                scenario_w = _scenario_week_weight(problem.scenario_id, wi)
                tier_w = _tier_penalty(tier)

                x_var = pulp.LpVariable(f"x_{d}_{c}_w{wi}", lowBound=0.0, cat="Continuous")
                y_var = pulp.LpVariable(f"y_{d}_{c}_w{wi}", cat="Binary")
                x[(d, c, wi)] = x_var
                y[(d, c, wi)] = y_var

                # Spend cap when the channel-week is inactive (binary linkage).
                max_spend = audience * uc_usd
                prob += x_var <= max_spend * y_var, f"link_{d}_{c}_w{wi}"

                # Per-week, per-channel hard ceiling at audience * unit cost.
                prob += x_var <= max_spend, f"cap_{d}_{c}_w{wi}"

                # Pay-TV spots only in eligible departments (schema / plan §7.2).
                if c == "tv_spots" and d not in _PAY_TV_ELIGIBLE:
                    prob += x_var == 0.0, f"paytv_block_{d}_w{wi}"

                # Contact contribution: piecewise-linear approximation (single
                # blended slope below/above the inflection share).
                contacts_per_unit_below = 1.0 / uc_usd
                contacts_per_unit_above = avg_residual / uc_usd
                # Use the convex combination weighted by inflection point.
                contacts_per_unit_eff = (
                    inflection * contacts_per_unit_below
                    + (1.0 - inflection) * contacts_per_unit_above
                )
                persuasion_per_unit = (
                    contacts_per_unit_eff * attention * salience * hostility * scenario_w * tier_w
                )
                term = persuasion_per_unit * x_var
                contact_terms.append(term)
                dept_contacts.append(contacts_per_unit_eff * x_var)
            dept_population_proxy = max(dept_population_proxy, audience)

        # Coverage floor: each department must receive expected contacts of at
        # least COVERAGE_LOWER_BOUND_PCT of its population proxy across the
        # 14-week window (contacts may repeat-touch the same person, so the
        # floor is feasible even in low-budget runs).
        if dept_population_proxy > 0 and dept_contacts:
            prob += (
                pulp.lpSum(dept_contacts)
                >= COVERAGE_LOWER_BOUND_PCT * dept_population_proxy,
                f"coverage_{d}",
            )
            coverage_terms.append(pulp.lpSum(dept_contacts))

    # Objective.
    prob += pulp.lpSum(contact_terms), "total_persuasion_adjusted_contacts"

    # Total budget envelope (± tolerance).
    total_spend = pulp.lpSum(x.values())
    prob += total_spend <= problem.budget_usd * (1.0 + problem.budget_tolerance), "budget_upper"
    prob += total_spend >= problem.budget_usd * (1.0 - problem.budget_tolerance), "budget_lower"

    # Channel-bundle constraints (cardinality + ratio + global minimum-spend
    # floor gated on a bundle-level binary z[bundle_id]). Skipped entirely when
    # ``problem.bundle_constraints`` is False (LP-relaxation comparator).
    z_bundle: dict[str, pulp.LpVariable] = {}
    if problem.bundle_constraints:
        for bundle_id, bundle in problem.bundles.items():
            members = list(bundle["members"].keys())
            ratios = bundle["members"]
            cardinality = bundle.get("cardinality")
            bundle_binding: str = bundle.get("binding", "hard")
            if bundle_binding != "hard":
                continue
            for d in DEPARTMENTS:
                for wi in WEEK_INDEX:
                    active_count = pulp.lpSum(y[(d, c, wi)] for c in members if (d, c, wi) in y)
                    if cardinality == "equality":
                        base = members[0]
                        if (d, base, wi) not in x:
                            continue
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
                    elif cardinality == "ge_2_of_3":
                        prob += (
                            active_count >= 2,
                            f"bundle_card_{bundle_id}_{d}_w{wi}",
                        )

            # Bundle-level activation binary z ∈ {0,1} with two linking edges:
            # - sum_y_bundle <= big_M * z  → z = 0 forces every member inactive
            # - bundle_total >= floor * z  → z = 1 enforces global minimum spend
            # The ge_2_of_3 / equality constraints above already force at least
            # one member active per (d, w), so z = 0 is infeasible in practice
            # and the floor binds. The binary is real — relaxing it (LP) would
            # let z take a fractional value and weaken the floor.
            floor = float(BUNDLE_MIN_USD.get(bundle_id, 0.0))
            if floor <= 0:
                continue
            z = pulp.LpVariable(f"z_{bundle_id}", cat="Binary")
            z_bundle[bundle_id] = z
            big_m = len(members) * len(DEPARTMENTS) * len(WEEK_INDEX)
            sum_y_bundle = pulp.lpSum(
                y[(d, c, wi)]
                for d in DEPARTMENTS
                for c in members
                for wi in WEEK_INDEX
                if (d, c, wi) in y
            )
            prob += sum_y_bundle <= big_m * z, f"bundle_link_{bundle_id}"
            bundle_total = pulp.lpSum(
                x[(d, c, wi)]
                for d in DEPARTMENTS
                for c in members
                for wi in WEEK_INDEX
                if (d, c, wi) in x
            )
            prob += bundle_total >= floor * z, f"bundle_min_spend_{bundle_id}"

    # In-person channels in 'negligible' tier capped at 5% of dept audience.
    in_person = {c for c, t in CHANNEL_TYPES.items() if t == "in_person"}
    for d in DEPARTMENTS:
        tier = str(caps_lookup.loc[(d, "tv_spots"), "department_tier"])
        if tier != "negligible":
            continue
        for c in in_person:
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

    solver = pulp.PULP_CBC_CMD(msg=False, options=[f"randomS {problem.solver_seed}"])
    status = prob.solve(solver)
    if status in (pulp.LpStatusInfeasible, pulp.LpStatusNotSolved):
        raise RuntimeError(f"Module B allocation solve failed with status={pulp.LpStatus[status]}")
    if status == pulp.LpStatusOptimal:
        row_solver_status = "OPTIMAL"
    elif status == pulp.LpStatusUndefined:
        row_solver_status = "UNDEFINED"
    elif status == pulp.LpStatusUnbounded:
        row_solver_status = "UNBOUNDED"
    else:
        row_solver_status = "FEASIBLE"

    def _constraint_pi(name: str) -> float | None:
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

    cap_dual_rows: list[dict[str, Any]] = []
    for cname, _ccon in prob.constraints.items():
        if not str(cname).startswith("cap_"):
            continue
        pi = _constraint_pi(str(cname))
        if pi is not None:
            cap_dual_rows.append({"constraint": str(cname), "pi": float(pi)})
    cap_dual_rows.sort(key=lambda r: abs(r["pi"]), reverse=True)

    try:
        _status_label = str(pulp.LpStatus[status])
    except Exception:
        _status_label = f"code_{int(status)}"
    lp_diagnostics: dict[str, Any] = {
        "budget_upper_pi": _constraint_pi("budget_upper"),
        "budget_lower_pi": _constraint_pi("budget_lower"),
        "pulp_status_code": int(status),
        "pulp_status_label": _status_label,
        "reach_cap_duals_top5": cap_dual_rows[:5],
    }

    rows: list[dict[str, Any]] = []

    # Result-level binding constraints: zero-slack global constraints
    # (budget band, coverage floors, bundle minimum-spend floors). Bundle
    # cardinality constraints are tight by construction so reporting them adds
    # noise; per-cell link/cap constraints are reported per row instead.
    _GLOBAL_PREFIXES = ("budget_", "coverage_", "bundle_min_spend_")
    binding: list[str] = []
    for cname, con in prob.constraints.items():
        if not str(cname).startswith(_GLOBAL_PREFIXES):
            continue
        slack = getattr(con, "slack", None)
        try:
            slack_f = float(slack) if slack is not None else None
        except (TypeError, ValueError):
            slack_f = None
        if slack_f is not None and abs(slack_f) <= 1e-4:
            binding.append(str(cname))
    binding.sort()

    def _trunc_cents(v: float) -> float:
        # Truncate to cents so the cumulative output never breaches the LP envelope.
        return int(v * 100.0) / 100.0

    for (d, c, wi), x_var in x.items():
        raw_v = pulp.value(cast(Any, x_var))
        val_usd = float(raw_v) if raw_v is not None else 0.0
        val_usd = _trunc_cents(val_usd)
        w = WEEK_LABELS[wi - 1]
        cap_row = caps_lookup.loc[(d, c)]
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
        scenario_w = _scenario_week_weight(problem.scenario_id, wi)
        dept_tier = str(cap_row["department_tier"])
        tier_w = _tier_penalty(dept_tier)
        persuasion = contacts * attention * salience * hostility * scenario_w * tier_w
        tier_default = str(cap_row["fx_tier_default"])
        bundle_id = CHANNEL_TO_BUNDLE.get(c)

        # Per-row binding diagnostic: which hard cap (if any) this cell hit.
        row_binding: str | None = None
        if c == "tv_spots" and d not in _PAY_TV_ELIGIBLE:
            row_binding = "paytv_block"
        elif reach_used >= 0.999:
            row_binding = "reach_cap"
        elif (
            dept_tier == "negligible"
            and CHANNEL_TYPES[c] == "in_person"
            and uc_usd > 0
            and val_usd >= 0.05 * audience * uc_usd - 0.01
            and val_usd > 0
        ):
            row_binding = "neg_tier_cap"

        rows.append(
            {
                "department": d,
                "channel": c,
                "channel_type": CHANNEL_TYPES[c],
                "week_index": int(wi),
                "iso_week": w,
                "department_tier": dept_tier,
                "region": str(cap_row["region"]),
                "budget_allocation_usd": val_usd,
                "budget_allocation_pyg": round(val_usd * layer.rate(w, tier_default), 2),  # type: ignore[arg-type]  # w/tier_default are str; layer.rate expects Literal types; loop controls valid values
                "fx_tier": tier_default,
                "tc_rate_pyg_per_usd": layer.rate(w, tier_default),  # type: ignore[arg-type]  # same as above
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
        )

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
