from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "core.json"
ADR = ROOT / "docs" / "adr" / "0005-native-tf-schema.md"

RECORD_FIELDS = {
    "bibliography", "condition", "credits", "date", "idno", "location",
    "material", "objecttype", "oraecid", "origplace", "sentences", "title",
}
SENTENCE_FIELDS = {"token", "translation"}
CREDITS_FIELDS = {"author", "license", "source"}
TOKEN_FIELDS = {
    "adjective", "adverb", "cotext_translation", "epitheton", "genus", "hiero",
    "inflection", "lemmaID", "lemma_form", "lineCount", "morphology", "name",
    "number", "numerus", "particle", "pos", "pronoun", "status", "token",
    "verbalClass", "voice", "written_form",
}
NODE_TYPES = {
    "word", "sentence", "text", "lex", "cv", "author", "source_ref",
    "idno", "hierarchy", "external_ref",
}
EDGE_FEATURES = {
    "date", "origplace", "objecttype", "location", "material", "author",
    "source", "idno", "hierarchy", "parent", "external",
}


def _schema() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_schema_covers_the_complete_audited_source_contract() -> None:
    schema = _schema()
    fields = schema["source"]["fields"]

    assert set(fields["record"]) == RECORD_FIELDS
    assert set(fields["sentence"]) == SENTENCE_FIELDS
    assert set(fields["credits"]) == CREDITS_FIELDS
    assert set(fields["token"]) == TOKEN_FIELDS

    coverage = schema["sourceCoverage"]
    assert set(coverage["record"]) == RECORD_FIELDS
    assert set(coverage["sentence"]) == SENTENCE_FIELDS
    assert set(coverage["credits"]) == CREDITS_FIELDS
    assert set(coverage["token"]) == TOKEN_FIELDS

    assert schema["source"]["semanticSidecars"] is False
    assert schema["source"]["corpusMetadata"] == {
        "authors": "README licence-table author column for oraec1.json .. oraec13026.json"
    }
    assert schema["sourceCoverage"]["corpusMetadata"] == {
        "authors": "author nodes + author.is_corpus_author + author.corpus_author_index"
    }
    assert schema["source"]["revision"] == (
        "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"
    )


def test_slot_and_native_node_types_are_frozen() -> None:
    schema = _schema()

    assert schema["slotType"] == "word"
    assert set(schema["nodeTypes"]) == NODE_TYPES
    assert "line" not in schema["nodeTypes"]

    word = schema["nodeTypes"]["word"]
    assert word["sourceIdentity"] == "token_id"
    assert word["features"]["is_anchor"]["origin"] == "derived"
    assert word["features"]["is_anchor"]["valueType"] == "int"
    assert word["features"]["trailer"]["origin"] == "derived"

    sentence = schema["nodeTypes"]["sentence"]
    assert sentence["sourceIdentity"] == "oraec_id+sentence_index"
    assert sentence["features"]["translation"]["supportsEmptyString"] is True

    lex = schema["nodeTypes"]["lex"]
    assert lex["sourceIdentity"] == "lemma_id"
    assert lex["features"]["lemma_id"]["sourceField"] == "token.lemmaID"
    assert lex["features"]["lemma_form"]["sourceField"] == "token.lemma_form"
    assert lex["oslots"] == "union_of_occurrence_words"


def test_source_token_features_are_lossless_and_lemma_is_normalized() -> None:
    schema = _schema()
    word_features = schema["nodeTypes"]["word"]["features"]

    assert word_features["token_id"]["sourceField"] == "token.token"
    assert word_features["written_form"]["sourceField"] == "token.written_form"
    assert word_features["cotext_translation"]["sourceField"] == "token.cotext_translation"
    assert word_features["hiero"]["sourceField"] == "token.hiero"
    assert word_features["hiero"]["exact"] is True
    assert word_features["line_count"]["sourceField"] == "token.lineCount"
    assert word_features["line_count"]["exact"] is True
    assert "lemma_id" not in word_features
    assert "lemma_form" not in word_features

    grammar_sources = {
        spec["sourceField"]
        for spec in word_features.values()
        if spec.get("origin") == "source"
    }
    grammar_sources |= {
        schema["nodeTypes"]["lex"]["features"]["lemma_id"]["sourceField"],
        schema["nodeTypes"]["lex"]["features"]["lemma_form"]["sourceField"],
    }
    assert grammar_sources == {f"token.{field}" for field in TOKEN_FIELDS}


