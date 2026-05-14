"""DVC pipeline config validation — dvc.yaml and dvc.lock structural checks."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_DVC_YAML = _ROOT / "dvc.yaml"
_DVC_LOCK = _ROOT / "dvc.lock"
_EXPECTED_STAGES = {"module_a", "module_b", "module_c"}


def test_dvc_yaml_exists_and_has_required_stages() -> None:
    assert _DVC_YAML.is_file(), "dvc.yaml missing — run `dvc repro` or create pipeline"
    doc = yaml.safe_load(_DVC_YAML.read_text(encoding="utf-8"))
    assert "stages" in doc, "dvc.yaml missing 'stages' key"
    stages = set(doc["stages"].keys())
    assert stages >= _EXPECTED_STAGES, f"Missing DVC stages: {_EXPECTED_STAGES - stages}"


def test_dvc_lock_exists_and_matches_stages() -> None:
    assert _DVC_LOCK.is_file(), "dvc.lock missing — run `dvc repro` to generate pipeline lock file"
    lock = yaml.safe_load(_DVC_LOCK.read_text(encoding="utf-8"))
    assert "stages" in lock, "dvc.lock missing 'stages' key"
    locked_stages = set(lock["stages"].keys())
    assert (
        locked_stages >= _EXPECTED_STAGES
    ), f"dvc.lock missing stages: {_EXPECTED_STAGES - locked_stages}"


def test_dvc_yaml_each_stage_has_cmd_deps_outs() -> None:
    doc = yaml.safe_load(_DVC_YAML.read_text(encoding="utf-8"))
    for stage_name in _EXPECTED_STAGES:
        stage = doc["stages"][stage_name]
        assert "cmd" in stage, f"Stage '{stage_name}' missing 'cmd'"
        assert "deps" in stage, f"Stage '{stage_name}' missing 'deps'"
        assert "outs" in stage, f"Stage '{stage_name}' missing 'outs'"
        assert len(stage["deps"]) >= 1, f"Stage '{stage_name}' has no deps"
        assert len(stage["outs"]) >= 1, f"Stage '{stage_name}' has no outs"
