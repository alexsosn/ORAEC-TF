"""RED-first Text-Fabric round-trip tests for issue #6, not test doubles."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tf.fabric import Fabric

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
from oraec_tf.writer import WriterError, write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _texts() -> tuple[TextIR, ...]:
    return (
        TextIR(
            oraec_id="oraec1",
            title="First source text",
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
                SentenceIR(index=2, translation="", tokens=()),
            ),
            credits=CreditsIR(
                license="cc-by-sa-4.0",
                author="Credited A",
                sources=("https://example.invalid/source",),
            ),
        ),
        TextIR(
            oraec_id="oraec2",
            title="Second source text",
            sentences=(
                SentenceIR(
                    index=1,
                    translation="Different translation",
                    tokens=(
                        TokenIR(
                            token_id="oraec2-1-1",
                            written_form="ḫpr",
                            line_count="0",
                        ),
                    ),
                ),
            ),
            credits=CreditsIR(
                license="cc-by-sa-4.0",
                author="Credited B",
                sources=("https://example.invalid/source",),
            ),
        ),
    )


def test_write_tf_preserves_word_sentence_text_and_technical_anchor(tmp_path: Path) -> None:
    output = tmp_path / "tf"
    write_tf(_texts(), output, source_revision=REVISION)

    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id title license sentence_index translation "
        "token_id written_form hiero line_count pos is_anchor trailer",
        silent="deep",
    )

    words = api.F.otype.s("word")
    sentences = api.F.otype.s("sentence")
    texts = api.F.otype.s("text")
    assert len(words) == 3  # two source tokens + exactly one technical anchor
    assert len(sentences) == 3
    assert len(texts) == 2

    source_tokens = [w for w in words if api.F.token_id.v(w) is not None]
    anchors = [w for w in words if api.F.is_anchor.v(w) == 1]
    assert len(source_tokens) == 2
    assert len(anchors) == 1
    assert api.F.token_id.v(anchors[0]) is None
    assert api.F.written_form.v(anchors[0]) is None
    assert api.F.trailer.v(anchors[0]) == ""

    first_word = source_tokens[0]
    assert api.F.token_id.v(first_word) == "oraec1-1-1"
    assert api.F.written_form.v(first_word) == "nṯr"
    assert api.F.hiero.v(first_word) == "[⯑]�"
    assert api.F.line_count.v(first_word) == " [Vs 1] "
    assert api.F.pos.v(first_word) == "N"

    first_text = next(n for n in texts if api.F.oraec_id.v(n) == "oraec1")
    first_sentences = api.L.d(first_text, otype="sentence")
    assert len(first_sentences) == 2
    assert [api.F.sentence_index.v(n) for n in first_sentences] == [1, 2]
    assert api.F.translation.v(first_sentences[0]) == ""
    assert api.F.translation.v(first_sentences[1]) == ""
    assert api.L.d(first_sentences[1], otype="word") == tuple(anchors)
    assert api.F.title.v(first_text) == "First source text"
    assert api.F.license.v(first_text) == "cc-by-sa-4.0"


def test_write_tf_retains_missingness_without_sentinel(tmp_path: Path) -> None:
    output = tmp_path / "tf"
    write_tf(_texts(), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").load(
        "token_id hiero line_count pos is_anchor written_form",
        silent="deep",
    )
    second_word = next(
        n for n in api.F.otype.s("word")
        if api.F.token_id.v(n) == "oraec2-1-1"
    )
    assert api.F.hiero.v(second_word) is None
    assert api.F.pos.v(second_word) is None
    assert api.F.line_count.v(second_word) == "0"


def test_walker_metadata_uses_int_features_not_value_type_override() -> None:
    from oraec_tf.writer import _feature_metadata

    metadata = _feature_metadata({"written_form", "sentence_index", "trailer"})
    assert set(metadata) == {"written_form", "sentence_index", "trailer"}
    assert all("valueType" not in fields for fields in metadata.values())
    assert metadata["written_form"]["sourceField"] == "token.written_form"
    assert metadata["sentence_index"]["origin"] == "derived"


def test_write_tf_preserves_shared_entities_and_occurrence_relations(
    tmp_path: Path,
) -> None:
    a, b = _texts()
    first_sentence = a.sentences[0]
    first_token = first_sentence.tokens[0]
    second_sentence = b.sentences[0]
    second_token = second_sentence.tokens[0]
    a = replace(
        a,
        sentences=(
            replace(
                first_sentence,
                tokens=(replace(first_token, lemma_id="L1", lemma_form="nṯr"),),
            ),
            a.sentences[1],
        ),
        dates=(ControlledValueIR(kind="date", cv_id="D1", label="Dynasty"),),
        idnos=("Duplicate", "Duplicate"),
    )
    b = replace(
        b,
        sentences=(
            replace(
                second_sentence,
                tokens=(replace(second_token, lemma_id="L1", lemma_form="nṯr"),),
            ),
        ),
        dates=(ControlledValueIR(kind="date", cv_id="D1", label="Dynasty"),),
    )
    tables = (
        MappingTableIR(
            filename="mapping_oraec_wikidata.tsv",
            source_domain="author.author_name OR cv.cv_id",
            target_system="wikidata",
            release_included=True,
            rows=(MappingRowIR(source="README Only", target="Q42"),),
        ),
        MappingTableIR(
            filename="mapping_oraec_karnak.tsv",
            source_domain="text.oraec_id",
            target_system="karnak",
            release_included=False,
            rows=(MappingRowIR(source="oraec1", target="https://karnak.invalid/1"),),
        ),
    )
    output = tmp_path / "tf"
    write_tf(
        (a, b),
        output,
        source_revision=REVISION,
        corpus_metadata=CorpusMetadataIR(corpus_authors=("Credited A", "README Only")),
        mapping_tables=tables,
    )

    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id token_id lemma_id lemma_form cv_kind cv_id cv_label "
        "author_name is_corpus_author corpus_author_index source_url "
        "idno_value idno_index external_system external_value "
        "date author source idno external",
        silent="deep",
    )
    texts = {api.F.oraec_id.v(t): t for t in api.F.otype.s("text")}
    assert len(api.F.otype.s("lex")) == 1
    lex = api.F.otype.s("lex")[0]
    assert api.F.lemma_id.v(lex) == "L1"
    assert api.F.lemma_form.v(lex) == "nṯr"
    assert {
        api.F.token_id.v(w) for w in api.L.d(lex, otype="word")
    } == {"oraec1-1-1", "oraec2-1-1"}

    assert len(api.F.otype.s("cv")) == 1
    cv = api.F.otype.s("cv")[0]
    assert (api.F.cv_kind.v(cv), api.F.cv_id.v(cv), api.F.cv_label.v(cv)) == (
        "date", "D1", "Dynasty",
    )
    assert dict(api.E.date.f(texts["oraec1"])) == {cv: 1}
    assert dict(api.E.date.f(texts["oraec2"])) == {cv: 1}

    idnos = tuple(api.E.idno.f(texts["oraec1"]))
    assert len(idnos) == 2
    assert [(api.F.idno_index.v(n), api.F.idno_value.v(n)) for n in
            sorted(idnos, key=lambda n: api.F.idno_index.v(n))] == [
        (1, "Duplicate"), (2, "Duplicate")
    ]

    authors = {
        api.F.author_name.v(n): n for n in api.F.otype.s("author")
    }
    assert "README Only" in authors
    assert api.F.is_corpus_author.v(authors["README Only"]) == 1
    assert api.F.corpus_author_index.v(authors["README Only"]) == 2
    assert set(api.E.author.f(texts["oraec1"])) == {authors["Credited A"]}
    assert set(api.E.author.f(texts["oraec2"])) == {authors["Credited B"]}
    assert authors["README Only"] not in set(api.E.author.f(texts["oraec1"]))

    assert len(api.F.otype.s("source_ref")) == 1
    src = api.F.otype.s("source_ref")[0]
    assert api.F.source_url.v(src) == "https://example.invalid/source"
    assert dict(api.E.source.f(texts["oraec1"])) == {src: 1}
    assert dict(api.E.source.f(texts["oraec2"])) == {src: 1}

    targets = tuple(dict(api.E.external.f(authors["README Only"])))
    assert len(targets) == 1
    target = targets[0]
    assert (api.F.external_system.v(target), api.F.external_value.v(target)) == (
        "wikidata", "Q42",
    )
    assert dict(api.E.external.f(authors["README Only"]))[target] == (
        "mapping_oraec_wikidata.tsv"
    )
    assert all(
        api.F.external_system.v(n) != "karnak"
        for n in api.F.otype.s("external_ref")
    )


def test_write_tf_preserves_hierarchy_occurrences_and_empty_labels(
    tmp_path: Path,
) -> None:
    root = HierarchyComponentIR(
        label="Root",
        tla_url="https://thesaurus-linguae-aegyptiae.de/object/R",
        tla_kind="object",
        tla_id="R",
    )
    empty_leaf = HierarchyComponentIR(
        label="",
        tla_url="https://thesaurus-linguae-aegyptiae.de/text/T1",
        tla_kind="text",
        tla_id="T1",
    )
    other_leaf = HierarchyComponentIR(
        label="Leaf",
        tla_url="https://thesaurus-linguae-aegyptiae.de/text/T2",
        tla_kind="text",
        tla_id="T2",
    )
    hierarchy = (
        HierarchyRowIR(oraec_id="oraec1", components=(root, empty_leaf)),
        HierarchyRowIR(oraec_id="oraec2", components=(root, other_leaf)),
    )
    output = tmp_path / "tf"
    write_tf(_texts(), output, source_revision=REVISION, hierarchy_rows=hierarchy)

    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id hierarchy_id hierarchy_label hierarchy_depth "
        "tla_url tla_kind tla_id hierarchy parent",
        silent="deep",
    )
    assert len(api.F.otype.s("hierarchy")) == 3
    texts = {api.F.oraec_id.v(t): t for t in api.F.otype.s("text")}
    first_leaf = next(iter(api.E.hierarchy.f(texts["oraec1"])))
    second_leaf = next(iter(api.E.hierarchy.f(texts["oraec2"])))
    assert first_leaf != second_leaf
    assert api.F.hierarchy_label.v(first_leaf) == ""
    assert api.F.hierarchy_label.v(second_leaf) == "Leaf"
    assert api.F.tla_url.v(first_leaf).endswith("/text/T1")
    assert api.F.tla_kind.v(first_leaf) == "text"
    assert api.F.tla_id.v(first_leaf) == "T1"
    assert api.F.hierarchy_depth.v(first_leaf) == 2
    parents = tuple(api.E.parent.f(first_leaf))
    assert len(parents) == 1
    assert parents == tuple(api.E.parent.f(second_leaf))
    assert api.F.hierarchy_label.v(parents[0]) == "Root"
    assert api.F.hierarchy_depth.v(parents[0]) == 1
    assert api.F.hierarchy_id.v(first_leaf).startswith("oraec-hierarchy:path-prefix:")


def test_write_tf_rejects_incomplete_hierarchy_rows(tmp_path: Path) -> None:
    partial = (
        HierarchyRowIR(
            oraec_id="oraec1",
            components=(
                HierarchyComponentIR(
                    label="A",
                    tla_url="https://thesaurus-linguae-aegyptiae.de/text/T1",
                    tla_kind="text",
                    tla_id="T1",
                ),
            ),
        ),
    )
    with pytest.raises(WriterError, match="hierarchy"):
        write_tf(
            _texts(),
            tmp_path / "tf",
            source_revision=REVISION,
            hierarchy_rows=partial,
        )


def test_multitext_bibliography_is_attached_to_correct_oraec_identity(
    tmp_path: Path,
) -> None:
    """#40: sparse, multiline bibliographies must never move between texts."""
    first, second = _texts()
    # Lexicographic filenames and iteration order deliberately disagree;
    # several metadata features are missing and one value begins with newline.
    text_10 = replace(
        second,
        oraec_id="oraec10",
        title="Balsamierungsritual",
        bibliography=(
            "- A. Mariette, Les Papyrus égyptiens du Musée Boulaq.\n"
            "- Rituel de l&#039;embaumement."
        ),
        sentences=(
            replace(
                second.sentences[0],
                tokens=(
                    replace(second.sentences[0].tokens[0], token_id="oraec10-1-1"),
                ),
            ),
        ),
    )
    text_100 = replace(
        first,
        oraec_id="oraec100",
        title="Papyrus Berlin",
        bibliography="\n- http://www.medizinische-papyri.de/PapyrusBerlin3038/",
        sentences=(
            replace(
                first.sentences[0],
                tokens=(
                    replace(first.sentences[0].tokens[0], token_id="oraec100-1-1"),
                ),
            ),
            first.sentences[1],
        ),
    )
    text_2 = replace(
        first,
        oraec_id="oraec2",
        title="No bibliography",
        bibliography=None,
        sentences=(
            replace(
                first.sentences[0],
                tokens=(replace(first.sentences[0].tokens[0], token_id="oraec2-1-1"),),
            ),
            first.sentences[1],
        ),
    )
    records = (text_10, text_2, text_100)
    destination = tmp_path / "tf"
    write_tf(records, destination, source_revision=REVISION)

    api = Fabric(locations=str(destination), silent="deep").load(
        "oraec_id title bibliography token_id",
        silent="deep",
    )
    actual = {
        api.F.oraec_id.v(t): (
            api.F.title.v(t),
            api.F.bibliography.v(t),
        )
        for t in api.F.otype.s("text")
    }
    assert actual == {
        item.oraec_id: (item.title, item.bibliography) for item in records
    }


