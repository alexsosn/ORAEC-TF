"""RED-first, schema-exhaustive researcher documentation requirements (#10)."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_feature_reference_covers_exact_frozen_native_schema() -> None:
    schema = json.loads((ROOT / "schema" / "core.json").read_text(encoding="utf-8"))
    reference = (ROOT / "docs" / "features.md").read_text(encoding="utf-8")
    expected = {
        f"{node_type}.{feature}"
        for node_type, node in schema["nodeTypes"].items()
        for feature in node["features"]
    }
    expected |= {f"edge.{feature}" for feature in schema["edgeFeatures"]}
    documented = set(
        re.findall(
            r"^\\| `((?:edge|word|sentence|text|lex|cv|author|source_ref|"
            r"idno|hierarchy|external_ref)\\.[a-z0-9_]+)` \\|",
            reference,
            flags=re.MULTILINE,
        )
    )
    assert documented == expected
    for topic in ("source", "derived", "anchor", "CR", "licence", "mapping"):
        assert topic.lower() in reference.lower()


def test_researcher_example_script_is_syntax_valid_and_self_contained() -> None:
    path = ROOT / "docs" / "examples.py"
    script = path.read_text(encoding="utf-8")
    parsed = ast.parse(script, filename=str(path))
    functions = {
        node.name for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {
        "load_corpus", "find_text", "sentences", "lexeme_words",
        "hierarchy_path", "external_identifiers",
    } <= functions
