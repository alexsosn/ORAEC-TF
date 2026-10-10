"""Independent raw ORAEC JSON → Text-Fabric conservation checks.

This code deliberately does not import the canonical parser, typed IR, schema
preflight, or TF writer. It reads raw JSON and an independently loaded Fabric
graph through separate public interfaces. It currently covers the primary
word/sentence/text spine; remaining native relations belong to issue #8.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tf.fabric import Fabric

TEXT_NAME_RE = re.compile(r"oraec[0-9]+\.json\Z")
SOURCE_WORD_FIELDS = {
    "token": "token_id",
    "written_form": "written_form",
    "cotext_translation": "cotext_translation",
    "hiero": "hiero",
    "lineCount": "line_count",
    "pos": "pos",
    "name": "name_type",
    "number": "number_type",
    "voice": "voice",
    "genus": "genus",
    "pronoun": "pronoun_type",
    "numerus": "numerus",
    "epitheton": "epitheton",
    "morphology": "morphology",
    "inflection": "inflection",
    "adjective": "adjective_type",
    "particle": "particle_type",
    "adverb": "adverb_type",
    "verbalClass": "verbal_class",
    "status": "status",
}


class GraphConservationError(ValueError):
    """An exact source field, identity, or node was lost or invented in TF."""


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GraphConservationError(f"duplicate raw JSON object key: {key}")
        result[key] = value
    return result


def _expect_equal(actual: object, expected: object, *, context: str) -> None:
    if actual != expected:
        raise GraphConservationError(
            f"{context}: expected {expected!r}, observed {actual!r}"
        )


def audit_basic_graph(source: str | Path, tf_dir: str | Path) -> dict[str, int]:
    """Compare all raw source text/sentence/word values against a loaded TF graph."""
    root = Path(source)
    paths = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and TEXT_NAME_RE.fullmatch(path.name)
    )
    if not paths:
        raise GraphConservationError("no ORAEC JSON source files")

    output = Path(tf_dir)
    # Load every emitted node/edge feature, not a writer-internal feature list.
    features = " ".join(sorted(path.stem for path in output.glob("*.tf")
                               if path.stem not in {"otype", "oslots"}))
    api = Fabric(locations=str(output), silent="deep").load(features, silent="deep")
    if not api:
        raise GraphConservationError("generated Text-Fabric output did not load")

    tf_texts = {
        api.F.oraec_id.v(n): n for n in api.F.otype.s("text")
    }
    if len(tf_texts) != len(api.F.otype.s("text")):
        raise GraphConservationError("duplicate Text-Fabric text identity")
    if len(tf_texts) != len(paths):
        raise GraphConservationError("missing or extra Text-Fabric text nodes")

    counts = {"texts": 0, "sentences": 0, "tokens": 0, "anchors": 0}
    observed_words: set[int] = set()
    for path in paths:
        text_id = path.stem
        try:
            decoded = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_no_duplicate_pairs,
            )
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise GraphConservationError(f"invalid source JSON: {path.name}") from exc
        if not isinstance(decoded, dict) or list(decoded) != [text_id]:
            raise GraphConservationError(f"unexpected JSON record identity: {text_id}")
        source_text = decoded[text_id]
        if not isinstance(source_text, dict):
            raise GraphConservationError(f"invalid raw ORAEC record: {text_id}")
        text_node = tf_texts.get(text_id)
        if text_node is None:
            raise GraphConservationError(f"missing TF text {text_id}")
        _expect_equal(
            api.F.title.v(text_node), source_text["title"], context=f"{text_id}.title"
        )
        _expect_equal(
            api.F.license.v(text_node),
            source_text["credits"]["license"],
            context=f"{text_id}.credits.license",
        )
        for raw_name in ("bibliography", "condition"):
            if raw_name in source_text:
                _expect_equal(
                    getattr(api.F, raw_name).v(text_node),
                    source_text[raw_name],
                    context=f"{text_id}.{raw_name}",
                )
        sentences = source_text["sentences"]
        actual_sentences = api.L.d(text_node, otype="sentence")
        _expect_equal(
            len(actual_sentences), len(sentences), context=f"{text_id}.sentences"
        )
        for index, (raw_sentence, sentence_node) in enumerate(
            zip(sentences, actual_sentences, strict=True), start=1
        ):
            _expect_equal(
                api.F.sentence_index.v(sentence_node),
                index,
                context=f"{text_id}.sentence_index",
            )
            _expect_equal(
                api.F.translation.v(sentence_node),
                raw_sentence["translation"],
                context=f"{text_id}.sentence[{index}].translation",
            )
            tf_slots = api.L.d(sentence_node, otype="word")
            raw_tokens = raw_sentence["token"]
            if not raw_tokens:
                _expect_equal(
                    len(tf_slots), 1, context=f"{text_id}.sentence[{index}].anchor"
                )
                anchor = tf_slots[0]
                _expect_equal(
                    api.F.is_anchor.v(anchor),
                    1,
                    context=f"{text_id}.sentence[{index}].is_anchor",
                )
                _expect_equal(
                    api.F.token_id.v(anchor),
                    None,
                    context=f"{text_id}.sentence[{index}].anchor.token_id",
                )
                counts["anchors"] += 1
                observed_words.add(anchor)
            else:
                _expect_equal(
                    len(tf_slots),
                    len(raw_tokens),
                    context=f"{text_id}.sentence[{index}].token_count",
                )
                for token_idx, (raw_token, slot) in enumerate(
                    zip(raw_tokens, tf_slots, strict=True), start=1
                ):
                    if api.F.is_anchor.v(slot) is not None:
                        raise GraphConservationError("fabricated anchor in real sentence")
                    for raw_field, tf_feature in SOURCE_WORD_FIELDS.items():
                        expected = raw_token.get(raw_field)
                        tf_feature_obj = getattr(api.F, tf_feature, None)
                        actual = None if tf_feature_obj is None else tf_feature_obj.v(slot)
                        _expect_equal(
                            actual,
                            expected,
                            context=(
                                f"{text_id}.sentence[{index}].token[{token_idx}]"
                                f".{raw_field}/{tf_feature}"
                            ),
                        )
                    observed_words.add(slot)
                    counts["tokens"] += 1
            counts["sentences"] += 1
        counts["texts"] += 1

    expected_word_count = counts["tokens"] + counts["anchors"]
    _expect_equal(
        len(observed_words), expected_word_count, context="unique TF word slots"
    )
    _expect_equal(
        len(api.F.otype.s("word")), expected_word_count, context="TF total slots"
    )
    return counts
