from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0003-hieroglyphic-preservation.md"


def test_hiero_decision_preserves_exact_oraec_values() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "code-point-for-code-point" in text
    assert "[⯑]" in text
    assert "U+FFFD" in text
    assert "bare ⯑" in text
    assert "must not overwrite" in text


def test_hiero_decision_records_producer_evidence_and_counts() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "formerly-mdc-now_unicode" in text
    assert "complete_mapping.csv" in text
    assert "HASH" in text
    assert "US85Aa1002XT" in text
    assert "13,198" in text
    assert "6,545" in text


def test_hiero_recovery_is_not_a_core_materializer_dependency() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "optional enrichment" in text
    assert "AED" in text
    assert "not a mandatory source" in text
