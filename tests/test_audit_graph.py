"""Independent source/TF tests: real Fabric graph, no parser in audit implementation."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from oraec_tf.audit_graph import GraphConservationError, audit_basic_graph
from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
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
