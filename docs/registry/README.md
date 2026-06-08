# Documentation registry (operators)

Authoritative inventory lives in [`docs_registry.yaml`](docs_registry.yaml) (YAML). Human navigation [`../INDEX.md`](../INDEX.md) is **generated**:

```bash
poetry run python scripts/build_docs_registry.py
poetry run python scripts/generate_doc_index.py --write
```

Verification runs under `make validate`: `scripts/verify_doc_registry.py`, `scripts/check_doc_drift.py`. Document metadata (`doc_id`, roles, lineage) lives in `docs_registry.yaml` only — Markdown files do not carry YAML headers. `check_doc_frontmatter.py` remains for repos that opt back in via `frontmatter_required: true`.

## Authority ordering (operators)

Conflicting prose claims are interpreted using [`authority_precedence.yaml`](authority_precedence.yaml) (`authority_rank`). That list must stay a **permutation** of [`taxonomy.yaml`](taxonomy.yaml) `authority_values`; `verify_doc_registry.py` enforces this.

## Structural schema

`docs_registry.yaml` shape is validated with Pydantic (`scripts/doc_registry_schema.py`). Export JSON Schema for reviewers or external tools:

```bash
make doc-registry-schema-export
```

Output: [`doc_registry.schema.json`](doc_registry.schema.json) (regenerate after changing the models).

## Membership vs semantic truth

1. **Builder membership:** `git ls-files '*.md'` defines which Markdown paths are emitted into the registry (respects the index / staging in your worktree).
2. **Semantic conformance:** `scripts/verify_doc_registry.py` validates the emitted YAML (schema, lineage, enums, precedence rules).
3. **CI:** workflows only see **committed** snapshots; run `make doc-registry-verify` locally before pushing.

Path-level generation policy (stable `doc_id` and roles) lives in [`path_overrides.yaml`](path_overrides.yaml). Do not raise `override_guard.max_paths` without a brief note in [`../../reports/decision_log.md`](../../reports/decision_log.md) (and use `maintainer/doc_debt/` if the change is contentious).
