"""Translated README versions share a reading budget but retain explicit lineage."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_docs_registry as registry
import check_public_doc_count as budget


@pytest.mark.parametrize("extra, expected", [([], 0), (["EXTRA.md"], 1), (["README.fr.md"], 1)])
def test_translations_are_one_reading_unit_without_hiding_other_docs(monkeypatch, extra, expected):
    monkeypatch.setattr(budget, "MAX_PUBLIC_MD", 1)
    monkeypatch.setattr(
        budget,
        "_tracked_markdown",
        lambda: [
            "README.md",
            "README.pt-BR.md",
            "README.de-AT.md",
            *extra,
        ],
    )
    assert budget.main() == expected


@pytest.mark.parametrize("path", ["README.pt-BR.md", "README.de-AT.md"])
def test_translation_registry_entry_is_derived_from_english(path):
    entry = registry.merged_entry(path, defaultdict(int))
    assert entry["doc_role"] == "derived"
    assert entry["visibility"] == "public"
    assert entry["canonical_source"] == registry.OVERRIDE["README.md"]["canonical_source"]
    assert entry["derived_from"] == [registry.OVERRIDE["README.md"]["doc_id"]]
    assert entry["doc_id"] != registry.OVERRIDE["README.md"]["doc_id"]
