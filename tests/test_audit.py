from __future__ import annotations

import json
from pathlib import Path

from oraec_tf.audit import audit_source


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _source_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()

    (root / "README.md").write_text(
        """# corpus_raw_data

| file | license | author | source |
| --- | --- | --- | --- |
| mapping_oraec_trismegistos.csv | cc0 | ORAEC | |
| oraec_hierarchical_path.tsv | cc-by-sa-4.0 | ORAEC | |
| oraec1.json .. oraec2.json | cc-by-sa-4.0 | ORAEC | AED |
| all files in FOLDER statistics | cc0 | ORAEC | |
| all files in FOLDER collocation | cc0 | ORAEC | |
""",
        encoding="utf-8",
    )

    _write_json(
        root / "oraec1.json",
        {
            "oraec1": {
                "oraecid": "oraec1",
                "title": "One",
                "date": [{"date": "Period A", "id": "DATE1"}],
                "origplace": [{"origplace": "Place A", "id": "PLACE1"}],
                "objecttype": [{"objecttype": "Stele", "id": "OBJ1"}],
                "location": [{"location": "Museum", "id": "LOC1"}],
                "material": [{"material": "Stone", "id": "MAT1"}],
                "condition": "fragmentary",
                "idno": ["X", "X"],
                "bibliography": "Ref",
                "sentences": [
                    {
                        "translation": "Sentence one",
                        "token": [
                            {
                                "lineCount": "[1]",
                                "written_form": "nṯr",
                                "cotext_translation": "god",
                                "lemma_form": "nṯr",
                                "lemmaID": "90260",
                                "pos": "substantive",
                                "hiero": "𓊹",
                                "token": "oraec1-1-1",
                            },
                            {
                                "lineCount": " [1]",
                                "written_form": "[x]",
                                "token": "oraec1-1-2",
                                "hiero": "[⯑]",
                            },
                        ],
                    }
                ],
                "credits": {
                    "license": "cc-by-sa-4.0",
                    "author": "Editor A",
                    "source": ["https://example.invalid/aed.xml"],
                },
            }
        },
    )
    _write_json(
        root / "oraec2.json",
        {
            "oraec2": {
                "oraecid": "oraec2",
                "title": "Two",
                "sentences": [
                    {
                        "token": [
                            {
                                "written_form": "m",
                                "lemma_form": "m",
                                "lemmaID": "64360",
                                "pos": "preposition",
                                "token": "oraec2-1-1",
                            }
                        ]
                    }
                ],
                "credits": {
                    "license": "cc-by-sa-4.0",
                    "author": "Editor B",
                    "source": ["https://example.invalid/aes"],
                },
            }
        },
    )

    (root / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec1,100\noraec1,101\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_karnak.tsv").write_text(
        "oraec1\thttps://example.invalid/karnak/1\n",
        encoding="utf-8",
    )
    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\troot\tchild\noraec2\troot\tother\n",
        encoding="utf-8",
    )
    _write_json(root / "statistics" / "freq.json", {"nṯr": 1})
    (root / "collocation").mkdir()
    (root / "collocation" / "pairs.tsv").write_text("a\tb\n", encoding="utf-8")

    return root


def test_audit_measures_core_corpus_contract(tmp_path: Path) -> None:
    report = audit_source(_source_fixture(tmp_path))

    assert report["inventory"]["text_file_count"] == 2
    assert report["inventory"]["text_number_min"] == 1
    assert report["inventory"]["text_number_max"] == 2
    assert report["inventory"]["missing_text_numbers"] == []
    assert report["counts"] == {"texts": 2, "sentences": 2, "tokens": 3}

    assert report["fields"]["record"]["title"]["present"] == 2
    assert report["fields"]["record"]["date"]["present"] == 1
    assert report["fields"]["record"]["date"]["missing"] == 1
    assert report["fields"]["record"]["title"]["distinct_scalar_values"] == 2
    assert report["fields"]["sentence"]["translation"]["present"] == 1
    assert report["fields"]["sentence"]["translation"]["missing"] == 1
    assert report["fields"]["token"]["lemmaID"]["present"] == 2
    assert report["fields"]["token"]["hiero"]["present"] == 2

    assert report["token_ids"]["duplicate_count"] == 0
    assert report["token_ids"]["malformed_count"] == 0
    assert report["token_ids"]["position_mismatch_count"] == 0

    assert report["line_count"]["present"] == 2
    assert report["line_count"]["distinct"] == 2
    assert report["hieroglyphs"]["present"] == 2
    assert report["hieroglyphs"]["placeholder_count"] == 1

    assert report["lemmas"]["distinct_ids"] == 2
    assert report["lemmas"]["id_to_multiple_forms_count"] == 0

    assert report["controlled_vocabulary"]["date"]["distinct_ids"] == 1
    assert report["controlled_vocabulary"]["origplace"]["distinct_ids"] == 1
    assert report["controlled_vocabulary"]["material"]["distinct_ids"] == 1
    assert report["fields"]["record"]["condition"]["distinct_scalar_values"] == 1
    assert report["line_count"]["leading_whitespace_count"] == 1
    assert report["idno"]["texts_with_duplicate_values"] == 1


def test_audit_preserves_mapping_multiplicity_and_license_gaps(tmp_path: Path) -> None:
    report = audit_source(_source_fixture(tmp_path))

    tm = report["tables"]["mapping_oraec_trismegistos.csv"]
    assert tm["rows"] == 2
    assert tm["column_counts"] == {"2": 2}
    assert tm["first_column_duplicate_values"] == 1
    assert tm["first_column_max_multiplicity"] == 2

    assert "statistics/freq.json" in report["inventory"]["non_text_files"]
    assert "collocation/pairs.tsv" in report["inventory"]["non_text_files"]
    assert "statistics" in report["inventory"]["directories"]
    assert "collocation" in report["inventory"]["directories"]

    assert "mapping_oraec_karnak.tsv" in report["license"]["uncovered_paths"]
    assert "mapping_oraec_trismegistos.csv" not in report["license"]["uncovered_paths"]


def test_audit_reports_identity_and_position_anomalies(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    payload["oraec2"]["sentences"][0]["token"][0]["token"] = "oraec999-7-4"
    _write_json(root / "oraec2.json", payload)

    report = audit_source(root)

    assert report["token_ids"]["malformed_count"] == 0
    assert report["token_ids"]["position_mismatch_count"] == 1
    assert report["anomalies"]["token_position_mismatches"][0]["actual"] == "oraec999-7-4"
    assert report["anomalies"]["token_position_mismatches"][0]["expected"] == "oraec2-1-1"


def test_audit_counts_missing_or_non_string_token_ids(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    del payload["oraec2"]["sentences"][0]["token"][0]["token"]
    _write_json(root / "oraec2.json", payload)

    report = audit_source(root)

    assert report["token_ids"]["missing_or_non_string_count"] == 1


def test_audit_records_empty_token_sentences_for_schema_design(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    payload["oraec2"]["sentences"].append(
        {"translation": "Source sentence without token slots", "token": []}
    )
    _write_json(root / "oraec2.json", payload)

    report = audit_source(root)

    assert report["sentences"]["empty_token_count"] == 1
    assert report["anomalies"]["empty_token_sentences"] == [
        {
            "text": "oraec2",
            "sentence": 2,
            "translation": "Source sentence without token slots",
        }
    ]