def test_carriage_return_is_losslessly_reconstructible_from_native_tf(
    tmp_path: Path,
) -> None:
    """#40: preserve literal CRLF and CR despite Text-Fabric transport limits."""
    from oraec_tf.text_codec import restore_source_string

    first, second = _texts()
    raw = "Editionen:\r\n- Papyrus Berlin\r\n- Other\r\rOriginal\nEnd"
    first = replace(first, bibliography=raw)
    second = replace(second, bibliography="ordinary\ntext")
    output = tmp_path / "tf"
    write_tf((first, second), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id bibliography text_cr_offsets",
        silent="deep",
    )
    texts = {api.F.oraec_id.v(n): n for n in api.F.otype.s("text")}
    a = texts[first.oraec_id]
    b = texts[second.oraec_id]
    assert api.F.bibliography.v(a) == raw.replace("\r", "")
    assert restore_source_string(
        api.F.bibliography.v(a), api.F.text_cr_offsets.v(a), "bibliography"
    ) == raw
    assert api.F.bibliography.v(b) == second.bibliography
    assert api.F.text_cr_offsets.v(b) is None


def test_carriage_return_transport_covers_word_sentence_and_shared_lex_cv(
    tmp_path: Path,
) -> None:
    """CR in any text-bearing node must not shift sparse native TF features."""
    from oraec_tf.text_codec import restore_source_string

    first, second = _texts()
    original_sentence = first.sentences[0]
    original_token = original_sentence.tokens[0]
    first = replace(
        first,
        title="Ti\rtle",
        sentences=(
            replace(
                original_sentence,
                translation="First\r\ntranslation",
                tokens=(
                    replace(
                        original_token,
                        written_form="n\rṯr",
                        lemma_id="L-CR",
                        lemma_form="lex\r-form",
                    ),
                ),
            ),
            first.sentences[1],
        ),
        dates=(ControlledValueIR(kind="date", cv_id="D1", label="Era\rlabel"),),
    )
    output = tmp_path / "tf"
    write_tf((first, second), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id title text_cr_offsets translation sentence_cr_offsets "
        "token_id written_form word_cr_offsets lemma_id lemma_form lex_cr_offsets "
        "cv_id cv_label cv_cr_offsets",
        silent="deep",
    )
    text_node = next(
        n for n in api.F.otype.s("text") if api.F.oraec_id.v(n) == "oraec1"
    )
    sentence_node = api.L.d(text_node, otype="sentence")[0]
    word = api.L.d(sentence_node, otype="word")[0]
    lex = next(n for n in api.F.otype.s("lex") if api.F.lemma_id.v(n) == "L-CR")
    cv = next(n for n in api.F.otype.s("cv") if api.F.cv_id.v(n) == "D1")
    for node, name, meta, original in (
        (text_node, "title", "text_cr_offsets", "Ti\rtle"),
        (sentence_node, "translation", "sentence_cr_offsets", "First\r\ntranslation"),
        (word, "written_form", "word_cr_offsets", "n\rṯr"),
        (lex, "lemma_form", "lex_cr_offsets", "lex\r-form"),
        (cv, "cv_label", "cv_cr_offsets", "Era\rlabel"),
    ):
        assert restore_source_string(
            getattr(api.F, name).v(node),
            getattr(api.F, meta).v(node),
            name,
        ) == original


def test_schema_v2_documents_sparse_carriage_return_features() -> None:
    import json

    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schema" / "core.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["schemaVersion"] == 2
    assert schema["source"]["semanticSidecars"] is False
    for node_type, spec in schema["nodeTypes"].items():
        metadata = spec["features"][f"{node_type}_cr_offsets"]
        assert metadata["valueType"] == "str"
        assert metadata["origin"] == "derived"
    assert schema["controlCharacterTransport"]["rawStringRoundTrip"] is True


def test_control_transport_contract_is_declared_in_native_tf_metadata(
    tmp_path: Path,
) -> None:
    first, second = _texts()
    first = replace(first, bibliography="A\r\nB")
    output = tmp_path / "tf"
    write_tf((first, second), output, source_revision=REVISION)
    text_feature = (output / "bibliography.tf").read_text(encoding="utf-8")
    assert "@schemaVersion=2" in text_feature
    assert "@controlCharacterTransport=cr-offsets-v1" in text_feature
