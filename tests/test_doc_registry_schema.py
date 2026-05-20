"""Unit tests for docs registry Pydantic schema (structural contract)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.doc_registry_schema import RegistryDocument, parse_registry_payload


def test_registry_document_rejects_unknown_field() -> None:
    base = {
        "doc_id": "DOC-X-001",
        "path": "x.md",
        "doc_type": "narrative",
        "doc_role": "canonical",
        "visibility": "public",
        "authority": "canonical",
        "sensitivity": "public",
        "owner": "t",
        "last_reviewed": "2026-01-01",
        "audience": ["portfolio"],
        "not_a_real_key": "no",
    }
    with pytest.raises(ValidationError):
        RegistryDocument.model_validate(base)


def test_parse_registry_payload_rejects_extra_root_key() -> None:
    reg = {
        "schema_version": 1,
        "numeric_namespaces": {},
        "documents": [],
        "extra_root": "bad",
    }
    with pytest.raises(ValidationError):
        parse_registry_payload(reg)
