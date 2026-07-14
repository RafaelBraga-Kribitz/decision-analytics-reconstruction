#!/usr/bin/env python3
"""Build package GeoJSON from geoBoundaries PRY ADM1 zip.

Reads ``data/raw/geoBoundaries-PRY-ADM1-all.zip`` (gitignored), maps
geoBoundaries ``shapeName`` values to canonical ``DEPARTMENTS`` labels, and
writes:

  module_c_forecasting_scenarios/src/module_c_forecasting_scenarios/geo/
    paraguay_departments.geojson
    paraguay_departments.SOURCE.md

Maintainers re-run when updating boundary vintages. CI uses the committed output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from module_b_resource_allocation.constants import DEPARTMENTS

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = REPO_ROOT / "data" / "raw" / "geoBoundaries-PRY-ADM1-all.zip"
GEO_OUT = (
    REPO_ROOT
    / "module_c_forecasting_scenarios"
    / "src"
    / "module_c_forecasting_scenarios"
    / "geo"
    / "paraguay_departments.geojson"
)
SOURCE_OUT = GEO_OUT.with_suffix(".SOURCE.md")
GEOJSON_MEMBER = "geoBoundaries-PRY-ADM1_simplified.geojson"
COORD_DECIMALS = 5

# Explicit overrides where ascii folding alone is insufficient.
_EXPLICIT: dict[str, str] = {
    "ASUNCION": "Asuncion",
    "ALTO PARAGUAY": "Alto Paraguay",
    "ALTO PARANA": "Alto Parana",
    "AMAMBAY": "Amambay",
    "BOQUERON": "Boqueron",
    "CAAGUAZU": "Caaguazu",
    "CAAZAPA": "Caazapa",
    "CANINDEYU": "Canindeyu",
    "CENTRAL": "Central",
    "CONCEPCION": "Concepcion",
    "CORDILLERA": "Cordillera",
    "GUAIRA": "Guaira",
    "ITAPUA": "Itapua",
    "MISIONES": "Misiones",
    "PARAGUARI": "Paraguari",
    "PRESIDENTE HAYES": "Presidente Hayes",
    "SAN PEDRO": "San Pedro",
    "NEEMBUCU": "Neembucu",
    "ÑEEMBUCU": "Neembucu",
}


def _ascii_fold(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper().strip()


def _map_shape_name(shape_name: str) -> str:
    key = _ascii_fold(shape_name)
    if key in _EXPLICIT:
        return _EXPLICIT[key]
    # Title-case fallback: "SAN PEDRO" -> try match against DEPARTMENTS via fold
    folded_depts = {_ascii_fold(d): d for d in DEPARTMENTS}
    if key in folded_depts:
        return folded_depts[key]
    raise ValueError(f"Unmapped geoBoundaries shapeName: {shape_name!r} (folded={key!r})")


def _round_coords(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(obj, COORD_DECIMALS)
    if isinstance(obj, list):
        return [_round_coords(x) for x in obj]
    return obj


def build(zip_path: Path) -> tuple[dict[str, Any], str]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"geoBoundaries zip not found: {zip_path}")

    zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(zip_path) as zf:
        if GEOJSON_MEMBER not in zf.namelist():
            raise FileNotFoundError(f"{GEOJSON_MEMBER} not found inside {zip_path}")
        raw = json.loads(zf.read(GEOJSON_MEMBER))

    if len(raw.get("features", [])) != len(DEPARTMENTS):
        raise ValueError(
            f"Expected {len(DEPARTMENTS)} ADM1 features, got {len(raw.get('features', []))}"
        )

    out_features: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feat in raw["features"]:
        shape_name = str(feat["properties"]["shapeName"])
        department = _map_shape_name(shape_name)
        if department in seen:
            raise ValueError(f"Duplicate mapping for department {department!r}")
        seen.add(department)
        geom = _round_coords(feat["geometry"])
        if geom["type"] not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"{department}: unsupported geometry {geom['type']}")
        out_features.append(
            {
                "type": "Feature",
                "properties": {
                    "department": department,
                    "geoboundaries_shape_name": shape_name,
                },
                "geometry": geom,
            }
        )

    missing = set(DEPARTMENTS) - seen
    if missing:
        raise ValueError(f"Missing departments after mapping: {sorted(missing)}")

    out_features.sort(key=lambda f: f["properties"]["department"])

    collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "_note": (
            "geoBoundaries PRY ADM1 simplified administrative boundaries. "
            "Exterior (diaspora) has no ADM1 polygon and is omitted. "
            "Regenerate via scripts/build_paraguay_adm1_geojson.py."
        ),
        "features": out_features,
    }
    return collection, zip_sha


def write_source_md(zip_path: Path, zip_sha: str) -> str:
    resolved = zip_path.resolve()
    root = REPO_ROOT.resolve()
    rel = resolved.relative_to(root) if resolved.is_relative_to(root) else zip_path
    text = f"""# paraguay_departments.geojson — provenance

| Field | Value |
|---|---|
| Source | [geoBoundaries](https://www.geoboundaries.org/) PRY ADM1 |
| Input archive | `{rel}` |
| Input SHA-256 | `{zip_sha}` |
| Member extracted | `{GEOJSON_MEMBER}` |
| Build date | {date.today().isoformat()} |
| Build script | `scripts/build_paraguay_adm1_geojson.py` |
| Feature count | {len(DEPARTMENTS)} (Exterior excluded — no ADM1 geometry) |

## Citation

When using these boundaries, cite geoBoundaries per the terms in
`CITATION-AND-USE-geoBoundaries.txt` inside the source zip.

## Regeneration

```bash
poetry run python scripts/build_paraguay_adm1_geojson.py \\
  --zip-path data/raw/geoBoundaries-PRY-ADM1-all.zip
```
"""
    return text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build paraguay_departments.geojson from geoBoundaries ADM1"
    )
    p.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--out-geojson", type=Path, default=GEO_OUT)
    p.add_argument("--out-source", type=Path, default=SOURCE_OUT)
    args = p.parse_args(argv)

    collection, zip_sha = build(args.zip_path)
    args.out_geojson.parent.mkdir(parents=True, exist_ok=True)
    args.out_geojson.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    args.out_source.write_text(write_source_md(args.zip_path, zip_sha), encoding="utf-8")

    print(f"[OK] wrote {args.out_geojson} ({len(collection['features'])} features)")
    print(f"[OK] wrote {args.out_source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
