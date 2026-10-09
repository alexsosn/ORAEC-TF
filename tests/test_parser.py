from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from oraec_tf.ir import (
    ControlledValueIR,
    CorpusMetadataIR,
    HierarchyComponentIR,
    MappingTableIR,
    SentenceIR,
    TextIR,
    TokenIR,
)
from oraec_tf.parser import (
    ParseError,
    iter_texts,
    parse_corpus_metadata,
    parse_hierarchy,
    parse_mapping_tables,
    parse_text,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _record(text_id: str = "oraec1") -> dict[str, object]:
    return {
        "oraecid": text_id,
        "title": "Exact title",
        "bibliography": "Ref\n[exact]",
        "condition": "fragmentarisch",
        "date": [{"date": "Period A", "id": "D1"}],
        "origplace": [{"origplace": "Place A", "id": "P1"}],
        "objecttype": [
            {"objecttype": "Stele", "id": "O1"},
            {"objecttype": "Text", "id": "O2"},
        ],
        "location": [{"location": "Museum", "id": "L1"}],
        "material": [{"material": "Stone", "id": "M1"}],
        "idno": ["X", "X"],
        "sentences": [
            {
                "translation": "",
                "token": [
                    {
                        "token": f"{text_id}-1-1",
                        "written_form": " nṯr ",
                        "cotext_translation": "god",
                        "lemmaID": "90260",
                        "lemma_form": "nṯr",
                        "lineCount": " [1]",
                        "hiero": "�𓇾",
                        "pos": "substantive",
                        "name": "person_name",
                        "number": "cardinal_number",
                        "voice": "active",
                        "genus": "masculine",
                        "pronoun": "personal_pronoun",
                        "numerus": "singular",
                        "epitheton": "title",
                        "morphology": "n-morpheme",
                        "inflection": "participle",
                        "adjective": "nisbe_adjective",
                        "particle": "enclitic_particle",
                        "adverb": "prepositional_adverb",
                        "verbalClass": "verb_3-lit",
                        "status": "st_absolutus",
                    },
                    {
                        "token": f"{text_id}-1-2",
                        "written_form": "[...]",
                    },
                ],
            },
            {"translation": "{empty source sentence}", "token": []},
        ],
        "credits": {
            "license": "cc-by-sa-4.0",
            "author": "Editor A",
            "source": [
                "https://example.invalid/aes",
                "https://example.invalid/aed.xml",
            ],
        },
    }


def _source_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()

    (root / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec10.json | cc-by-sa-4.0 | "
        "Editor A, Corpus Contributor | synthetic |\n",
        encoding="utf-8",
    )

    _write_json(root / "oraec10.json", {"oraec10": _record("oraec10")})
    _write_json(root / "oraec2.json", {"oraec2": _record("oraec2")})
    _write_json(root / "oraec1.json", {"oraec1": _record("oraec1")})

    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\t\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1"></a>\n'
        "oraec2\tRoot→Leaf\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/object/O1">Root</a>→'
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T2">Leaf</a>\n',
        encoding="utf-8",
    )

    (root / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec1,100\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_lemmata_vega.tsv").write_text(
        "90260\thttps://vega.invalid/90260\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_wikidata.tsv").write_text(
        "Editor A\tQ1\nD1\tQ2\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_karnak.tsv").write_text(
        "oraec1\thttps://karnak.invalid/text/1\n",
        encoding="utf-8",
    )
    (root / "mapping_oraec_lemmata_karnak.tsv").write_text(
        "90260\thttps://karnak.invalid/lemma/1\n"
        "90260\thttps://karnak.invalid/lemma/2\n",
        encoding="utf-8",
    )
    return root


def test_ir_is_frozen_slotted_and_explicit() -> None:
    token = TokenIR(token_id="oraec1-1-1", written_form="x")

    with pytest.raises(FrozenInstanceError):
        token.written_form = "changed"  # type: ignore[misc]

    assert not hasattr(token, "__dict__")
    assert TokenIR.__dataclass_fields__
    assert SentenceIR.__dataclass_fields__
    assert TextIR.__dataclass_fields__
    assert ControlledValueIR.__dataclass_fields__
    assert CorpusMetadataIR.__dataclass_fields__
    assert HierarchyComponentIR.__dataclass_fields__
    assert MappingTableIR.__dataclass_fields__


def test_parse_text_preserves_exact_values_and_zero_token_sentence(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)

    text = parse_text(root / "oraec1.json")

    assert text.oraec_id == "oraec1"
    assert text.title == "Exact title"
    assert text.bibliography == "Ref\n[exact]"
    assert text.condition == "fragmentarisch"
    assert text.idnos == ("X", "X")
    assert [value.cv_id for value in text.dates] == ["D1"]
    assert [value.cv_id for value in text.object_types] == ["O1", "O2"]
    assert text.credits.sources == (
        "https://example.invalid/aes",
        "https://example.invalid/aed.xml",
    )

    first = text.sentences[0]
    assert first.index == 1
    assert first.translation == ""
    assert first.tokens[0].written_form == " nṯr "
    assert first.tokens[0].line_count == " [1]"
    assert first.tokens[0].hiero == "�𓇾"
    assert first.tokens[0].lemma_id == "90260"
    assert first.tokens[0].lemma_form == "nṯr"
    assert first.tokens[1].lemma_id is None
    assert first.tokens[1].lemma_form is None

    empty = text.sentences[1]
    assert empty.index == 2
    assert empty.translation == "{empty source sentence}"
    assert empty.tokens == ()


def test_iter_texts_uses_numeric_source_order(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)

    assert [text.oraec_id for text in iter_texts(root)] == [
        "oraec1",
        "oraec2",
        "oraec10",
    ]


