"""Validate that the pinned ORAEC source can satisfy the frozen TF schema."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TEXT_FILE_RE = re.compile(r"^oraec(?P<number>\d+)\.json$")
ANCHOR_RE = re.compile(r'<a\s+href="([^"]+)">([^<]*)</a>')
CV_KINDS = ("date", "origplace", "objecttype", "location", "material")


def _text_paths(root: Path) -> list[Path]:
    paths = [
        path
        for path in root.iterdir()
        if path.is_file() and TEXT_FILE_RE.fullmatch(path.name)
    ]

    def number(path: Path) -> int:
        match = TEXT_FILE_RE.fullmatch(path.name)
        assert match is not None
        return int(match.group("number"))

    return sorted(paths, key=number)


def _record_anomaly(
    anomalies: dict[str, list[Any]],
    key: str,
    value: Any,
) -> None:
    anomalies.setdefault(key, []).append(value)


def _duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _iter_delimited(path: Path, *, delimiter: str) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


def audit_schema_source(root: str | Path) -> dict[str, Any]:
    """Check whether source identities/relations are representable by ADR 0005."""
    source = Path(root).resolve()
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")

    anomalies: dict[str, list[Any]] = {}
    text_ids: set[str] = set()
    lemma_ids: set[str] = set()
    authors: set[str] = set()
    cv_ids_by_kind: dict[str, set[str]] = {kind: set() for kind in CV_KINDS}

    for path in _text_paths(source):
        payload = json.loads(path.read_text(encoding="utf-8"))
        text_id = path.stem
        record = payload[text_id]
        text_ids.add(text_id)

        for kind in CV_KINDS:
            raw_items = record.get(kind, [])
            if not isinstance(raw_items, list):
                continue
            ids: list[str] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                raw_id = item.get("id")
                if isinstance(raw_id, str):
                    ids.append(raw_id)
                    cv_ids_by_kind[kind].add(raw_id)
            for duplicate in _duplicate_values(ids):
                _record_anomaly(
                    anomalies,
                    "edge_collapsing_duplicates",
                    {"text": text_id, "relation": kind, "target": duplicate},
                )

        credits = record.get("credits", {})
        if isinstance(credits, dict):
            author = credits.get("author")
            if isinstance(author, str):
                authors.add(author)
            raw_sources = credits.get("source", [])
            if isinstance(raw_sources, list):
                source_values = [value for value in raw_sources if isinstance(value, str)]
                for duplicate in _duplicate_values(source_values):
                    _record_anomaly(
                        anomalies,
                        "edge_collapsing_duplicates",
                        {
                            "text": text_id,
                            "relation": "source",
                            "target": duplicate,
                        },
                    )

        sentences = record.get("sentences", [])
        if not isinstance(sentences, list):
            continue
        for sentence in sentences:
            if not isinstance(sentence, dict):
                continue
            tokens = sentence.get("token", [])
            if not isinstance(tokens, list):
                continue
            for token in tokens:
                if not isinstance(token, dict):
                    continue
                lemma_id = token.get("lemmaID")
                if isinstance(lemma_id, str):
                    lemma_ids.add(lemma_id)

    required_files = (
        "mapping_oraec_trismegistos.csv",
        "mapping_oraec_lemmata_vega.tsv",
        "mapping_oraec_wikidata.tsv",
        "oraec_hierarchical_path.tsv",
    )
    for name in required_files:
        if not (source / name).is_file():
            _record_anomaly(anomalies, "missing_required_files", name)

    external_rows = 0
    seen_external_edges: set[tuple[str, str, str]] = set()

    tm_rows = _iter_delimited(
        source / "mapping_oraec_trismegistos.csv",
        delimiter=",",
    )
    if tm_rows and tm_rows[0][:2] == ["ORAEC", "Trismegistos Text"]:
        tm_rows = tm_rows[1:]
    unresolved_tm: set[str] = set()
    for row in tm_rows:
        if len(row) < 2:
            _record_anomaly(anomalies, "malformed_mapping_rows", {
                "file": "mapping_oraec_trismegistos.csv",
                "row": row,
            })
            continue
        external_rows += 1
        source_id, target = row[0], row[1]
        if source_id not in text_ids:
            unresolved_tm.add(source_id)
        edge = ("mapping_oraec_trismegistos.csv", source_id, target)
        if edge in seen_external_edges:
            _record_anomaly(anomalies, "duplicate_external_edges", {
                "file": edge[0], "source": source_id, "target": target,
            })
        seen_external_edges.add(edge)
    if unresolved_tm:
        anomalies["unresolved_trismegistos_text_ids"] = sorted(unresolved_tm)

    vega_rows = _iter_delimited(
        source / "mapping_oraec_lemmata_vega.tsv",
        delimiter="\t",
    )
    unresolved_vega: set[str] = set()
    for row in vega_rows:
        if len(row) < 2:
            _record_anomaly(anomalies, "malformed_mapping_rows", {
                "file": "mapping_oraec_lemmata_vega.tsv",
                "row": row,
            })
            continue
        external_rows += 1
        source_id, target = row[0], row[1]
        if source_id not in lemma_ids:
            unresolved_vega.add(source_id)
        edge = ("mapping_oraec_lemmata_vega.tsv", source_id, target)
        if edge in seen_external_edges:
            _record_anomaly(anomalies, "duplicate_external_edges", {
                "file": edge[0], "source": source_id, "target": target,
            })
        seen_external_edges.add(edge)
    if unresolved_vega:
        anomalies["unresolved_vega_lemma_ids"] = sorted(unresolved_vega)

    cv_domains: dict[str, set[str]] = defaultdict(set)
    for kind, ids in cv_ids_by_kind.items():
        for cv_id in ids:
            cv_domains[cv_id].add(f"cv:{kind}")

    wikidata_rows = _iter_delimited(
        source / "mapping_oraec_wikidata.tsv",
        delimiter="\t",
    )
    unresolved_wikidata: set[str] = set()
    ambiguous_wikidata: list[dict[str, Any]] = []
    for row in wikidata_rows:
        if len(row) < 2:
            _record_anomaly(anomalies, "malformed_mapping_rows", {
                "file": "mapping_oraec_wikidata.tsv",
                "row": row,
            })
            continue
        external_rows += 1
        key, target = row[0], row[1]
        domains = set(cv_domains.get(key, set()))
        if key in authors:
            domains.add("author")
        if not domains:
            unresolved_wikidata.add(key)
        elif len(domains) > 1:
            ambiguous_wikidata.append(
                {"key": key, "domains": sorted(domains)}
            )
        edge = ("mapping_oraec_wikidata.tsv", key, target)
        if edge in seen_external_edges:
            _record_anomaly(anomalies, "duplicate_external_edges", {
                "file": edge[0], "source": key, "target": target,
            })
        seen_external_edges.add(edge)
    if unresolved_wikidata:
        anomalies["unresolved_wikidata_keys"] = sorted(unresolved_wikidata)
    if ambiguous_wikidata:
        anomalies["ambiguous_wikidata_keys"] = sorted(
            ambiguous_wikidata,
            key=lambda item: item["key"],
        )

    hierarchy_rows = _iter_delimited(
        source / "oraec_hierarchical_path.tsv",
        delimiter="\t",
    )
    hierarchy_texts: list[str] = []
    seen_hierarchy_texts: set[str] = set()
    prefix_hashes: dict[str, str] = {}

    for row in hierarchy_rows:
        if len(row) != 3:
            _record_anomaly(
                anomalies,
                "malformed_hierarchy_rows",
                {"column_count": len(row), "row": row},
            )
            continue
        text_id, path_text, linked_text = row
        hierarchy_texts.append(text_id)
        if text_id in seen_hierarchy_texts:
            _record_anomaly(anomalies, "duplicate_hierarchy_texts", text_id)
        seen_hierarchy_texts.add(text_id)
        if text_id not in text_ids:
            _record_anomaly(anomalies, "unknown_hierarchy_texts", text_id)

        labels = path_text.split("→") if path_text != "" else []
        links = [
            (href, html.unescape(label))
            for href, label in ANCHOR_RE.findall(linked_text)
        ]
        if len(labels) != len(links):
            _record_anomaly(
                anomalies,
                "hierarchy_component_mismatches",
                {"text": text_id, "labels": len(labels), "links": len(links)},
            )
            continue

        prefix: list[str] = []
        for depth, (label, (href, linked_label)) in enumerate(
            zip(labels, links, strict=True),
            start=1,
        ):
            if label != linked_label:
                _record_anomaly(
                    anomalies,
                    "hierarchy_label_link_mismatches",
                    {
                        "text": text_id,
                        "depth": depth,
                        "label": label,
                        "linked_label": linked_label,
                    },
                )
            if not (
                href.startswith("https://thesaurus-linguae-aegyptiae.de/object/")
                or href.startswith("https://thesaurus-linguae-aegyptiae.de/text/")
            ):
                _record_anomaly(
                    anomalies,
                    "unsupported_hierarchy_links",
                    {"text": text_id, "depth": depth, "href": href},
                )
            prefix.append(f"{label}\u241f{href}")
            exact_prefix = "→".join(prefix)
            # Collision detection is intentionally independent of the writer.
            digest = hashlib.sha256(exact_prefix.encode("utf-8")).hexdigest()
            previous = prefix_hashes.get(digest)
            if previous is not None and previous != exact_prefix:
                _record_anomaly(
                    anomalies,
                    "hierarchy_path_prefix_hash_collisions",
                    {"digest": digest, "left": previous, "right": exact_prefix},
                )
            prefix_hashes[digest] = exact_prefix

    missing_hierarchy = sorted(text_ids - set(hierarchy_texts))
    if missing_hierarchy:
        anomalies["missing_hierarchy_texts"] = missing_hierarchy

    for key in list(anomalies):
        if not anomalies[key]:
            del anomalies[key]

    return {
        "ok": not anomalies,
        "counts": {
            "texts": len(text_ids),
            "lemmas": len(lemma_ids),
            "authors": len(authors),
            "cv_ids": sum(len(ids) for ids in cv_ids_by_kind.values()),
            "hierarchy_rows": len(hierarchy_rows),
            "external_rows": external_rows,
        },
        "anomalies": anomalies,
    }
