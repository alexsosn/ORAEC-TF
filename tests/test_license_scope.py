from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_SCOPE = ROOT / "LICENSE_SCOPE.md"


def test_karnak_mapping_licence_evidence_is_explicit() -> None:
    text = LICENSE_SCOPE.read_text(encoding="utf-8")

    assert "mapping_oraec_karnak.tsv" in text
    assert "mapping_oraec_lemmata_karnak.tsv" in text
    assert "CC0" in text
    assert "edd5e4dc1e567274819ed05c644b6f83cc243579" in text
    assert "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd" in text
    assert "our own things we create in the future" in text


def test_karnak_mapping_scope_is_not_inferred_from_blog_footer() -> None:
    text = LICENSE_SCOPE.read_text(encoding="utf-8")

    assert "VÉgA counterexample" in text
    assert "adapted from TLA" in text
    assert "not the content behind SITH URLs" in text
    assert "README omission" in text


def test_karnak_mappings_fail_closed_without_explicit_file_level_licence() -> None:
    text = LICENSE_SCOPE.read_text(encoding="utf-8")

    assert "strong evidence of intended CC0" in text
    assert "insufficient for release-grade file-level licensing" in text
    assert "exclude the Karnak mappings from distributable generated corpora" in text
    assert "explicit upstream clarification" in text
