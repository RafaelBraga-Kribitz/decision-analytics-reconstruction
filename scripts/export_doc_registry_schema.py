#!/usr/bin/env python3
"""Emit docs/registry/doc_registry.schema.json from Pydantic models."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.doc_registry_schema import (
    export_json_schema,
)


def main() -> int:
    export_json_schema(ROOT / "docs" / "registry" / "doc_registry.schema.json")
    print("Wrote docs/registry/doc_registry.schema.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
