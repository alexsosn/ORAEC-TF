"""RED-first local/private Karnak mapping E2E and adversarial regressions (#85)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tf.fabric import Fabric

from oraec_tf.audit_graph import GraphConservationError, audit_basic_graph
from oraec_tf.parser import (
    iter_texts,
    parse_corpus_metadata,
    parse_hierarchy,
    parse_mapping_tables,
)
from oraec_tf.parser_validation import CorpusValidationError, validate_corpus_source
from oraec_tf.writer import WriterError, write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _fixture(tmp_path: Path) -> Path:
    source = tmp_path / "raw"
    source.mkdir()
    (source / "README.md").write_text(
        "| file | license | author | source |\n"
        "| --- | --- | --- | --- |\n"
        "| oraec1.json .. oraec1.json | cc-by-sa-4.0 | Editor | synthetic |\n",
        encoding="utf-8",
    )
    record = {
        "oraec1": {
            "oraecid": "oraec1",
            "title": "Research sample",
            "credits": {"license": "cc-by-sa-4.0", "author": "Editor",
                        "source": ["https://example.invalid/text"]},
            "sentences": [{
                "translation": "",
                "token": [
                    {"token": "oraec1-1-1", "written_form": "nṯr",
                     "lemmaID": "101", "lemma_form": "nṯr"},
                    {"token": "oraec1-1-2", "written_form": "pr",
                     "lemmaID": "102", "lemma_form": "pr"},
                ],
            }],
        },
    }
    (source / "oraec1.json").write_text(
        json.dumps(record, ensure_ascii=False), encoding="utf-8",
    )
    (source / "oraec_hierarchical_path.tsv").write_text(
        'oraec1\tA\t<a href="https://thesaurus-linguae-aegyptiae.de/text/T1">A</a>\n',
        encoding="utf-8",
    )
    (source / "mapping_oraec_trismegistos.csv").write_text(
        "ORAEC,Trismegistos Text\noraec1,100\n", encoding="utf-8",
    )
    (source / "mapping_oraec_lemmata_vega.tsv").write_text(
        "101\thttps://vega.invalid/101\n", encoding="utf-8",
    )
    (source / "mapping_oraec_wikidata.tsv").write_text(
        "Editor\tQ1\n", encoding="utf-8",
    )
    (source / "mapping_oraec_karnak.tsv").write_text(
        "oraec1\thttp://sith.huma-num.fr/karnak/1\n", encoding="utf-8",
    )
    (source / "mapping_oraec_lemmata_karnak.tsv").write_text(
        "101\thttp://sith.huma-num.fr/vocable/1\n"
        "101\thttp://sith.huma-num.fr/vocable/2\n"
        "102\thttp://sith.huma-num.fr/vocable/1\n",
        encoding="utf-8",
    )
    return source


def _convert(source: Path, target: Path, *, include_karnak: bool) -> None:
    write_tf(
        iter_texts(source),
        target,
        source_revision=REVISION,
        corpus_metadata=parse_corpus_metadata(source),
        hierarchy_rows=parse_hierarchy(source),
        mapping_tables=parse_mapping_tables(source, include_karnak=include_karnak),
    )


def test_default_omits_karnak_and_opt_in_audits_all_four_pairs(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    default = tmp_path / "default-tf"
    _convert(source, default, include_karnak=False)
    assert audit_basic_graph(source, default) == {
        "texts": 1, "sentences": 1, "tokens": 2, "anchors": 0,
    }
    api = Fabric(locations=str(default), silent="deep").loadAll(silent="deep")
    assert all(api.F.external_system.v(n) != "karnak"
               for n in api.F.otype.s("external_ref"))
    opt = tmp_path / "local-tf"
    validated = validate_corpus_source(source, include_karnak=True)
    assert validated["counts"]["included_mapping_rows"] == 7
    assert validated["counts"]["excluded_mapping_rows"] == 0
    _convert(source, opt, include_karnak=True)
    assert audit_basic_graph(source, opt, include_karnak=True)["tokens"] == 2
    with pytest.raises(GraphConservationError, match="Karnak|mapping|external"):
        audit_basic_graph(source, opt)
    graph = Fabric(locations=str(opt), silent="deep").loadAll(silent="deep")
    refs = {n: graph.F.external_value.v(n) for n in graph.F.otype.s("external_ref")
            if graph.F.external_system.v(n) == "karnak"}
    assert len(refs) == 3
    provenance = [
        (source_node, refs[target], file_name)
        for source_node in (
            list(graph.F.otype.s("text")) + list(graph.F.otype.s("lex"))
        )
        for target, file_name in dict(graph.E.external.f(source_node)).items()
        if target in refs
    ]
    assert len(provenance) == 4
    assert sum(target.endswith("/vocable/1") for _, target, _ in provenance) == 2
    assert {filename for _, _, filename in provenance} == {
        "mapping_oraec_karnak.tsv", "mapping_oraec_lemmata_karnak.tsv",
    }


def test_local_mode_rejects_unresolved_karnak_source_before_publish(
    tmp_path: Path,
) -> None:
    source = _fixture(tmp_path)
    (source / "mapping_oraec_lemmata_karnak.tsv").write_text(
        "UNKNOWN\thttp://sith.huma-num.fr/vocable/2\n", encoding="utf-8",
    )
    # Default retains legacy behavior, but local mode must fail closed.
    assert validate_corpus_source(source)["ok"] is True
    with pytest.raises(CorpusValidationError, match="karnak|lemma|UNKNOWN"):
        validate_corpus_source(source, include_karnak=True)


def test_opt_in_rejects_duplicate_pair(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    (source / "mapping_oraec_karnak.tsv").write_text(
        "oraec1\thttp://sith.huma-num.fr/karnak/1\n"
        "oraec1\thttp://sith.huma-num.fr/karnak/1\n", encoding="utf-8",
    )
    with pytest.raises(CorpusValidationError, match="duplicate mapping"):
        validate_corpus_source(source, include_karnak=True)


def test_local_auditor_detects_missing_karnak_edges(tmp_path: Path) -> None:
    source = _fixture(tmp_path)
    out = tmp_path / "tf"
    _convert(source, out, include_karnak=False)
    with pytest.raises(GraphConservationError, match="mapping|external"):
        audit_basic_graph(source, out, include_karnak=True)


def test_writer_rejects_karnak_with_forged_family_filename(tmp_path: Path) -> None:
    from oraec_tf.ir import MappingRowIR, MappingTableIR

    source = _fixture(tmp_path)
    table = MappingTableIR(
        filename="unapproved_karnak.tsv", source_domain="text.oraec_id",
        target_system="karnak", release_included=True,
        rows=(MappingRowIR(source="oraec1", target="http://sith.invalid/1"),),
    )
    with pytest.raises(WriterError, match="unapproved"):
        write_tf(iter_texts(source), tmp_path / "tf",
                 source_revision=REVISION, mapping_tables=(table,))


def test_opt_in_is_explicit_direct_cli_and_tracks_origin_without_source_copy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    from unittest.mock import patch
    from oraec_tf.cli import main
    from oraec_tf.source import SourceSnapshot

    source = _fixture(tmp_path)
    out = tmp_path / "explicit-tf"
    with patch("oraec_tf.cli.verify_source", return_value=SourceSnapshot(
        path=source, revision=REVISION,
    )):
        assert main([
            "convert", str(source), "--output", str(out),
            "--upstream-commit", REVISION, "--include-karnak",
        ]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["mapping_mode"] == "local-karnak-opt-in"
    assert summary["karnak_mapping_redistribution_terms"] == "unresolved"
    assert summary["karnak_mapping_files"] == [
        "mapping_oraec_karnak.tsv",
        "mapping_oraec_lemmata_karnak.tsv",
    ]
    assert audit_basic_graph(source, out, include_karnak=True)["tokens"] == 2
    otext = (out / "otext.tf").read_text(encoding="utf-8")
    assert "karnakMappingRedistributionTerms=unresolved" in otext
    assert "karnakTextMappingSource=mapping_oraec_karnak.tsv" in otext
    assert "karnakLemmaMappingSource=mapping_oraec_lemmata_karnak.tsv" in otext
    assert not (out / "mapping_oraec_karnak.tsv").exists()
    assert not (out / "mapping_oraec_lemmata_karnak.tsv").exists()


def test_schema_separates_default_exclusion_and_local_opt_in() -> None:
    schema = json.loads((Path(__file__).resolve().parents[1] /
                         "schema/core.json").read_text(encoding="utf-8"))
    files = {
        "mapping_oraec_karnak.tsv", "mapping_oraec_lemmata_karnak.tsv",
    }
    assert set(schema["release"]["excludedMappings"]) == files
    assert set(schema["release"]["localOptInMappings"]) == files
    assert schema["release"]["localOptInFlag"] == "--include-karnak"
    for filename in files:
        assert schema["mappingFamilies"][filename]["localOptInStatus"] == (
            "direct_cli_only"
        )
