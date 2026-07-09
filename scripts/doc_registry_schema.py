"""Pydantic schema for docs/registry/docs_registry.yaml structural conformance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Vendored subtrees and CI/tooling dirs — excluded from registry tracking.
# Single source for build_docs_registry.py and verify_doc_registry.py; the two
# scripts drifted once (F-076) when .github/ was added to only one of them.
VENDOR_PREFIXES = ("governance/_kit/", ".github/")


class RegistryDocument(BaseModel):
    """Single inventory row — keys must match emitted YAML (no unknown keys)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    doc_id: str
    path: str
    doc_type: str
    doc_role: str
    visibility: str
    authority: str
    status: str = "active"
    sensitivity: str
    owner: str
    last_reviewed: str
    audience: list[str]
    canonical_source: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    numeric_authority: list[str] = Field(default_factory=list)
    frontmatter_required: bool = True
    tier_shorthand: str | None = None
    allowed_content: list[str] | None = None
    forbidden_content: list[str] | None = None
    tags: list[str] | None = None
    governance_subject: str | None = None


class RegistryRoot(BaseModel):
    """Root object written by scripts/build_docs_registry.py."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    numeric_namespaces: dict[str, dict[str, Any]]
    documents: list[RegistryDocument]


def parse_registry_payload(reg: dict[str, Any]) -> RegistryRoot:
    """Validate loaded YAML; raises pydantic.ValidationError on mismatch."""
    return RegistryRoot.model_validate(reg)


def export_json_schema(dest: Path) -> None:
    """Write JSON Schema for RegistryRoot (Draft 2020-12 style via Pydantic)."""
    schema = RegistryRoot.model_json_schema()
    import json

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