@pytest.mark.parametrize(
    ("level", "key"),
    [
        ("record", "unexpected_record"),
        ("sentence", "unexpected_sentence"),
        ("token", "unexpected_token"),
        ("credits", "unexpected_credits"),
        ("cv", "unexpected_cv"),
    ],
)
def test_parser_fails_closed_on_unknown_keys(
    tmp_path: Path,
    level: str,
    key: str,
) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec1.json").read_text(encoding="utf-8"))
    record = payload["oraec1"]

    if level == "record":
        record[key] = "x"
    elif level == "sentence":
        record["sentences"][0][key] = "x"
    elif level == "token":
        record["sentences"][0]["token"][0][key] = "x"
    elif level == "credits":
        record["credits"][key] = "x"
    else:
        record["date"][0][key] = "x"

    _write_json(root / "oraec1.json", payload)

    with pytest.raises(ParseError, match="unknown"):
        parse_text(root / "oraec1.json")


@pytest.mark.parametrize(
    "mutation",
    ["top_key", "oraecid", "token_position"],
)
def test_parser_rejects_source_identity_mismatches(
    tmp_path: Path,
    mutation: str,
) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec1.json").read_text(encoding="utf-8"))

    if mutation == "top_key":
        payload = {"oraec999": payload["oraec1"]}
    elif mutation == "oraecid":
        payload["oraec1"]["oraecid"] = "oraec999"
    else:
        payload["oraec1"]["sentences"][0]["token"][0]["token"] = "oraec1-9-9"

    _write_json(root / "oraec1.json", payload)

    with pytest.raises(ParseError, match="identity|position|top-level"):
        parse_text(root / "oraec1.json")


@pytest.mark.parametrize("missing", ["lemmaID", "lemma_form"])
def test_parser_requires_lemma_pair_copresence(tmp_path: Path, missing: str) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec1.json").read_text(encoding="utf-8"))
    del payload["oraec1"]["sentences"][0]["token"][0][missing]
    _write_json(root / "oraec1.json", payload)

    with pytest.raises(ParseError, match="lemmaID.*lemma_form|lemma_form.*lemmaID"):
        parse_text(root / "oraec1.json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", 7),
        ("sentences", {}),
        ("date", {}),
        ("bibliography", []),
    ],
)
def test_parser_rejects_wrong_record_types(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    root = _source_fixture(tmp_path)
    payload = json.loads((root / "oraec1.json").read_text(encoding="utf-8"))
    payload["oraec1"][field] = value
    _write_json(root / "oraec1.json", payload)

    with pytest.raises(ParseError, match=field):
        parse_text(root / "oraec1.json")


def test_parse_corpus_metadata_preserves_readme_author_order(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)

    metadata = parse_corpus_metadata(root)

    assert metadata.corpus_authors == ("Editor A", "Corpus Contributor")


def test_parse_corpus_metadata_rejects_duplicate_author_identity(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    (root / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec10.json | cc-by-sa-4.0 | "
        "Editor A, Editor A | synthetic |\n",
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match="duplicate.*author"):
        parse_corpus_metadata(root)


def test_parse_hierarchy_preserves_empty_component_and_tla_identity(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)

    rows = parse_hierarchy(root)

    first = rows[0]
    assert first.oraec_id == "oraec1"
    assert len(first.components) == 1
    assert first.components[0].label == ""
    assert first.components[0].tla_url == (
        "https://thesaurus-linguae-aegyptiae.de/text/T1"
    )
    assert first.components[0].tla_kind == "text"
    assert first.components[0].tla_id == "T1"

    second = rows[1]
    assert [component.label for component in second.components] == ["Root", "Leaf"]
    assert [component.tla_kind for component in second.components] == ["object", "text"]


def test_parse_hierarchy_rejects_component_mismatch(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    (root / "oraec_hierarchical_path.tsv").write_text(
        "oraec1\tRoot→Leaf\t"
        '<a href="https://thesaurus-linguae-aegyptiae.de/text/T1">Root</a>\n',
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match="component"):
        parse_hierarchy(root)


def test_parse_mapping_tables_preserves_family_semantics_and_rows(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)

    tables = {table.filename: table for table in parse_mapping_tables(root)}

    assert set(tables) == {
        "mapping_oraec_trismegistos.csv",
        "mapping_oraec_lemmata_vega.tsv",
        "mapping_oraec_wikidata.tsv",
        "mapping_oraec_karnak.tsv",
        "mapping_oraec_lemmata_karnak.tsv",
    }
    assert tables["mapping_oraec_trismegistos.csv"].source_domain == "text.oraec_id"
    assert tables["mapping_oraec_trismegistos.csv"].target_system == "trismegistos"
    assert tables["mapping_oraec_lemmata_vega.tsv"].source_domain == "lex.lemma_id"
    assert tables["mapping_oraec_wikidata.tsv"].source_domain == (
        "author.author_name OR cv.cv_id"
    )
    assert tables["mapping_oraec_wikidata.tsv"].release_included is True

    karnak = tables["mapping_oraec_lemmata_karnak.tsv"]
    assert karnak.release_included is False
    assert [(row.source, row.target) for row in karnak.rows] == [
        ("90260", "https://karnak.invalid/lemma/1"),
        ("90260", "https://karnak.invalid/lemma/2"),
    ]


def test_mapping_parser_rejects_malformed_rows(tmp_path: Path) -> None:
    root = _source_fixture(tmp_path)
    (root / "mapping_oraec_wikidata.tsv").write_text(
        "Editor A\n",
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match="mapping.*row|row.*mapping"):
        parse_mapping_tables(root)
