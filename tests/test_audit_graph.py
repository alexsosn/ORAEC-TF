"""Independent source/TF tests: real Fabric graph, no parser in audit implementation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from oraec_tf.audit_graph import (
    GraphConservationError,
    audit_basic_graph,
    audit_graph_with_provenance,
)
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


def test_independent_audit_rejects_unmodeled_new_raw_token_field(
    tmp_path: Path,
) -> None:
    source, record = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION)
    path = source / "oraec1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["oraec1"]["sentences"][0]["token"][0]["newSourceAnnotation"] = "lost"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(GraphConservationError, match="unmodeled|unknown"):
        audit_basic_graph(source, output)


def test_audit_report_hashes_generated_tf_without_semantic_sidecars(
    tmp_path: Path,
) -> None:
    source, record = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION)
    report = audit_graph_with_provenance(
        source, output,
        source_revision=REVISION,
        converter_revision="a" * 40,
        schema_version=1,
    )
    assert report["ok"] is True
    assert report["source_revision"] == REVISION
    assert report["converter_revision"] == "a" * 40
    assert report["schema_version"] == 1
    assert report["counts"]["tokens"] == 1
    assert report["tf_version"]
    assert report["output_sha256"]["otype.tf"] == hashlib.sha256(
        (output / "otype.tf").read_bytes()
    ).hexdigest()
    assert report["output_bytes"]["otype.tf"] == (output / "otype.tf").stat().st_size
    assert report["total_tf_bytes"] == sum(
        path.stat().st_size for path in output.glob("*.tf") if path.is_file()
    )
    assert all(path.endswith(".tf") for path in report["output_sha256"])


@pytest.mark.parametrize("field", ["bibliography", "condition"])
def test_independent_audit_rejects_fabricated_optional_text_values(
    tmp_path: Path, field: str
) -> None:
    """An absent source annotation must not acquire an invented TF value."""
    source, text = _source(tmp_path)
    if field == "bibliography":
        fabricated = replace(text, bibliography="invented bibliography")
    else:
        fabricated = replace(text, condition="invented condition")
    output = tmp_path / "tf"
    write_tf((fabricated,), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match=field):
        audit_basic_graph(source, output)


@pytest.mark.parametrize("location", ["record", "sentence", "credits"])
def test_independent_audit_rejects_new_source_object_fields(
    tmp_path: Path, location: str,
) -> None:
    source, text = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)
    path = source / "oraec1.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    record = raw["oraec1"]
    if location == "record":
        target = record
    elif location == "sentence":
        target = record["sentences"][0]
    else:
        target = record["credits"]
    target["previouslyUnknownField"] = "unrepresented"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(GraphConservationError, match="unknown|unmodeled"):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_mismatched_embedded_record_id(
    tmp_path: Path,
) -> None:
    source, text = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)
    path = source / "oraec1.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["oraec1"]["oraecid"] = "oraec999"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(GraphConservationError, match="oraecid|identity"):
        audit_basic_graph(source, output)


@pytest.mark.parametrize(
    ("field", "wrong"),
    [("tla_id", "WRONG"), ("tla_kind", "text")],
)
def test_audit_detects_incorrect_hierarchy_tla_metadata(
    tmp_path: Path, field: str, wrong: str,
) -> None:
    """A corrupted native hierarchy node must fail against raw linked TLA URLs."""
    source, text = _source(tmp_path)
    original = _source_hierarchy(source)
    first = original[0].components[0]
    broken = replace(original[0], components=(
        replace(first, **{field: wrong}), *original[0].components[1:],
    ))
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION, hierarchy_rows=(broken,))
    with pytest.raises(GraphConservationError, match=field):
        audit_basic_graph(source, output)


def test_independent_audit_rejects_invented_extra_author(
    tmp_path: Path,
) -> None:
    # No README-level contributors exist in this fixture. This extra author
    # must not be accepted merely because a TF node claims corpus-wide scope.
    source, record = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf(
        (record,), output, source_revision=REVISION,
        corpus_metadata=CorpusMetadataIR(("Invented third contributor",)),
    )
    with pytest.raises(GraphConservationError, match="author|invented"):
        audit_basic_graph(source, output)


@pytest.mark.parametrize("feature", ["hierarchy_id", "hierarchy_depth"])
def test_audit_rejects_corrupted_derived_hierarchy_feature(
    tmp_path: Path, feature: str,
) -> None:
    """Mutate real generated TF bytes; verify independent source-derived metadata."""
    source, record = _source(tmp_path)
    hierarchy = _source_hierarchy(source)
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION, hierarchy_rows=hierarchy)

    file_path = output / f"{feature}.tf"
    original = file_path.read_text(encoding="utf-8")
    if feature == "hierarchy_id":
        assert "oraec-hierarchy:path-prefix:" in original
        corrupted = original.replace(
            "oraec-hierarchy:path-prefix:", "wrong-hierarchy:path-prefix:", 1
        )
    else:
        lines = original.splitlines(keepends=True)
        for line_no, line in enumerate(lines):
            if line.startswith("@") or not line.strip() or "\t" not in line:
                continue
            node, value = line.split("\t", 1)
            if not node.isdigit() or not value.strip().isdigit():
                continue
            lines[line_no] = f"{node}\t9999\n"
            break
        corrupted = "".join(lines)
    assert corrupted != original, "mutation must modify generated TF data"
    file_path.write_text(corrupted, encoding="utf-8")
    with pytest.raises(GraphConservationError, match=feature):
        audit_basic_graph(source, output)


def test_full_source_audit_rejects_missing_companion_semantic_files(
    tmp_path: Path,
) -> None:
    source, record = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION)
    with pytest.raises(GraphConservationError, match="required.*source"):
        audit_basic_graph(source, output, require_complete_source=True)


@pytest.mark.parametrize(
    "node_type",
    ["author", "source_ref", "idno", "cv", "hierarchy", "external_ref"],
)
def test_independent_audit_rejects_corrupt_native_entity_oslots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_type: str,
) -> None:
    """Real Fabric graph with a deliberately corrupted native entity span.

    The independent auditor must not trust oslots on shared native entities
    merely because their source labels and mapping edges remain intact.
    """
    from tf.fabric import Fabric

    import oraec_tf.audit_graph as audit_module

    source, record = _relational_source(tmp_path)
    hierarchy = _source_hierarchy(source)
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
        hierarchy_rows=hierarchy,
    )
    # Positive control: the unmodified real graph must be conserved.
    assert audit_basic_graph(source, output)["tokens"] == 1
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    nodes = tuple(api.F.otype.s(node_type))
    assert nodes
    target = nodes[0]
    original_descend = api.L.d
    assert original_descend(target, otype="word")

    def corrupt_descend(node: int, otype: str | None = None) -> object:
        if node == target and otype == "word":
            return ()
        return original_descend(node, otype=otype)

    monkeypatch.setattr(api.L, "d", corrupt_descend)

    class CorruptedFabric:
        def __init__(self, **kwargs: object) -> None:
            pass

        def loadAll(self, **kwargs: object) -> object:
            return api

    monkeypatch.setattr(audit_module, "Fabric", CorruptedFabric)
    with pytest.raises(GraphConservationError, match="oslots"):
        audit_basic_graph(source, output)


def test_auditor_independently_reconstructs_crlf_and_cr_on_native_nodes(
    tmp_path: Path,
) -> None:
    """Schema v2 audit must decode TF native offsets without writer helpers."""
    source, record = _source(tmp_path)
    raw_file = source / "oraec1.json"
    raw = json.loads(raw_file.read_text(encoding="utf-8"))
    source_bib = "Editionen:\r\n- Wreszinski\r\n- Berlin\rTail"
    source_translation = "Line\r\ntranslated"
    source_word = "n\rṯr"
    raw_record = raw["oraec1"]
    raw_record["bibliography"] = source_bib
    raw_record["sentences"][0]["translation"] = source_translation
    raw_record["sentences"][0]["token"][0]["written_form"] = source_word
    raw_file.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    original_sentence = record.sentences[0]
    token = original_sentence.tokens[0]
    converted = replace(
        record,
        bibliography=source_bib,
        sentences=(
            replace(
                original_sentence,
                translation=source_translation,
                tokens=(replace(token, written_form=source_word),),
            ),
            record.sentences[1],
        ),
    )
    output = tmp_path / "tf"
    write_tf((converted,), output, source_revision=REVISION)
    assert audit_basic_graph(source, output) == {
        "texts": 1, "sentences": 2, "tokens": 1, "anchors": 1,
    }


def test_auditor_rejects_tampered_native_cr_position_metadata(
    tmp_path: Path,
) -> None:
    source, record = _source(tmp_path)
    raw_file = source / "oraec1.json"
    raw = json.loads(raw_file.read_text(encoding="utf-8"))
    raw["oraec1"]["bibliography"] = "A\r\nB"
    raw_file.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "tf"
    write_tf((replace(record, bibliography="A\r\nB"),), output,
             source_revision=REVISION)
    positions = output / "text_cr_offsets.tf"
    payload = positions.read_text(encoding="utf-8")
    assert "bibliography=1" in payload
    positions.write_text(
        payload.replace("bibliography=1", "bibliography=999"),
        encoding="utf-8",
    )
    with pytest.raises(GraphConservationError, match="CR|offset|position"):
        audit_basic_graph(source, output)


@pytest.mark.parametrize(
    "feature,forgery",
    [
        ("written_form", "invented-word"),
        ("hiero", "𓀀"),
        ("pos", "substantive"),
        ("line_count", "[Vs 99]"),
        ("trailer", "invented spacing"),
    ],
)
def test_independent_auditor_rejects_any_forged_anchor_annotation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    feature: str, forgery: str,
) -> None:
    """#20: fabricated linguistic/spacing data must not enter empty sentences."""
    from tf.fabric import Fabric

    from oraec_tf import audit_graph as audit_module

    source, original = _source(tmp_path)
    output = tmp_path / "tf"
    write_tf((original,), output, source_revision=REVISION)
    assert audit_basic_graph(source, output)["anchors"] == 1

    # Mutate the *loaded real Fabric feature data*, not an invented mock
    # writer/parser object, while preserving all valid source relations.
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    anchor = next(
        word for word in api.F.otype.s("word")
        if api.F.is_anchor.v(word) == 1
    )
    accessor = getattr(api.F, feature)
    accessor.data[anchor] = forgery

    class CorruptedFabric:
        def __init__(self, **kwargs: object) -> None:
            pass

        def loadAll(self, **kwargs: object) -> object:
            return api

    monkeypatch.setattr(audit_module, "Fabric", CorruptedFabric)
    with pytest.raises(GraphConservationError, match=feature):
        audit_basic_graph(source, output)



@pytest.mark.parametrize(
    "counts",
    [
        {"present": 267041, "placeholder": 13198, "replacement": 6545},
        {"present": 267042, "placeholder": 13197, "replacement": 6545},
        {"present": 267042, "placeholder": 13198, "replacement": 6544},
        {"present": 267043, "placeholder": 13198, "replacement": 6545},
    ],
)
def test_independent_pinned_hiero_census_rejects_changed_source_coverage(
    counts: dict[str, int],
) -> None:
    """#21: pinned source preservation includes omission/uncertainty statistics."""
    from oraec_tf.audit_graph import _validate_hiero_counts

    with pytest.raises(GraphConservationError, match="hiero|placeholder|replacement"):
        _validate_hiero_counts(counts)


def test_independent_pinned_hiero_census_accepts_exact_source_counts() -> None:
    from oraec_tf.audit_graph import _validate_hiero_counts

    _validate_hiero_counts(
        {"present": 267042, "placeholder": 13198, "replacement": 6545}
    )
