"""Independent source/TF tests: real Fabric graph, no parser in audit implementation."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from oraec_tf.audit_graph import GraphConservationError, audit_basic_graph
from oraec_tf.ir import (
    ControlledValueIR,
    CorpusMetadataIR,
    CreditsIR,
    HierarchyComponentIR,
    HierarchyRowIR,
    MappingRowIR,
    MappingTableIR,
    SentenceIR,
    TextIR,
    TokenIR,
)
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _source(tmp_path: Path) -> tuple[Path, TextIR]:
    source = tmp_path / "raw"
    source.mkdir()
    original = {
        "oraec1": {
            "oraecid": "oraec1",
            "title": "Exact source title",
            "sentences": [
                {
                    "translation": "",
                    "token": [
                        {
                            "token": "oraec1-1-1",
                            "written_form": "nṯr",
                            "hiero": "[⯑]�",
                            "lineCount": " [Vs 1] ",
                            "pos": "N",
                        }
                    ],
                },
                {"translation": "No source words", "token": []},
            ],
            "credits": {
                "license": "cc-by-sa-4.0",
                "author": "Editor A",
                "source": ["https://example.invalid/source"],
            },
        }
    }
    (source / "oraec1.json").write_text(
        json.dumps(original, ensure_ascii=False), encoding="utf-8"
    )
    text = TextIR(
        oraec_id="oraec1",
        title="Exact source title",
        sentences=(
            SentenceIR(
                index=1,
                translation="",
                tokens=(
                    TokenIR(
                        token_id="oraec1-1-1",
                        written_form="nṯr",
                        hiero="[⯑]�",
                        line_count=" [Vs 1] ",
                        pos="N",
                    ),
                ),
            ),
            SentenceIR(index=2, translation="No source words", tokens=()),
        ),
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Editor A",
            sources=("https://example.invalid/source",),
        ),
    )
    return source, text


def test_independent_raw_source_vs_native_tf_round_trip(tmp_path: Path) -> None:
    source, text = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)

    report = audit_basic_graph(source, output)
    assert report["texts"] == 1
    assert report["sentences"] == 2
    assert report["tokens"] == 1
    assert report["anchors"] == 1


def test_independent_audit_rejects_silent_unicode_value_change(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    sentence = text.sentences[0]
    corrupted = replace(
        text,
        sentences=(
            replace(
                sentence,
                tokens=(replace(sentence.tokens[0], written_form="ntr"),),
            ),
            text.sentences[1],
        ),
    )
    output = tmp_path / "tf"
    write_tf((corrupted,), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match="written_form"):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_duplicate_raw_object_keys(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)
    path = source / "oraec1.json"
    original = path.read_text(encoding="utf-8")
    corrupted = original.replace(
        '"written_form": "nṯr"',
        '"written_form": "nṯr", "written_form": "changed"',
    )
    assert corrupted != original
    path.write_text(corrupted, encoding="utf-8")
    with pytest.raises(GraphConservationError, match="duplicate.*written_form"):
        audit_basic_graph(source, output)


def _relational_source(tmp_path: Path) -> tuple[Path, TextIR]:
    source, original = _source(tmp_path)
    path = source / "oraec1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload["oraec1"]
    raw["date"] = [{"id": "D1", "date": "Dynasty"}]
    raw["idno"] = ["Same", "Same"]
    raw["sentences"][0]["token"][0].update(
        {"lemmaID": "L1", "lemma_form": "nṯr"}
    )
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (source / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec13026.json | cc-by-sa-4.0 | "
        "Editor A, README Only | synthetic |\n",
        encoding="utf-8",
    )
    (source / "mapping_oraec_wikidata.tsv").write_text(
        "README Only\tQ42\n", encoding="utf-8"
    )
    sentence = original.sentences[0]
    adjusted = replace(
        original,
        dates=(ControlledValueIR(kind="date", cv_id="D1", label="Dynasty"),),
        idnos=("Same", "Same"),
        sentences=(
            replace(
                sentence,
                tokens=(
                    replace(sentence.tokens[0], lemma_id="L1", lemma_form="nṯr"),
                ),
            ),
            original.sentences[1],
        ),
    )
    return source, adjusted


def test_independent_relation_audit_accepts_native_links(tmp_path: Path) -> None:
    source, record = _relational_source(tmp_path)
    output = tmp_path / "tf"
    write_tf(
        (record,),
        output,
        source_revision=REVISION,
        corpus_metadata=CorpusMetadataIR(("Editor A", "README Only")),
        mapping_tables=(
            MappingTableIR(
                filename="mapping_oraec_wikidata.tsv",
                source_domain="author.author_name OR cv.cv_id",
                target_system="wikidata",
                release_included=True,
                rows=(MappingRowIR(source="README Only", target="Q42"),),
            ),
        ),
    )
    assert audit_basic_graph(source, output)["tokens"] == 1


def test_independent_relation_audit_detects_dropped_idno_occurrences(
    tmp_path: Path,
) -> None:
    source, record = _relational_source(tmp_path)
    output = tmp_path / "tf"
    write_tf((replace(record, idnos=()),), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match="idno"):
        audit_basic_graph(source, output)


def test_independent_relation_audit_rejects_invented_credit_from_readme(
    tmp_path: Path,
) -> None:
    source, record = _relational_source(tmp_path)
    output = tmp_path / "tf"
    write_tf((replace(record, credits=replace(record.credits, author="README Only")),),
             output, source_revision=REVISION,
             corpus_metadata=CorpusMetadataIR(("Editor A", "README Only")))
    with pytest.raises(GraphConservationError, match="author"):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_changed_wikidata_mapping(
    tmp_path: Path,
) -> None:
    source, record = _relational_source(tmp_path)
    output = tmp_path / "tf"
    write_tf(
        (record,),
        output,
        source_revision=REVISION,
        corpus_metadata=CorpusMetadataIR(("Editor A", "README Only")),
        mapping_tables=(
            MappingTableIR(
                filename="mapping_oraec_wikidata.tsv",
                source_domain="author.author_name OR cv.cv_id",
                target_system="wikidata",
                release_included=True,
                rows=(MappingRowIR(source="README Only", target="Q42"),),
            ),
        ),
    )
    (source / "mapping_oraec_wikidata.tsv").write_text(
        "README Only\tQ99\n", encoding="utf-8"
    )
    with pytest.raises(GraphConservationError, match="mapping|external|wikidata"):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_lost_readme_contributor_identity(
    tmp_path: Path,
) -> None:
    source, record = _relational_source(tmp_path)
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match="README|corpus author"):
        audit_basic_graph(source, output)


def _source_hierarchy(source: Path) -> tuple[HierarchyRowIR, ...]:
    root = HierarchyComponentIR(
        label="Root",
        tla_url="https://thesaurus-linguae-aegyptiae.de/object/R",
        tla_kind="object",
        tla_id="R",
    )
    leaf = HierarchyComponentIR(
        label="",
        tla_url="https://thesaurus-linguae-aegyptiae.de/text/T1",
        tla_kind="text",
        tla_id="T1",
    )
    (source / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\tRoot→\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/R">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1"></a>\n',
        encoding="utf-8",
    )
    return (HierarchyRowIR(oraec_id="oraec1", components=(root, leaf)),)


def test_independent_audit_checks_exact_empty_hierarchy_label(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    hierarchy = _source_hierarchy(source)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION, hierarchy_rows=hierarchy)
    assert audit_basic_graph(source, output)["sentences"] == 2


def test_independent_audit_rejects_unparsed_linked_hierarchy_suffix(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    hierarchy = _source_hierarchy(source)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION, hierarchy_rows=hierarchy)
    path = source / "oraec_hierarchical_path.tsv"
    path.write_text(
        path.read_text(encoding="utf-8").replace("</a>\n", "</a>GARBAGE\n"),
        encoding="utf-8",
    )
    with pytest.raises(GraphConservationError, match="hierarchy|linked"):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_dropped_hierarchy_component(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    _source_hierarchy(source)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match="hierarchy"):
        audit_basic_graph(source, output)
