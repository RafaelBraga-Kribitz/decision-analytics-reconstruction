"""Canonical entry: ``python -m population_segmentation.pipeline``.

Defaults assume the current working directory is the repository root:
``module_a_population_segmentation/config/generation.yaml``,
``module_a_population_segmentation/config/calibration_anchors.yaml``,
``data/processed``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from population_segmentation.pipeline.export import run_export

_DEFAULT_CFG = Path("module_a_population_segmentation/config/generation.yaml")
_DEFAULT_ANCHORS = Path("module_a_population_segmentation/config/calibration_anchors.yaml")
_DEFAULT_OUT = Path("data/processed")


def _resolve_defaults(
    config: Path | None,
    anchors: Path | None,
    out_dir: Path | None,
) -> tuple[Path, Path, Path]:
    root = Path.cwd()
    c = config if config is not None else (root / _DEFAULT_CFG).resolve()
    a = anchors if anchors is not None else (root / _DEFAULT_ANCHORS).resolve()
    o = out_dir if out_dir is not None else (root / _DEFAULT_OUT).resolve()
    return c, a, o


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Module A end-to-end pipeline: generation → injection → cleaning → "
            "features → segmentation → propensity → contract artifacts."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"Path to generation.yaml (default: {_DEFAULT_CFG})",
    )
    parser.add_argument(
        "--anchors",
        type=Path,
        default=None,
        help=f"Path to calibration_anchors.yaml (default: {_DEFAULT_ANCHORS})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=f"Output directory (default: {_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Override sample_size in config (optional)",
    )
    ns = parser.parse_args(argv)

    cfg_p, anch_p, out_p = _resolve_defaults(ns.config, ns.anchors, ns.out_dir)
    if not cfg_p.is_file():
        print(f"error: config file not found: {cfg_p}", file=sys.stderr)
        return 2
    if not anch_p.is_file():
        print(f"error: anchors file not found: {anch_p}", file=sys.stderr)
        return 2

    with open(cfg_p, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)
    with open(anch_p, encoding="utf-8") as f:
        anchors: dict[str, Any] = yaml.safe_load(f)

    try:
        artifacts = run_export(config, anchors, out_p, sample_size=ns.sample_size)
    except Exception as exc:
        print(f"error: pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("\n[pipeline] Done. Artifacts:")
    for name, path in artifacts.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
