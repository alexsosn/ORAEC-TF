from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-source-layer-and-tff.md"
PYPROJECT = ROOT / "pyproject.toml"


def test_source_layer_and_tff_decision_is_recorded() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "Decision: use as implementation/reference material only" in text
    assert "oraec/corpus_raw_data" in text
    assert "tf.convert.walker.CV" in text


def test_text_fabric_factory_is_not_a_runtime_dependency() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8").lower()
    assert "text-fabric-factory" not in pyproject
