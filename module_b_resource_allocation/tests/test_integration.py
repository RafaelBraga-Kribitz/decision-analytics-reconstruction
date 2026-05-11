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
    assert body["solver_status"] in {"Optimal", "Feasible"}
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
