from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0004-linecount-semantics.md"


def test_linecount_decision_rejects_invented_core_line_nodes() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "no core `line` node type" in text
    assert "exact `lineCount`" in text
    assert "must not be stripped" in text
    assert "contiguous-run reconstruction" in text


def test_linecount_decision_records_corpus_wide_evidence() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "789,633" in text
    assert "28,672" in text
    assert "30,467" in text
    assert "2,143" in text
    assert "7,119" in text


def test_linecount_decision_records_real_gap_counterexample() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "oraec1:83" in text
    assert "[Vs 22]" in text
    assert '<gap reason="lost"/>' in text
    assert "no intervening `<lb>`" in text