def test_multivalued_metadata_is_relational_not_packed() -> None:
    schema = _schema()
    assert set(schema["edgeFeatures"]) == EDGE_FEATURES

    for kind in ("date", "origplace", "objecttype", "location", "material"):
        edge = schema["edgeFeatures"][kind]
        assert edge["from"] == ["text"]
        assert edge["to"] == ["cv"]
        assert edge["valueType"] == "int"
        assert edge["valueSemantics"] == "source_list_ordinal"
        assert edge["targetConstraint"] == {"cv_kind": kind}

    cv = schema["nodeTypes"]["cv"]
    assert cv["sourceIdentity"] == "cv_kind+cv_id"
    assert cv["features"]["cv_id"]["origin"] == "source"
    assert cv["features"]["cv_label"]["origin"] == "source"

    idno = schema["nodeTypes"]["idno"]
    assert idno["sourceIdentity"] == "oraec_id+idno_index"
    assert idno["features"]["idno_index"]["origin"] == "derived"
    assert idno["preservesDuplicateOccurrences"] is True


def test_credits_hierarchy_and_external_mappings_are_native() -> None:
    schema = _schema()

    author = schema["nodeTypes"]["author"]
    assert author["sourceIdentity"] == "author_name"
    assert author["sourceIdentitySources"] == [
        "credits.author",
        "README corpus author column",
    ]
    assert author["features"]["is_corpus_author"]["origin"] == "source"
    assert author["features"]["is_corpus_author"]["valueType"] == "int"
    assert author["features"]["corpus_author_index"]["origin"] == "derived"
    assert author["features"]["corpus_author_index"]["valueType"] == "int"
    assert schema["nodeTypes"]["source_ref"]["sourceIdentity"] == "source_url"

    hierarchy = schema["nodeTypes"]["hierarchy"]
    assert hierarchy["sourceIdentity"] == "exact_path_prefix"
    assert hierarchy["features"]["hierarchy_label"]["supportsEmptyString"] is True
    assert hierarchy["features"]["tla_url"]["origin"] == "source"
    assert hierarchy["features"]["tla_id"]["origin"] == "derived"
    assert schema["edgeFeatures"]["parent"]["from"] == ["hierarchy"]
    assert schema["edgeFeatures"]["parent"]["to"] == ["hierarchy"]
    assert schema["edgeFeatures"]["hierarchy"]["from"] == ["text"]
    assert schema["edgeFeatures"]["hierarchy"]["to"] == ["hierarchy"]

    external = schema["edgeFeatures"]["external"]
    assert set(external["from"]) == {"text", "lex", "cv", "author"}
    assert external["to"] == ["external_ref"]
    assert external["valueType"] == "str"
    assert external["valueSemantics"] == "source_mapping_filename"

    assert set(schema["release"]["excludedMappings"]) == {
        "mapping_oraec_karnak.tsv",
        "mapping_oraec_lemmata_karnak.tsv",
    }


def test_all_non_slot_entity_nodes_have_an_oslots_strategy() -> None:
    schema = _schema()

    for node_type, spec in schema["nodeTypes"].items():
        if node_type == schema["slotType"]:
            continue
        assert spec["oslots"], node_type

    assert schema["nodeTypes"]["sentence"]["oslots"] == "contained_words"
    assert schema["nodeTypes"]["text"]["oslots"] == "contained_words"
    assert schema["nodeTypes"]["cv"]["oslots"] == "union_of_referencing_text_words"
    assert schema["nodeTypes"]["hierarchy"]["oslots"] == "union_of_descendant_text_words"


