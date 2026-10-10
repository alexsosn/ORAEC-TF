"""Native Text-Fabric writer for the core ORAEC word/sentence/text spine.

The graph is deliberately incomplete while #6 is a draft. It must not be
published as a corpus materializer until the remaining ADR 0005 node/edge
families are implemented and independently validated.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from tf.convert.walker import CV
from tf.fabric import Fabric

from .ir import TextIR

COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")

WORD_FIELDS = (
    "token_id",
    "written_form",
    "cotext_translation",
    "hiero",
    "line_count",
    "pos",
    "name_type",
    "number_type",
    "voice",
    "genus",
    "pronoun_type",
    "numerus",
    "epitheton",
    "morphology",
    "inflection",
    "adjective_type",
    "particle_type",
    "adverb_type",
    "verbal_class",
    "status",
)
INT_FEATURES = {"sentence_index", "is_anchor"}
OTEXT = {
    "sectionTypes": "text,sentence",
    "sectionFeatures": "oraec_id,sentence_index",
    "fmt:text-orig-full": "{written_form}{trailer}",
}


class WriterError(ValueError):
    """The typed source cannot be emitted as a valid native TF graph."""


def _feature_metadata(used_features: set[str]) -> dict[str, dict[str, str]]:
    """Read frozen feature declarations; avoid writing conflicting metadata."""
    import json

    schema_path = Path(__file__).resolve().parents[2] / "schema" / "core.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    names = used_features
    result: dict[str, dict[str, str]] = {}
    for node_type in ("word", "sentence", "text"):
        for feature, spec in schema["nodeTypes"][node_type]["features"].items():
            if feature not in names:
                continue
            result[feature] = {
                "description": spec["description"],
                "valueType": spec["valueType"],
                "origin": spec["origin"],
            }
            if "sourceField" in spec:
                result[feature]["sourceField"] = spec["sourceField"]
    if set(result) != names:
        raise WriterError(f"schema metadata mismatch: {sorted(names - set(result))}")
    return result


def write_tf(
    texts: Iterable[TextIR], output_dir: str | Path, *, source_revision: str
) -> None:
    """Write the initial source-token spine; #6 remains draft until full graph."""
    if COMMIT_RE.fullmatch(source_revision) is None:
        raise WriterError("source_revision must be an immutable 40-hex Git commit")
    records = tuple(texts)
    if not records:
        raise WriterError("cannot write an empty ORAEC corpus")
    identities = [record.oraec_id for record in records]
    if len(identities) != len(set(identities)):
        raise WriterError("duplicate ORAEC text identities")
    if any(not record.sentences for record in records):
        raise WriterError("cannot anchor a text with no sentence records")
    for record in records:
        if tuple(s.index for s in record.sentences) != tuple(
            range(1, len(record.sentences) + 1)
        ):
            raise WriterError(f"non-contiguous sentence indices: {record.oraec_id}")

    used_features = {
        "oraec_id", "title", "license", "sentence_index", "translation", "trailer"
    }
    for record in records:
        if record.bibliography is not None:
            used_features.add("bibliography")
        if record.condition is not None:
            used_features.add("condition")
        for sentence in record.sentences:
            if not sentence.tokens:
                used_features.add("is_anchor")
            for token in sentence.tokens:
                used_features.update(
                    field for field in WORD_FIELDS if getattr(token, field) is not None
                )
    if "written_form" not in used_features:
        raise WriterError("cannot produce a text format without real ORAEC words")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tf = Fabric(locations=str(output), silent="deep")
    cv = CV(tf, silent="deep")

    def director(walker: Any) -> None:
        for record in records:
            text = walker.node("text")
            text_features: dict[str, str] = {
                "oraec_id": record.oraec_id,
                "title": record.title,
                "license": record.credits.license,
            }
            if record.bibliography is not None:
                text_features["bibliography"] = record.bibliography
            if record.condition is not None:
                text_features["condition"] = record.condition
            walker.feature(text, **text_features)

            for sentence in record.sentences:
                section = walker.node("sentence")
                walker.feature(
                    section,
                    sentence_index=sentence.index,
                    translation=sentence.translation,
                )
                if not sentence.tokens:
                    anchor = walker.slot()
                    walker.feature(anchor, is_anchor=1, trailer="")
                else:
                    for token in sentence.tokens:
                        slot = walker.slot()
                        values = {
                            name: value
                            for name in WORD_FIELDS
                            if (value := getattr(token, name)) is not None
                        }
                        walker.feature(slot, **values, trailer=" ")
                walker.terminate(section)
            walker.terminate(text)

    good = cv.walk(
        director,
        "word",
        otext=OTEXT,
        generic={
            "source": "https://github.com/oraec/corpus_raw_data",
            "sourceRevision": source_revision,
            "license": "CC BY-SA 4.0",
        },
        intFeatures=INT_FEATURES & used_features,
        featureMeta=_feature_metadata(used_features),
        warn=True,
        force=False,
    )
    if not good:
        raise WriterError("Text-Fabric walker rejected the ORAEC graph")
