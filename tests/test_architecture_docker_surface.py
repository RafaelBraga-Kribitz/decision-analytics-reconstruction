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


def _service_dockerfile(cfg: dict, service: str) -> str:
    services = cfg.get("services") or {}
    build = (services.get(service) or {}).get("build") or {}
    return str(build.get("dockerfile", ""))


def test_docker_compose_declares_version_3_9() -> None:
    assert _compose().get("version") == "3.9"


def test_docker_compose_points_at_existing_dockerfiles() -> None:
    cfg = _compose()
    mod_df = _service_dockerfile(cfg, "module_a")
    mlf_df = _service_dockerfile(cfg, "mlflow")
    assert mod_df == "docker/Dockerfile", f"module_a dockerfile got {mod_df!r}"
    assert mlf_df == "docker/mlflow.Dockerfile", f"mlflow dockerfile got {mlf_df!r}"
    for rel in (mod_df, mlf_df):
        assert (_REPO / rel).is_file(), f"Compose references missing file: {rel}"


def test_module_a_dockerfile_not_duplicated_under_module_package() -> None:
    assert not _LEGACY_MODULE_A_DOCKERFILE.exists(), (
        "Remove module_a_population_segmentation/docker/Dockerfile; "
        "canonical image is docker/Dockerfile"
    )
