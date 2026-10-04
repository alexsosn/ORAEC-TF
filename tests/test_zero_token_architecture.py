from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0002-zero-token-sentences.md"


def test_zero_token_sentence_decision_records_real_cases_and_tf_constraint() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "oraec17:248" in text
    assert "oraec34:256" in text
    assert "oraec5614:3" in text
    assert "tf.convert.walker.CV" in text
    assert "empty target" in text
    assert "technical anchor" in text


def test_zero_token_sentence_decision_rejects_false_extent_and_preserves_counts() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "Do not anchor to a neighbouring real source-token slot" in text
    assert "815,026 source tokens" in text
    assert "3 technical anchor slots" in text
    assert "815,029 total slots" in text
    assert "slot-type name is deferred to #3" in text
