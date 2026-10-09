from __future__ import annotations

import json
from pathlib import Path

from oraec_tf.schema_preflight import audit_schema_source


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec2.json | cc-by-sa-4.0 | Editor A, Editor B | synthetic |\n",
        encoding="utf-8",
    )

    _write_json(
        root / "oraec1.json",
        {
            "oraec1": {
                "oraecid": "oraec1",
                "title": "One",
                "date": [{"date": "Period A", "id": "D1"}],
                "sentences": [
                    {
                        "translation": "",
                        "token": [
                            {
                                "token": "oraec1-1-1",
                                "written_form": "a",
                                "lemmaID": "10",
                                "lemma_form": "a",
                            }
                        ],
                    }
                ],
                "credits": {
                    "license": "cc-by-sa-4.0",
                    "author": "Editor A",
                    "source": ["https://example.invalid/a", "https://example.invalid/aed1"],
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
                "material": [{"material": "Stone", "id": "M1"}],
                "sentences": [
                    {
                        "translation": "",
                        "token": [
                            {
                                "token": "oraec2-1-1",
                                "written_form": "b",
                                "lemmaID": "20",
                                "lemma_form": "b",
                            }
                        ],
                    }
                ],
                "credits": {
                    "license": "cc-by-sa-4.0",
                    "author": "Editor B",
                    "source": ["https://example.invalid/a", "https://example.invalid/aed2"],
                },
            }
        },
    )

    (root / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec1,100\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_lemmata_vega.tsv").write_text(
        "10\thttps://vega.invalid/10\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_wikidata.tsv").write_text(
        "Editor A\tQ1\nD1\tQ2\n",
        encoding="utf-8",
    )
    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\tRoot→Leaf A\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/ROOT">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1">Leaf A</a>\n'
        "oraec2\tRoot→Leaf B\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/ROOT">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T2">Leaf B</a>\n',
        encoding="utf-8",
    )
    return root


def test_preflight_accepts_resolvable_native_domains(tmp_path: Path) -> None:
    report = audit_schema_source(_fixture(tmp_path))

    assert report["ok"] is True
    assert report["counts"]["texts"] == 2
    assert report["counts"]["lemmas"] == 2
    assert report["counts"]["authors"] == 2
    assert report["counts"]["cv_ids"] == 2
    assert report["counts"]["hierarchy_rows"] == 2
    assert report["counts"]["external_rows"] == 4
    assert report["anomalies"] == {}


def test_preflight_resolves_corpus_level_readme_author_for_wikidata(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    (root / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec2.json | cc-by-sa-4.0 | "
        "Editor A, Editor B, Corpus Contributor | synthetic |\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_wikidata.tsv").write_text(
        "Corpus Contributor\tQ3\n",
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is True
    assert report["counts"]["credit_authors"] == 2
    assert report["counts"]["corpus_authors"] == 3
    assert report["counts"]["authors"] == 3
    assert report["anomalies"] == {}


def test_preflight_accepts_one_component_empty_hierarchy_label(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\t\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1"></a>\n'
        "oraec2\tRoot→Leaf B\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/ROOT">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T2">Leaf B</a>\n',
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is True
    assert report["counts"]["hierarchy_empty_labels"] == 1
    assert report["anomalies"] == {}


def test_preflight_rejects_ambiguous_wikidata_key_domain(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    payload["oraec2"]["material"] = [{"material": "Stone", "id": "D1"}]
    _write_json(root / "oraec2.json", payload)

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["ambiguous_wikidata_keys"] == [
        {"key": "D1", "domains": ["cv:date", "cv:material"]}
    ]


def test_preflight_rejects_unresolved_mapping_source_keys(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    (root / "mapping_oraec_lemmata_vega.tsv").write_text(
        "999\thttps://vega.invalid/999\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_wikidata.tsv").write_text(
        "Nobody\tQ99\n",
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["unresolved_vega_lemma_ids"] == ["999"]
    assert report["anomalies"]["unresolved_wikidata_keys"] == ["Nobody"]


def test_preflight_rejects_relations_that_tf_edges_would_collapse(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    payload = json.loads((root / "oraec1.json").read_text(encoding="utf-8"))
    payload["oraec1"]["date"] = [
        {"date": "Period A", "id": "D1"},
        {"date": "Period A", "id": "D1"},
    ]
    payload["oraec1"]["credits"]["source"] = [
        "https://example.invalid/a",
        "https://example.invalid/a",
    ]
    _write_json(root / "oraec1.json", payload)

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["edge_collapsing_duplicates"] == [
        {"text": "oraec1", "relation": "date", "target": "D1"},
        {
            "text": "oraec1",
            "relation": "source",
            "target": "https://example.invalid/a",
        },
    ]


def test_preflight_rejects_malformed_or_incomplete_hierarchy(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\tRoot→Leaf A\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/ROOT">Root</a>\n',
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["hierarchy_component_mismatches"] == [
        {"text": "oraec1", "labels": 2, "links": 1}
    ]
    assert report["anomalies"]["missing_hierarchy_texts"] == ["oraec2"]


def test_preflight_rejects_missing_text_mapping_source(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    (root / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec999,100\n",
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["unresolved_trismegistos_text_ids"] == ["oraec999"]


def test_preflight_rejects_lemma_identity_conflicts(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    payload["oraec2"]["sentences"][0]["token"][0]["lemmaID"] = "10"
    payload["oraec2"]["sentences"][0]["token"][0]["lemma_form"] = "different"
    _write_json(root / "oraec2.json", payload)

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["lemma_id_form_conflicts"] == [
        {"lemma_id": "10", "forms": ["a", "different"]}
    ]


def test_preflight_rejects_controlled_vocabulary_identity_conflicts(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    payload = json.loads((root / "oraec2.json").read_text(encoding="utf-8"))
    payload["oraec2"]["date"] = [{"date": "Different label", "id": "D1"}]
    _write_json(root / "oraec2.json", payload)

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["cv_id_label_conflicts"] == [
        {
            "kind": "date",
            "cv_id": "D1",
            "labels": ["Different label", "Period A"],
        }
    ]


def test_preflight_requires_readme_when_corpus_author_identity_is_in_schema(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    (root / "README.md").unlink()

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["missing_required_files"] == ["README.md"]


def test_preflight_rejects_duplicate_corpus_author_identity(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    (root / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec2.json | cc-by-sa-4.0 | "
        "Editor A, Editor A, Editor B | synthetic |\n",
        encoding="utf-8",
    )

    report = audit_schema_source(root)

    assert report["ok"] is False
    assert report["anomalies"]["duplicate_corpus_authors"] == ["Editor A"]
