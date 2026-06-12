"""CI sync gate: calibration anchors must agree across config, schema, model card.

Regression for the silent anchor drift where
`schema_contracts/participation_propensity.yaml` enforced gates against stale
department rates (e.g. Central 0.4399) while the model raked to the verified
T11-1 rates (Central 0.6207) from `config/calibration_anchors.yaml`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ANCHORS = REPO_ROOT / "module_a_population_segmentation" / "config" / "calibration_anchors.yaml"
SCHEMA = REPO_ROOT / "schema_contracts" / "participation_propensity.yaml"
MODEL_CARD = REPO_ROOT / "module_a_population_segmentation" / "reports" / "model_card_propensity.md"

# Schema gate key -> department name in calibration_anchors.yaml
ENFORCED_GATES = {
    "presidente_hayes_mean": "Presidente Hayes",
    "alto_parana_mean": "Alto Parana",
    "central_mean": "Central",
    "guaira_mean": "Guaira",
}


def _load(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def test_schema_enforced_gates_match_config_anchors() -> None:
    anchors = _load(ANCHORS)["department_participation_rates"]
    gates = _load(SCHEMA)["calibration_gates"]
    for gate_key, dept in ENFORCED_GATES.items():
        gate = gates[gate_key]
        assert gate["status"] == "ENFORCED", f"{gate_key} no longer ENFORCED"
        assert float(gate["target"]) == float(anchors[dept]), (
            f"anchor drift: schema gate {gate_key} target={gate['target']} "
            f"!= config anchor {dept}={anchors[dept]}"
        )


def test_national_informational_gate_matches_config() -> None:
    anchors = _load(ANCHORS)["national"]
    gates = _load(SCHEMA)["calibration_gates"]
    assert float(gates["national_mean"]["target"]) == float(anchors["participation_rate"])
    assert float(gates["female_mean"]["target"]) == float(anchors["female_participation_rate"])
    assert float(gates["male_mean"]["target"]) == float(anchors["male_participation_rate"])
    assert float(gates["youth_mean"]["target"]) == float(anchors["youth_participation_rate"])


def test_model_card_quotes_current_anchor_values() -> None:
    anchors = _load(ANCHORS)["department_participation_rates"]
    card = MODEL_CARD.read_text()
    for dept in ENFORCED_GATES.values():
        value = f"{float(anchors[dept]):.4f}"
        assert value in card, (
            f"model card does not quote the verified anchor for {dept} ({value}); "
            "update reports/model_card_propensity.md"
        )
