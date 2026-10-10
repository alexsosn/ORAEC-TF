"""Write a native ORAEC Text-Fabric graph directly from the typed source IR.

Issue #6 is still a draft until hierarchy, complete CLI conversion, whole-source
loadability, and the independent source-to-TF audit are implemented. No semantic
sidecars or raw JSON feature values are emitted.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path
from typing import Any

from tf.convert.walker import CV
from tf.fabric import Fabric

from .ir import CorpusMetadataIR, HierarchyRowIR, MappingTableIR, TextIR
from .text_codec import encode_node_features

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
CV_FIELDS = {
    "date": "dates",
    "origplace": "original_places",
    "objecttype": "object_types",
    "location": "locations",
    "material": "materials",
}
INCLUDED_MAPPINGS = {
    "trismegistos": "mapping_oraec_trismegistos.csv",
    "vega": "mapping_oraec_lemmata_vega.tsv",
    "wikidata": "mapping_oraec_wikidata.tsv",
}
OTEXT = {
    "sectionTypes": "text,sentence",
    "sectionFeatures": "oraec_id,sentence_index",
    "fmt:text-orig-full": "{written_form}{trailer}",
    "fmt:text-translit": "{written_form}{trailer}",
    "fmt:text-hiero": "{hiero}{trailer}",
}


class WriterError(ValueError):
    """The source or schema cannot be serialized into the frozen TF graph."""


def _schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "schema" / "core.json"
    if path.is_file():
        content = path.read_text(encoding="utf-8")
    else:
        content = files("oraec_tf").joinpath("schema_core.json").read_text(
            encoding="utf-8"
        )
    result: dict[str, Any] = json.loads(content)
    return result


def _feature_contract() -> tuple[dict[str, dict[str, str]], set[str]]:
    contract = _schema()
    metadata: dict[str, dict[str, str]] = {}
    int_features: set[str] = set()
    for kind in contract["nodeTypes"].values():
        for name, spec in kind["features"].items():
            if name in metadata:
                raise WriterError(f"duplicate feature metadata definition: {name}")
            metadata[name] = {
                "description": spec["description"],
                "origin": spec["origin"],
            }
            if "sourceField" in spec:
                metadata[name]["sourceField"] = spec["sourceField"]
            if spec["valueType"] == "int":
                int_features.add(name)
    for name, spec in contract["edgeFeatures"].items():
        if name in metadata:
            raise WriterError(f"node and edge feature name collision: {name}")
        metadata[name] = {
            "description": spec["description"],
            "origin": spec["origin"],
        }
        if "sourceField" in spec:
            metadata[name]["sourceField"] = spec["sourceField"]
        if spec["valueType"] == "int":
            int_features.add(name)
    return metadata, int_features


def _feature_metadata(used_features: set[str]) -> dict[str, dict[str, str]]:
    metadata, _ = _feature_contract()
    unknown = used_features - metadata.keys()
    if unknown:
        raise WriterError(f"schema metadata mismatch: {sorted(unknown)}")
    return {name: meta for name, meta in metadata.items() if name in used_features}


def write_tf(
    texts: Iterable[TextIR],
    output_dir: str | Path,
    *,
    source_revision: str,
    corpus_metadata: CorpusMetadataIR | None = None,
    mapping_tables: Iterable[MappingTableIR] = (),
    hierarchy_rows: Iterable[HierarchyRowIR] = (),
) -> None:
    """Materialize the current draft of the native graph into standard TF files."""
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
    corpus_authors = () if corpus_metadata is None else corpus_metadata.corpus_authors
    if len(corpus_authors) != len(set(corpus_authors)):
        raise WriterError("duplicate corpus author names")
    hierarchy = tuple(hierarchy_rows)
    if hierarchy:
        hierarchy_ids = [row.oraec_id for row in hierarchy]
        if len(hierarchy_ids) != len(set(hierarchy_ids)):
            raise WriterError("duplicate hierarchy text identity")
        if set(hierarchy_ids) != set(identities):
            raise WriterError("hierarchy must contain exactly one row per text")
        if any(not row.components for row in hierarchy):
            raise WriterError("hierarchy paths must contain at least one component")
    tables = tuple(mapping_tables)
    for table in tables:
        if table.release_included and (
            INCLUDED_MAPPINGS.get(table.target_system) != table.filename
        ):
            raise WriterError(f"unapproved mapping family: {table.filename}")

    metadata, int_features = _feature_contract()
    # Text-Fabric requires every declared text format to reference a node
    # feature that actually occurs. A tiny valid corpus may have no hiero at
    # all; do not invent hieroglyphic source values merely for display.
    has_hieroglyphs = any(
        token.hiero is not None
        for record in records
        for sentence in record.sentences
        for token in sentence.tokens
    )
    otext = (
        OTEXT
        if has_hieroglyphs
        else {key: value for key, value in OTEXT.items() if key != "fmt:text-hiero"}
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    fabric = Fabric(locations=str(output), silent="deep")
    cv = CV(fabric, silent="deep")

    def director(walker: Any) -> None:
        # Keep exact owner handles until all ordinary node slots are linked.
        # Occurrences are emitted once, after the source graph is finalized.
        pending_cr: list[tuple[Any, str, int]] = []

        def assign(node: Any, **values: Any) -> None:
            # TF 13.1 cannot safely serialize literal CR in a feature row.
            # Each original code point receives its own native TF occurrence.
            scalars, offsets = encode_node_features(node[0], values)
            walker.feature(node, **scalars)
            pending_cr.extend(
                (node, feature, offset) for feature, offset in offsets
            )

        text_handles: dict[str, Any] = {}
        text_slots: dict[str, set[int]] = {}
        lex_occurrences: dict[str, tuple[str, set[int]]] = {}
        all_slots: set[int] = set()

        # First pass: sections and exact slots in canonical source order.
        for record in records:
            t = walker.node("text")
            text_handles[record.oraec_id] = t
            text_data = {
                "oraec_id": record.oraec_id,
                "title": record.title,
                "license": record.credits.license,
            }
            if record.bibliography is not None:
                text_data["bibliography"] = record.bibliography
            if record.condition is not None:
                text_data["condition"] = record.condition
            assign(t, **text_data)
            slots: set[int] = set()
            for sentence in record.sentences:
                s = walker.node("sentence")
                assign(
                    s, sentence_index=sentence.index, translation=sentence.translation
                )
                if not sentence.tokens:
                    anchor = walker.slot()
                    assign(anchor, is_anchor=1, trailer="")
                    slots.add(anchor[1])
                else:
                    for token in sentence.tokens:
                        w = walker.slot()
                        slots.add(w[1])
                        values = {
                            field: val
                            for field in WORD_FIELDS
                            if (val := getattr(token, field)) is not None
                        }
                        assign(w, **values, trailer=" ")
                        if token.lemma_id is not None:
                            if token.lemma_form is None:
                                raise WriterError(
                                    f"lemma form missing for {token.lemma_id}"
                                )
                            existing = lex_occurrences.get(token.lemma_id)
                            if existing is None:
                                lex_occurrences[token.lemma_id] = (
                                    token.lemma_form, {w[1]}
                                )
                            else:
                                if existing[0] != token.lemma_form:
                                    raise WriterError(
                                        f"conflicting lemma_form for {token.lemma_id}"
                                    )
                                existing[1].add(w[1])
                walker.terminate(s)
            walker.terminate(t)
            text_slots[record.oraec_id] = slots
            all_slots.update(slots)

        # Shared lexical identities: oslots is the set of occurrence words.
        lex_handles: dict[str, Any] = {}
        for lemma_id, (lemma_form, slots) in sorted(lex_occurrences.items()):
            n = walker.node("lex", slots=sorted(slots))
            assign(n, lemma_id=lemma_id, lemma_form=lemma_form)
            lex_handles[lemma_id] = n

        # Shared controlled vocabulary; text edges preserve source ordinals.
        cv_occurrences: dict[tuple[str, str], tuple[str, set[int]]] = {}
        for record in records:
            for kind, attr in CV_FIELDS.items():
                for value in getattr(record, attr):
                    if value.kind != kind:
                        raise WriterError(f"CV kind mismatch: {value.kind} != {kind}")
                    key = (kind, value.cv_id)
                    existing = cv_occurrences.get(key)
                    if existing is None:
                        cv_occurrences[key] = (value.label, set(text_slots[record.oraec_id]))
                    else:
                        if existing[0] != value.label:
                            raise WriterError(f"conflicting CV labels for {key}")
                        existing[1].update(text_slots[record.oraec_id])
        cv_handles: dict[tuple[str, str], Any] = {}
        for (kind, cv_id), (label, slots) in sorted(cv_occurrences.items()):
            n = walker.node("cv", slots=sorted(slots))
            assign(n, cv_kind=kind, cv_id=cv_id, cv_label=label)
            cv_handles[kind, cv_id] = n
        for record in records:
            text_node = text_handles[record.oraec_id]
            for kind, attr in CV_FIELDS.items():
                seen: set[tuple[str, str]] = set()
                for index, value in enumerate(getattr(record, attr), start=1):
                    key = (kind, value.cv_id)
                    if key in seen:
                        raise WriterError(f"duplicate CV edge target in {record.oraec_id}")
                    seen.add(key)
                    walker.edge(text_node, cv_handles[key], **{kind: index})

        # README corpus-contribution is node provenance, not a text credit edge.
        credited_slots: dict[str, set[int]] = defaultdict(set)
        for record in records:
            credited_slots[record.credits.author].update(text_slots[record.oraec_id])
        corpus_positions = {name: idx for idx, name in enumerate(corpus_authors, 1)}
        authors: dict[str, Any] = {}
        for author in sorted(set(credited_slots) | set(corpus_positions)):
            slots = (
                all_slots if author in corpus_positions else credited_slots[author]
            )
            n = walker.node("author", slots=sorted(slots))
            fields: dict[str, Any] = {"author_name": author}
            if author in corpus_positions:
                fields["is_corpus_author"] = 1
                fields["corpus_author_index"] = corpus_positions[author]
            assign(n, **fields)
            authors[author] = n
        for record in records:
            walker.edge(
                text_handles[record.oraec_id],
                authors[record.credits.author],
                author=None,
            )

        # Source URLs are shared by exact string; ordinal edge values retain order.
        urls: dict[str, set[int]] = defaultdict(set)
        for record in records:
            if len(set(record.credits.sources)) != len(record.credits.sources):
                raise WriterError(f"duplicate source URL in {record.oraec_id}")
            for url in record.credits.sources:
                urls[url].update(text_slots[record.oraec_id])
        sources: dict[str, Any] = {}
        for url, slots in sorted(urls.items()):
            n = walker.node("source_ref", slots=sorted(slots))
            assign(n, source_url=url)
            sources[url] = n
        for record in records:
            for index, url in enumerate(record.credits.sources, start=1):
                walker.edge(
                    text_handles[record.oraec_id],
                    sources[url],
                    source=index,
                )

        # Duplicate source identifier strings have distinct occurrence nodes.
        for record in records:
            for index, identifier in enumerate(record.idnos, start=1):
                n = walker.node("idno", slots=sorted(text_slots[record.oraec_id]))
                assign(n, idno_value=identifier, idno_index=index)
                walker.edge(text_handles[record.oraec_id], n, idno=None)

        # Distinct ordered source path prefixes are distinct native graph nodes.
        # A TLA URL alone does not determine a single parent/ORAEC hierarchy path.
        if hierarchy:
            prefix_slots: dict[tuple[tuple[str, str], ...], set[int]] = defaultdict(set)
            prefix_meta: dict[tuple[tuple[str, str], ...], tuple[str, str]] = {}
            leaves: dict[str, tuple[tuple[str, str], ...]] = {}
            for row in hierarchy:
                prefix: tuple[tuple[str, str], ...] = ()
                for component in row.components:
                    prefix += ((component.label, component.tla_url),)
                    prefix_slots[prefix].update(text_slots[row.oraec_id])
                    detail = (component.tla_kind, component.tla_id)
                    if prefix in prefix_meta and prefix_meta[prefix] != detail:
                        raise WriterError(f"hierarchy TLA metadata conflict: {prefix}")
                    prefix_meta[prefix] = detail
                leaves[row.oraec_id] = prefix

            handles: dict[tuple[tuple[str, str], ...], Any] = {}
            for prefix in sorted(prefix_slots, key=lambda p: (len(p), p)):
                payload = json.dumps(
                    prefix, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
                digest = hashlib.sha256(payload).hexdigest()
                node = walker.node("hierarchy", slots=sorted(prefix_slots[prefix]))
                tla_kind, tla_id = prefix_meta[prefix]
                label, url = prefix[-1]
                assign(
                    node,
                    hierarchy_id=f"oraec-hierarchy:path-prefix:{digest}",
                    hierarchy_label=label,
                    hierarchy_depth=len(prefix),
                    tla_url=url,
                    tla_kind=tla_kind,
                    tla_id=tla_id,
                )
                handles[prefix] = node
                if len(prefix) > 1:
                    walker.edge(node, handles[prefix[:-1]], parent=None)
            for oraec_id, prefix in leaves.items():
                walker.edge(text_handles[oraec_id], handles[prefix], hierarchy=None)

        # Included external crosswalks; unlicensed Karnak never enters release TF.
        mapping_edges: dict[tuple[str, str], list[tuple[Any, str]]] = defaultdict(list)
        for table in tables:
            if not table.release_included:
                continue
            for mapping_row in table.rows:
                if table.target_system == "trismegistos":
                    source_handle = text_handles.get(mapping_row.source)
                elif table.target_system == "vega":
                    source_handle = lex_handles.get(mapping_row.source)
                elif table.target_system == "wikidata":
                    matches = [authors[mapping_row.source]] if mapping_row.source in authors else []
                    matches += [
                        handle
                        for (kind, cv_id), handle in cv_handles.items()
                        if cv_id == mapping_row.source
                    ]
                    if len(matches) != 1:
                        raise WriterError(
                            f"ambiguous or missing Wikidata source {mapping_row.source}"
                        )
                    source_handle = matches[0]
                else:
                    raise WriterError(f"unknown mapping family: {table.target_system}")
                if source_handle is None:
                    raise WriterError(
                        f"unresolved {table.target_system} source {mapping_row.source}"
                    )
                mapping_edges[(table.target_system, mapping_row.target)].append(
                    (source_handle, table.filename)
                )
        observed_edges: set[tuple[Any, str, str]] = set()
        for (system, value), edges in sorted(mapping_edges.items()):
            slots = set().union(*(set(walker.linked(handle)) for handle, _ in edges))
            if not slots:
                raise WriterError(f"external ref {system}:{value} has no slots")
            n = walker.node("external_ref", slots=sorted(slots))
            assign(n, external_system=system, external_value=value)
            for source_handle, filename in edges:
                mapping_edge_key = (source_handle, system, value)
                if mapping_edge_key in observed_edges:
                    raise WriterError("duplicate external mapping target would collapse")
                observed_edges.add(mapping_edge_key)
                walker.edge(source_handle, n, external=filename)

        # Native typed CR occurrences have exact owner identities and slots.
        # No string packs coordinates, and no new word/anchor slots are added.
        # Every previously emitted owner now has finalized word membership.
        for owner, source_feature, original_offset in pending_cr:
            owner_words = tuple(sorted(walker.linked(owner)))
            if not owner_words:
                raise WriterError("CR occurrence owner has no TF slots")
            occurrence = walker.node("cr_occurrence", slots=owner_words)
            walker.feature(
                occurrence,
                cr_feature=source_feature,
                cr_offset=original_offset,
            )
            walker.edge(occurrence, owner, cr_owner=None)

        # Remove contracts for absent optional features before Walker's checks.
        for feature in metadata:
            if not walker.occurs(feature):
                walker.meta(feature)

    good = cv.walk(
        director,
        "word",
        otext=otext,
        generic={
            "source": "https://github.com/oraec/corpus_raw_data",
            "sourceRevision": source_revision,
            "license": "CC BY-SA 4.0",
            "schemaVersion": str(_schema()["schemaVersion"]),
            "controlCharacterTransport": "native-cr-occurrences-v1",
        },
        intFeatures=int_features,
        featureMeta=metadata,
        warn=True,
        force=False,
    )
    if not good:
        raise WriterError("Text-Fabric walker rejected the ORAEC graph")
