# paraguay_departments.geojson — provenance

| Field | Value |
|---|---|
| Source | [geoBoundaries](https://www.geoboundaries.org/) PRY ADM1 |
| Input archive | `data\raw\geoBoundaries-PRY-ADM1-all.zip` |
| Input SHA-256 | `26587033fe085206652c797fcf39eb83f0e5dcb3e424b09a51e22bfbc6cfc304` |
| Member extracted | `geoBoundaries-PRY-ADM1_simplified.geojson` |
| Build date | 2026-07-14 |
| Build script | `scripts/build_paraguay_adm1_geojson.py` |
| Feature count | 18 (Exterior excluded — no ADM1 geometry) |

## Citation

When using these boundaries, cite geoBoundaries per the terms in
`CITATION-AND-USE-geoBoundaries.txt` inside the source zip.

## Regeneration

```bash
poetry run python scripts/build_paraguay_adm1_geojson.py \
  --zip-path data/raw/geoBoundaries-PRY-ADM1-all.zip
```
