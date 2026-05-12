"""Regression: canonical Dockerfiles under docker/ and compose build pointers."""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_COMPOSE = _REPO / "docker-compose.yml"
_DOCKER_DIR = _REPO / "docker"
_LEGACY_MODULE_A_DOCKERFILE = _REPO / "module_a_population_segmentation" / "docker" / "Dockerfile"


def _compose() -> dict:
    return yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))


def test_canonical_dockerfiles_exist() -> None:
    assert (_DOCKER_DIR / "Dockerfile").is_file(), "Expected docker/Dockerfile (Module A image)"
    assert (_DOCKER_DIR / "mlflow.Dockerfile").is_file(), "Expected docker/mlflow.Dockerfile"


def test_docker_compose_points_at_existing_dockerfiles() -> None:
    cfg = _compose()
    assert cfg.get("version") == "3.9", "docker-compose.yml must declare version: '3.9' (Codebase Maturity contract)"
    services = cfg.get("services") or {}
    module_a = services.get("module_a") or {}
    mlflow = services.get("mlflow") or {}
    mod_df = (module_a.get("build") or {}).get("dockerfile")
    mlf_df = (mlflow.get("build") or {}).get("dockerfile")
    assert mod_df == "docker/Dockerfile", (
        "module_a build.dockerfile must be docker/Dockerfile, " f"got {mod_df!r}"
    )
    assert mlf_df == "docker/mlflow.Dockerfile", (
        "mlflow build.dockerfile must be docker/mlflow.Dockerfile, " f"got {mlf_df!r}"
    )
    for rel in (mod_df, mlf_df):
        path = _REPO / rel
        assert path.is_file(), f"Compose references missing file: {path}"


def test_module_a_dockerfile_not_duplicated_under_module_package() -> None:
    assert not _LEGACY_MODULE_A_DOCKERFILE.exists(), (
        "Remove module_a_population_segmentation/docker/Dockerfile; "
        "canonical image is docker/Dockerfile"
    )
