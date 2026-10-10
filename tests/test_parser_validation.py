from __future__ import annotations

import json
from pathlib import Path

import pytest

from oraec_tf.parser_validation import CorpusValidationError, validate_corpus_source


def _fixture(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec2.json | cc-by-sa-4.0 | Editor A | synthetic |\n",
        encoding="utf-8",
    )
    for number in (1, 2):
        text_id = f"oraec{number}"
        payload = {
            text_id: {
                "oraecid": text_id,
                "title": f"Text {number}",
                "sentences": [{
                    "translation": "",
                    "token": [{
                        "token": f"{text_id}-1-1",
                        "written_form": "nṯr",
                        "lemmaID": str(100 + number),
                        "lemma_form": f"lemma{number}",
                    }],
                }],
                "credits": {
                    "license": "cc-by-sa-4.0",
                    "author": "Editor A",
                    "source": ["https://example.invalid/aes", f"https://example.invalid/{number}"],
                },
            }
        }
        (source / f"{text_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    (source / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\tRoot→A\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/R">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1">A</a>\n'
        "oraec2\tRoot→B\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/R">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T2">B</a>\n',
        encoding="utf-8",
    )
    (source / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec1,100\n", encoding="utf-8"
    )
    (source / "mapping_oraec_lemmata_vega.tsv").write_text(
        "101\thttps://example.invalid/v101\n", encoding="utf-8"
    )
    (source / "mapping_oraec_wikidata.tsv").write_text(
        "Editor A\tQ1\n", encoding="utf-8"
    )
    (source / "mapping_oraec_karnak.tsv").write_text(
        "oraec2\thttps://karnak.invalid/2\n", encoding="utf-8"
    )
    (source / "mapping_oraec_lemmata_karnak.tsv").write_text(
        "102\thttps://karnak.invalid/102\n", encoding="utf-8"
    )
    return source


def test_full_parser_validation_counts_and_license_gate(tmp_path: Path) -> None:
    report = validate_corpus_source(_fixture(tmp_path))
    assert report["counts"]["texts"] == 2
    assert report["counts"]["sentences"] == 2
    assert report["counts"]["tokens"] == 2
    assert report["counts"]["lemmas"] == 2
    assert report["counts"]["included_mapping_rows"] == 3
    assert report["counts"]["excluded_mapping_rows"] == 2
    assert report["counts"]["hierarchy_rows"] == 2
    assert report["ok"] is True


def test_full_parser_validation_rejects_global_lemma_conflict(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    path = source / "oraec2.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["oraec2"]["sentences"][0]["token"][0]["lemmaID"] = "101"
    (path).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="lemma"):
        validate_corpus_source(source)


def test_full_parser_validation_rejects_missing_text_number(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    (source / "oraec2.json").rename(source / "oraec3.json")
    with pytest.raises(CorpusValidationError, match="number"):
        validate_corpus_source(source)


def test_full_parser_validation_rejects_unresolved_external_source(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    (source / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec999,100\n", encoding="utf-8"
    )
    with pytest.raises(CorpusValidationError, match="trismegistos"):
        validate_corpus_source(source)


def test_full_parser_validation_rejects_missing_hierarchy_text(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    (source / "oraec_hierarchical_path.tsv").write_text(
        'oraec1\tA\t<a href="https://thesaurus-linguae-aegyptiae.de/text/T1">A</a>\n',
        encoding="utf-8",
    )
    with pytest.raises(CorpusValidationError, match="hierarchy"):
        validate_corpus_source(source)