def test_sections_and_text_formats_follow_text_fabric_contract() -> None:
    schema = _schema()

    assert schema["sections"] == {
        "types": ["text", "sentence"],
        "features": ["oraec_id", "sentence_index"],
    }
    assert schema["formats"]["text-orig-full"] == "{written_form}{trailer}"
    assert schema["formats"]["text-translit"] == "{written_form}{trailer}"
    assert schema["formats"]["text-hiero"] == "{hiero}{trailer}"
    assert schema["formats"]["lex-default"] == "{lemma_form}"


def test_fail_closed_rules_prevent_lossy_or_ambiguous_materialization() -> None:
    rules = set(_schema()["failClosed"])
    assert {
        "unknown_source_field",
        "unsupported_source_shape_or_type",
        "lemma_id_form_conflict",
        "duplicate_relation_that_tf_edge_would_collapse",
        "unresolved_or_ambiguous_wikidata_key",
        "malformed_hierarchy_path_link_alignment",
        "unsupported_or_unlicensed_mapping_family",
        "source_string_normalization",
    } <= rules


def test_schema_records_source_vs_derived_provenance() -> None:
    schema = _schema()

    for node_spec in schema["nodeTypes"].values():
        for feature_spec in node_spec.get("features", {}).values():
            assert feature_spec["origin"] in {"source", "derived"}
            assert feature_spec["description"]

    for edge_spec in schema["edgeFeatures"].values():
        assert edge_spec["origin"] in {"source", "derived"}
        assert edge_spec["description"]

    assert schema["nodeTypes"]["word"]["features"]["is_anchor"]["origin"] == "derived"
    assert schema["nodeTypes"]["word"]["features"]["trailer"]["origin"] == "derived"
    assert schema["nodeTypes"]["sentence"]["features"]["sentence_index"]["origin"] == "derived"
    assert schema["nodeTypes"]["hierarchy"]["features"]["hierarchy_id"]["origin"] == "derived"
    assert schema["nodeTypes"]["author"]["features"]["is_corpus_author"]["origin"] == "source"


def test_schema_adr_records_key_design_boundaries() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "word slots" in text
    assert "815,029" in text
    assert "no core `line` nodes" in text
    assert "empty string" in text
    assert "idno occurrence" in text
    assert "Karnak" in text
    assert "fail closed" in text
    assert "BHSA" in text
    assert "semantic sidecars" in text


def test_mapping_families_and_hierarchy_serialization_are_frozen() -> None:
    schema = _schema()
    mappings = schema["mappingFamilies"]

    assert mappings["mapping_oraec_trismegistos.csv"]["sourceDomain"] == "text.oraec_id"
    assert mappings["mapping_oraec_trismegistos.csv"]["targetSystem"] == "trismegistos"
    assert mappings["mapping_oraec_lemmata_vega.tsv"]["sourceDomain"] == "lex.lemma_id"
    assert mappings["mapping_oraec_lemmata_vega.tsv"]["targetSystem"] == "vega"
    assert mappings["mapping_oraec_wikidata.tsv"]["sourceDomain"] == (
        "author.author_name OR cv.cv_id"
    )
    assert mappings["mapping_oraec_wikidata.tsv"]["targetSystem"] == "wikidata"
    assert mappings["mapping_oraec_karnak.tsv"]["releaseStatus"] == (
        "excluded_pending_issue_17"
    )
    assert mappings["mapping_oraec_lemmata_karnak.tsv"]["releaseStatus"] == (
        "excluded_pending_issue_17"
    )

    hierarchy = schema["hierarchyContract"]
    assert hierarchy["separator"] == "→"
    assert hierarchy["emptyLabelsAreComponents"] is True
    assert "label_component_count_equals_link_component_count" in hierarchy["requirements"]

    assert set(schema["release"]["includedMappings"]) == {
        "mapping_oraec_trismegistos.csv",
        "mapping_oraec_wikidata.tsv",
        "mapping_oraec_lemmata_vega.tsv",
    }
