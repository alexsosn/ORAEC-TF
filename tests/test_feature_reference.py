"""RED-first schema → researcher reference conservation gates (issue #10)."""

from __future__ import annotations

import json
from pathlib import Path

from oraec_tf.feature_reference import render_feature_reference

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "core.json"
DOC = ROOT / "docs" / "feature-reference.md"


def test_feature_reference_matches_all_frozen_schema_features() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    generated = render_feature_reference(schema)
    assert DOC.read_text(encoding="utf-8") == generated
    assert f"Schema version: {schema['schemaVersion']}" in generated
    assert "Source: `schema/core.json`" in generated

    for kind, declaration in schema["nodeTypes"].items():
        assert f"### `{kind}`" in generated
        for name in declaration["features"]:
            assert f"|`{name}`|" in generated

    for edge in schema["edgeFeatures"]:
        assert f"|`{edge}`|" in generated


def test_reference_provides_exact_source_and_derived_provenance() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    result = render_feature_reference(schema)
    assert "Source field(s)" in result
    assert "|Source|" in result
    assert "|Derived|" in result
    assert "token.lineCount" in result
    assert "schema v2 source U+000D" in result


def test_reference_does_not_claim_unknown_corpus_count_or_web_url() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = render_feature_reference(schema)
    assert "oraecid" in doc
    assert "Karnak" in doc
    assert "No external web endpoint is inferred" in doc
