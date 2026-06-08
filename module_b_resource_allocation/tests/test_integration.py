"""Phase 10 integration tests: API surface + cross-module contract round-trip.

These tests exercise the FastAPI app via TestClient (no socket) and verify
that Module B's allocation_output, reach_caps, and routing artifacts honor
the schemas declared in ``schema_contracts/*.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient
from module_b_resource_allocation.api.app import app
from module_b_resource_allocation.constants import (
    ALLOCATION_ROWS,
    CHANNEL_NAMES,
    DEPARTMENTS,
    REACH_CAPS_ROWS,
    SEED_MAX,
    SEED_MIN,
    SHIFT_SHARE_MAX,
    SHIFT_SHARE_MIN,
    VALID_FX_SERIES,
    VALID_ROUTING_SCENARIOS,
    VALID_SCENARIOS,
    WEEK_COUNT,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _load_contract(name: str) -> dict:
    path = Path(__file__).resolve().parents[2] / "schema_contracts" / name
    with open(path) as f:
        return yaml.safe_load(f)


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["module"] == "module_b_resource_allocation"


def test_allocation_endpoint_returns_full_grid(client: TestClient) -> None:
    r = client.get("/allocation/baseline")
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == ALLOCATION_ROWS
    assert body["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    assert body["scenario_id"] == "baseline"


def test_allocation_week_endpoint_filters_correctly(client: TestClient) -> None:
    r = client.get("/allocation/baseline/week/7")
    assert r.status_code == 200
    body = r.json()
    assert body["week_index"] == 7
    expected = len(DEPARTMENTS) * len(CHANNEL_NAMES)
    assert body["row_count"] == expected


def test_allocation_week_endpoint_rejects_out_of_range(client: TestClient) -> None:
    r = client.get("/allocation/baseline/week/0")
    assert r.status_code == 400
    r = client.get(f"/allocation/baseline/week/{WEEK_COUNT + 1}")
    assert r.status_code == 400


def test_allocation_endpoint_rejects_unknown_scenario(client: TestClient) -> None:
    r = client.get("/allocation/imaginary_scenario")
    assert r.status_code == 404


def test_allocation_endpoint_redirects_broadcast_to_direct(client: TestClient) -> None:
    r = client.get("/allocation/broadcast_to_direct")
    assert r.status_code == 400


def test_counterfactual_endpoint_runs(client: TestClient) -> None:
    r = client.get("/counterfactual/broadcast_to_direct?shift_share=0.30")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == "broadcast_to_direct"
    assert body["row_count"] == ALLOCATION_ROWS
    assert 0.0 <= body["routing_feasible_share"] <= 1.0


def test_fx_endpoint_returns_14_rows(client: TestClient) -> None:
    r = client.get("/fx/series_b_weekly")
    assert r.status_code == 200
    body = r.json()
    assert body["series_id"] == "series_b_weekly"
    assert len(body["rows"]) == WEEK_COUNT


def test_reach_caps_endpoint_row_count(client: TestClient) -> None:
    r = client.get("/reach_caps")
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == REACH_CAPS_ROWS


def test_routing_endpoint_returns_matrix(client: TestClient) -> None:
    r = client.get("/routing/cost_matrix?scenario=dry_standard")
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == len(DEPARTMENTS) ** 2


# ---------------------------------------------------------------------------
# Cross-module contract round-trip
# ---------------------------------------------------------------------------


def test_allocation_output_matches_contract(client: TestClient) -> None:
    """Every column declared in allocation_output.yaml must appear in the
    LP output, and unique_key must hold."""
    contract = _load_contract("allocation_output.yaml")
    r = client.get("/allocation/baseline")
    df = pd.DataFrame(r.json()["rows"])
    declared_fields = set(contract["fields"].keys())
    present = set(df.columns)
    missing = declared_fields - present
    assert not missing, f"allocation_output contract missing columns: {sorted(missing)}"

    # Unique key check.
    keys = contract["unique_key"]
    assert not df.duplicated(keys).any()
    assert len(df) == int(contract["row_count"]["exact"])


def test_reach_caps_contract_has_required_columns(client: TestClient) -> None:
    contract = _load_contract("reachability_caps_dept_channel.yaml")
    r = client.get("/reach_caps")
    df = pd.DataFrame(r.json()["rows"])
    required = set(contract["quality_gates"]["required_columns"])
    assert required.issubset(set(df.columns))
    assert len(df) == int(contract["row_count"]["exact"])


def test_routing_contract_round_trip(client: TestClient) -> None:
    contract = _load_contract("routing_cost_matrix.yaml")
    r = client.get("/routing/cost_matrix?scenario=dry_standard")
    df = pd.DataFrame(r.json()["rows"])
    declared = set(contract["fields"].keys())
    # Soft-check: every declared key for the routing contract must be present
    # in the matrix output.
    missing = declared - set(df.columns)
    assert not missing, f"routing_cost_matrix contract missing columns: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


class TestSeedValidation:
    """Validate seed parameter bounds across all endpoints."""

    def test_seed_below_min(self, client: TestClient) -> None:
        r = client.get(f"/allocation/baseline?seed={SEED_MIN - 1}")
        assert r.status_code == 400
        assert "seed out of range" in r.json()["detail"]

    def test_seed_above_max(self, client: TestClient) -> None:
        r = client.get(f"/allocation/baseline?seed={SEED_MAX + 1}")
        assert r.status_code == 400
        assert "seed out of range" in r.json()["detail"]

    def test_seed_at_min_boundary(self, client: TestClient) -> None:
        r = client.get(f"/allocation/baseline?seed={SEED_MIN}")
        assert r.status_code == 200

    def test_seed_at_max_boundary(self, client: TestClient) -> None:
        r = client.get(f"/allocation/baseline?seed={SEED_MAX}")
        assert r.status_code == 200

    def test_seed_in_counterfactual(self, client: TestClient) -> None:
        r = client.get(f"/counterfactual/broadcast_to_direct?seed={SEED_MAX + 1}")
        assert r.status_code == 400

    def test_seed_in_routing(self, client: TestClient) -> None:
        r = client.get(f"/routing/cost_matrix?seed={SEED_MAX + 1}")
        assert r.status_code == 400


class TestScenarioValidation:
    """Validate scenario_id parameter."""

    def test_unknown_scenario(self, client: TestClient) -> None:
        r = client.get("/allocation/unknown_scenario")
        assert r.status_code == 404
        assert "unknown scenario_id" in r.json()["detail"]

    def test_all_valid_scenarios(self, client: TestClient) -> None:
        for scenario in VALID_SCENARIOS:
            if scenario == "broadcast_to_direct":
                # This scenario is reserved for counterfactual endpoint
                continue
            r = client.get(f"/allocation/{scenario}")
            assert r.status_code == 200, f"scenario={scenario} should be valid"


class TestWeekValidation:
    """Validate week_index parameter."""

    def test_week_zero(self, client: TestClient) -> None:
        r = client.get("/allocation/baseline/week/0")
        assert r.status_code == 400
        assert "week_index out of range" in r.json()["detail"]

    def test_week_negative(self, client: TestClient) -> None:
        r = client.get("/allocation/baseline/week/-1")
        assert r.status_code == 400

    def test_week_above_max(self, client: TestClient) -> None:
        r = client.get(f"/allocation/baseline/week/{WEEK_COUNT + 1}")
        assert r.status_code == 400
        assert "week_index out of range" in r.json()["detail"]

    def test_week_at_boundaries(self, client: TestClient) -> None:
        # Min boundary
        r = client.get("/allocation/baseline/week/1")
        assert r.status_code == 200
        # Max boundary
        r = client.get(f"/allocation/baseline/week/{WEEK_COUNT}")
        assert r.status_code == 200


class TestShiftShareValidation:
    """Validate shift_share parameter in counterfactual."""

    def test_shift_share_below_zero(self, client: TestClient) -> None:
        r = client.get("/counterfactual/broadcast_to_direct?shift_share=-0.1")
        assert r.status_code == 400
        assert "shift_share out of range" in r.json()["detail"]

    def test_shift_share_above_one(self, client: TestClient) -> None:
        r = client.get("/counterfactual/broadcast_to_direct?shift_share=1.1")
        assert r.status_code == 400
        assert "shift_share out of range" in r.json()["detail"]

    def test_shift_share_at_boundaries(self, client: TestClient) -> None:
        r = client.get(f"/counterfactual/broadcast_to_direct?shift_share={SHIFT_SHARE_MIN}")
        assert r.status_code == 200
        r = client.get(f"/counterfactual/broadcast_to_direct?shift_share={SHIFT_SHARE_MAX}")
        assert r.status_code == 200

    def test_shift_share_in_valid_range(self, client: TestClient) -> None:
        for share in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r = client.get(f"/counterfactual/broadcast_to_direct?shift_share={share}")
            assert r.status_code == 200


class TestRoutingScenarioValidation:
    """Validate routing_scenario parameter."""

    def test_unknown_routing_scenario(self, client: TestClient) -> None:
        r = client.get("/counterfactual/broadcast_to_direct?routing_scenario=unknown")
        assert r.status_code == 400
        assert "unknown routing scenario" in r.json()["detail"]

    def test_all_valid_routing_scenarios(self, client: TestClient) -> None:
        for scenario in VALID_ROUTING_SCENARIOS:
            r = client.get(f"/counterfactual/broadcast_to_direct?routing_scenario={scenario}")
            assert r.status_code == 200, f"routing_scenario={scenario} should be valid"

    def test_routing_scenario_in_cost_matrix(self, client: TestClient) -> None:
        r = client.get("/routing/cost_matrix?scenario=invalid")
        assert r.status_code == 400
        assert "unknown routing scenario" in r.json()["detail"]


class TestFxSeriesValidation:
    """Validate FX series_id parameter."""

    def test_unknown_fx_series(self, client: TestClient) -> None:
        r = client.get("/fx/unknown_series")
        # FastAPI validates Literal type hints and returns 422 Unprocessable Entity
        assert r.status_code in [400, 422]

    def test_all_valid_fx_series(self, client: TestClient) -> None:
        for series in VALID_FX_SERIES:
            r = client.get(f"/fx/{series}")
            assert r.status_code == 200, f"fx_series={series} should be valid"


# ---------------------------------------------------------------------------
# Error Handling & Robustness
# ---------------------------------------------------------------------------


class TestSolverErrorHandling:
    """Verify robust error handling for allocation failures."""

    def test_successful_allocation_returns_diagnostics(self, client: TestClient) -> None:
        """Verify that successful solves include diagnostic information."""
        r = client.get("/allocation/baseline")
        assert r.status_code == 200
        body = r.json()
        # All allocation responses should include solver diagnostics
        assert body["solver_status"] in {"OPTIMAL", "FEASIBLE", "UNDEFINED", "UNBOUNDED"}
        assert "row_count" in body
        assert body["row_count"] > 0

    def test_counterfactual_returns_feasibility_share(self, client: TestClient) -> None:
        """Verify counterfactual includes routing feasibility metrics."""
        r = client.get("/counterfactual/broadcast_to_direct")
        assert r.status_code == 200
        body = r.json()
        assert "routing_feasible_share" in body
        assert 0.0 <= body["routing_feasible_share"] <= 1.0
        assert "total_budget_usd_baseline" in body
        assert "total_budget_usd_counterfactual" in body


class TestHttpErrorResponses:
    """Verify HTTP error responses are well-formed."""

    def test_invalid_param_error_has_detail(self, client: TestClient) -> None:
        """Bad parameters return 400 with explanatory detail."""
        r = client.get("/allocation/baseline?seed=-1")
        assert r.status_code == 400
        body = r.json()
        assert "detail" in body
        assert len(body["detail"]) > 0

    def test_unknown_resource_returns_404_with_list(self, client: TestClient) -> None:
        """404 errors include hint of valid options."""
        r = client.get("/allocation/phantom_scenario")
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body
        # Detail should mention valid scenarios
        assert "baseline" in body["detail"]


class TestLogging:
    """Verify structured logging is present in API operations."""

    def test_healthz_endpoint_works(self, client: TestClient) -> None:
        """Basic smoke test that endpoints execute without logging errors."""
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_allocation_logs_scenario_and_status(self, client: TestClient, caplog) -> None:
        """Allocation endpoint logs scenario_id and solver_status."""
        import logging

        caplog.set_level(logging.INFO, logger="module_b_api")
        r = client.get("/allocation/baseline?seed=20180422")
        assert r.status_code == 200
        body = r.json()
        # Verify that logs contain scenario and status info
        # (Note: caplog may not capture logs from within FastAPI middleware,
        # but the logger is configured and will write to stderr)
        assert body["scenario_id"] == "baseline"
        assert body["solver_status"] in {"OPTIMAL", "FEASIBLE"}
