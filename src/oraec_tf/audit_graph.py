"""Independent raw ORAEC JSON → Text-Fabric conservation checks.

This code deliberately does not import the canonical parser, typed IR, schema
preflight, or TF writer. It reads raw JSON and an independently loaded Fabric
graph through separate public interfaces. It currently covers the primary
word/sentence/text spine; remaining native relations belong to issue #8.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path
from typing import Any

from tf.fabric import Fabric

TEXT_NAME_RE = re.compile(r"oraec[0-9]+\.json\Z")
RAW_RECORD_KEYS = {
    "oraecid", "title", "sentences", "credits", "bibliography", "condition",
    "date", "origplace", "objecttype", "location", "material", "idno",
}
RAW_SENTENCE_KEYS = {"translation", "token"}
RAW_CREDITS_KEYS = {"license", "author", "source"}

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


PINNED_HIERO_COUNTS = {
    "present": 267_042,
    "placeholder": 13_198,
    "replacement": 6_545,
}


def _validate_hiero_counts(observed: dict[str, int]) -> None:
    """Independently enforce authoritative full-snapshot hieroglyph coverage.

    Exact Unicode values have already been compared source→Fabric token by
    token; these source-derived counts additionally catch changes in the
    supported pinned corpus snapshot, including uncertainty annotations.
    """
    for kind, expected in PINNED_HIERO_COUNTS.items():
        _expect_equal(
            observed.get(kind), expected,
            context=f"pinned source hiero {kind} coverage",
        )


class GraphConservationError(ValueError):
    """An exact source field, identity, or node was lost or invented in TF."""


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GraphConservationError(f"duplicate raw JSON object key: {key}")
        result[key] = value
    return result


def _reject_unmodeled_keys(
    record: dict[str, Any], known: set[str], *, context: str,
) -> None:
    unseen = set(record) - known
    if unseen:
        raise GraphConservationError(
            f"unknown raw source fields at {context}: {sorted(unseen)}"
        )


def _expect_equal(actual: object, expected: object, *, context: str) -> None:
    if actual != expected:
        raise GraphConservationError(
            f"{context}: expected {expected!r}, observed {actual!r}"
        )


def _edge_targets(api: Any, feature: str, source_node: int) -> Any:
    """An absent TF edge feature denotes no edge, not guessed relations."""
    accessor = getattr(api.E, feature, None)
    return () if accessor is None else accessor.f(source_node)


def _decode_transport_value(
    encoded: str, cr_positions: str, source_feature: str,
) -> str:
    """Independently reconstruct exact CR values from the native TF grammar.

    This verifier deliberately does not import the writer's encoder/decoder.
    Instead of inserting into a string, it walks the original character-index
    space and interleaves literal CR with the encoded transport characters.
    """
    positions_by_field: dict[str, list[int]] = {}
    for item in cr_positions.split("|"):
        if item.count("=") != 1:
            raise GraphConservationError("invalid native CR offset entry")
        name, data = item.split("=")
        if re.fullmatch(r"[a-z][a-z0-9_]*", name) is None:
            raise GraphConservationError("invalid native CR offset feature name")
        if name in positions_by_field:
            raise GraphConservationError("duplicate native CR offset feature")
        numbers = data.split(",")
        if not numbers or any(
            re.fullmatch(r"(?:0|[1-9][0-9]*)", digit) is None
            for digit in numbers
        ):
            raise GraphConservationError("invalid native CR offset integer")
        decoded = [int(n) for n in numbers]
        if decoded != sorted(set(decoded)):
            raise GraphConservationError("unordered/repeated native CR offsets")
        positions_by_field[name] = decoded

    positions = positions_by_field.get(source_feature)
    if positions is None:
        return encoded
    if "\r" in encoded:
        raise GraphConservationError("native TF feature still contains raw CR")
    total = len(encoded) + len(positions)
    if positions[-1] >= total:
        raise GraphConservationError("native CR position exceeds source length")
    restored: list[str] = []
    cr_index = 0
    for original_index in range(total):
        if cr_index < len(positions) and positions[cr_index] == original_index:
            restored.append("\r")
            cr_index += 1
        else:
            restored.append(encoded[original_index - cr_index])
    if cr_index != len(positions):
        raise GraphConservationError("native CR offset restoration incomplete")
    return "".join(restored)


def _node_value(api: Any, feature: str, node: int) -> Any:
    accessor = getattr(api.F, feature, None)
    value = None if accessor is None else accessor.v(node)
    if not isinstance(value, str) or feature.endswith("_cr_offsets"):
        return value
    node_type = api.F.otype.v(node)
    offset_accessor = getattr(api.F, f"{node_type}_cr_offsets", None)
    serial = None if offset_accessor is None else offset_accessor.v(node)
    return (
        value if not serial else _decode_transport_value(value, serial, feature)
    )


def _verify_text_relations(api: Any, text_node: int, source: dict[str, Any],
                           *, text_id: str) -> None:
    """Compare graph relations with source lists; keep order and duplicate idno."""
    credited = tuple(
        _node_value(api, "author_name", node)
        for node in _edge_targets(api, "author", text_node)
    )
    _expect_equal(
        credited, (source["credits"]["author"],),
        context=f"{text_id}.credits.author",
    )

    source_edges = _edge_targets(api, "source", text_node)
    actual_sources = sorted(
        (ordinal, _node_value(api, "source_url", node))
        for node, ordinal in dict(source_edges).items()
    )
    expected_sources = [
        (index, url)
        for index, url in enumerate(source["credits"]["source"], start=1)
    ]
    _expect_equal(
        actual_sources, expected_sources, context=f"{text_id}.credits.source"
    )

    idno_nodes = tuple(_edge_targets(api, "idno", text_node))
    actual_idnos = sorted(
        (
            _node_value(api, "idno_index", node),
            _node_value(api, "idno_value", node),
        )
        for node in idno_nodes
    )
    expected_idnos = [
        (index, value)
        for index, value in enumerate(source.get("idno", []), start=1)
    ]
    _expect_equal(actual_idnos, expected_idnos, context=f"{text_id}.idno")

    for source_field in ("date", "origplace", "objecttype", "location", "material"):
        edge = _edge_targets(api, source_field, text_node)
        observed = sorted(
            (
                ordinal,
                _node_value(api, "cv_kind", target),
                _node_value(api, "cv_id", target),
                _node_value(api, "cv_label", target),
            )
            for target, ordinal in dict(edge).items()
        )
        expected = [
            (index, source_field, item["id"], item[source_field])
            for index, item in enumerate(source.get(source_field, []), start=1)
        ]
        _expect_equal(
            observed, expected, context=f"{text_id}.{source_field}"
        )


def _verify_readme_and_external_crosswalks(
    api: Any, root: Path, tf_texts: dict[str, int],
    credited_authors: set[str],
) -> None:
    """Independently resolve external edges and README contributor identities."""
    tf_authors = {
        _node_value(api, "author_name", n): n
        for n in api.F.otype.s("author")
    }
    if len(tf_authors) != len(api.F.otype.s("author")):
        raise GraphConservationError("duplicate TF author identity")
    tf_lex = {
        _node_value(api, "lemma_id", n): n for n in api.F.otype.s("lex")
    }
    tf_cvs: dict[str, list[int]] = {}
    for n in api.F.otype.s("cv"):
        cv_id = _node_value(api, "cv_id", n)
        tf_cvs.setdefault(cv_id, []).append(n)

    readme = root / "README.md"
    declared: tuple[str, ...] = ()
    if readme.is_file():
        matching_rows = []
        for line in readme.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            fields = [field.strip() for field in line.strip().strip("|").split("|")]
            if (
                len(fields) >= 3
                and re.fullmatch(
                    r"oraec[0-9]+\.json\s*\.\.\s*oraec[0-9]+\.json",
                    fields[0],
                )
            ):
                matching_rows.append(fields)
        if len(matching_rows) != 1:
            raise GraphConservationError("README corpus author declaration missing")
        declared = tuple(
            x.strip() for x in matching_rows[0][2].split(",") if x.strip()
        )
        if len(set(declared)) != len(declared):
            raise GraphConservationError("duplicate README author identity")
        for idx, author in enumerate(declared, start=1):
            node = tf_authors.get(author)
            if node is None:
                raise GraphConservationError(f"missing README corpus author: {author}")
            _expect_equal(
                _node_value(api, "is_corpus_author", node),
                1,
                context=f"README corpus author {author}",
            )
            _expect_equal(
                _node_value(api, "corpus_author_index", node),
                idx,
                context=f"README corpus author index {author}",
            )
        unexpected = [
            author
            for author, node in tf_authors.items()
            if author not in declared and _node_value(api, "is_corpus_author", node) == 1
        ]
        if unexpected:
            raise GraphConservationError(
                f"invented README corpus authors: {unexpected}"
            )

    _expect_equal(
        set(tf_authors), credited_authors | set(declared),
        context="complete source-declared author identities (no invented authors)",
    )

    families = (
        ("mapping_oraec_trismegistos.csv", ",", "trismegistos"),
        ("mapping_oraec_lemmata_vega.tsv", "\t", "vega"),
        ("mapping_oraec_wikidata.tsv", "\t", "wikidata"),
    )
    expected: set[tuple[int, str, str, str]] = set()
    for filename, delimiter, system in families:
        path = root / filename
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        if filename == "mapping_oraec_trismegistos.csv":
            if rows and rows[0] == ["ORAEC", "Trismegistos Text"]:
                rows = rows[1:]
        for index, row in enumerate(rows, start=1):
            if len(row) != 2:
                raise GraphConservationError(
                    f"invalid mapping row {index}: {filename}"
                )
            key, target = row
            if system == "trismegistos":
                source_node = tf_texts.get(key)
            elif system == "vega":
                source_node = tf_lex.get(key)
            else:
                matches = ([tf_authors[key]] if key in tf_authors else []) + (
                    tf_cvs.get(key, [])
                )
                if len(matches) != 1:
                    raise GraphConservationError(
                        f"ambiguous Wikidata mapping source: {key}"
                    )
                source_node = matches[0]
            if source_node is None:
                raise GraphConservationError(
                    f"unresolved {system} mapping source: {key}"
                )
            relation = (source_node, system, target, filename)
            if relation in expected:
                raise GraphConservationError(
                    f"duplicate mapping row: {filename} {key} {target}"
                )
            expected.add(relation)

    external_nodes = tuple(api.F.otype.s("external_ref"))
    actual: set[tuple[int, str, str, str]] = set()
    used_external_nodes: set[int] = set()
    for node in (
        list(tf_texts.values()) + list(tf_authors.values())
        + list(tf_lex.values())
        + [n for nodes in tf_cvs.values() for n in nodes]
    ):
        edges = _edge_targets(api, "external", node)
        for target, filename in dict(edges).items():
            used_external_nodes.add(target)
            system = _node_value(api, "external_system", target)
            value = _node_value(api, "external_value", target)
            actual.add((node, system, value, filename))

    _expect_equal(actual, expected, context="external mapping edges")
    _expect_equal(
        used_external_nodes, set(external_nodes),
        context="unreferenced or invented external_ref nodes",
    )
    if any(_node_value(api, "external_system", n) == "karnak"
           for n in external_nodes):
        raise GraphConservationError("unlicensed Karnak mapping in generated TF")


class _StrictLinkedHierarchy(HTMLParser):
    """Parse complete source link markup independently of the converter regex."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.outside = ""
        self.href: str | None = None
        self.label = ""
        self.links: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "a" or self.inside or len(attrs) != 1:
            raise GraphConservationError("unexpected hierarchy linked markup")
        if self.outside != ("" if not self.links else "→"):
            raise GraphConservationError("unparsed hierarchy linked separator")
        self.outside = ""
        if attrs[0][0] != "href" or attrs[0][1] is None:
            raise GraphConservationError("hierarchy anchor missing href")
        self.href = attrs[0][1]
        self.label = ""
        self.inside = True

    def handle_data(self, data: str) -> None:
        if self.inside:
            self.label += data
        else:
            self.outside += data

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self.inside or self.href is None:
            raise GraphConservationError("unexpected hierarchy closing tag")
        self.links.append((self.href, self.label))
        self.href = None
        self.inside = False

    def handle_comment(self, data: str) -> None:
        raise GraphConservationError("unexpected hierarchy HTML comment")

    def finish(self) -> tuple[tuple[str, str], ...]:
        self.close()
        if self.inside or self.outside or not self.links:
            raise GraphConservationError("unparsed hierarchy linked path bytes")
        return tuple(self.links)


def _verify_hierarchy(api: Any, root: Path, tf_texts: dict[str, int]) -> None:
    path = root / "oraec_hierarchical_path.tsv"
    if not path.is_file():
        return
    rows: dict[str, tuple[tuple[str, str], ...]] = {}
    expected_prefixes: set[tuple[tuple[str, str], ...]] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        for index, fields in enumerate(csv.reader(handle, delimiter="\t"), start=1):
            if len(fields) != 3:
                raise GraphConservationError(
                    f"hierarchy row {index} must contain three columns"
                )
            oraec_id, plain, linked = fields
            if oraec_id in rows:
                raise GraphConservationError("duplicate hierarchy text identity")
            decoder = _StrictLinkedHierarchy()
            decoder.feed(linked)
            links = decoder.finish()
            labels = plain.split("→")
            if len(links) != len(labels):
                raise GraphConservationError(
                    f"hierarchy component count mismatch: {oraec_id}"
                )
            components: list[tuple[str, str]] = []
            for label, (href, linked_label) in zip(labels, links, strict=True):
                if label != linked_label:
                    raise GraphConservationError(
                        f"hierarchy linked label mismatch: {oraec_id}"
                    )
                if not (
                    href.startswith("https://thesaurus-linguae-aegyptiae.de/object/")
                    or href.startswith("https://thesaurus-linguae-aegyptiae.de/text/")
                ):
                    raise GraphConservationError(
                        f"unexpected hierarchy linked href: {oraec_id}"
                    )
                components.append((label, href))
                expected_prefixes.add(tuple(components))
            rows[oraec_id] = tuple(components)

    _expect_equal(set(rows), set(tf_texts), context="hierarchy text coverage")
    hierarchy_nodes = tuple(api.F.otype.s("hierarchy"))
    _expect_equal(
        len(hierarchy_nodes), len(expected_prefixes),
        context="hierarchy path-prefix node count",
    )
    observed_prefixes: set[tuple[tuple[str, str], ...]] = set()
    for oraec_id, expected in rows.items():
        text_node = tf_texts[oraec_id]
        tf_hierarchy_leaves = tuple(_edge_targets(api, "hierarchy", text_node))
        if len(tf_hierarchy_leaves) != 1:
            raise GraphConservationError(
                f"hierarchy leaf membership missing or duplicated: {oraec_id}"
            )
        current_hierarchy_node: int = tf_hierarchy_leaves[0]
        observed_path: list[tuple[str, str]] = []
        observed_nodes: list[int] = []
        visited: set[int] = set()
        while True:
            if current_hierarchy_node in visited:
                raise GraphConservationError("hierarchy parent cycle")
            visited.add(current_hierarchy_node)
            observed_nodes.append(current_hierarchy_node)
            observed_path.append(
                (
                    _node_value(api, "hierarchy_label", current_hierarchy_node),
                    _node_value(api, "tla_url", current_hierarchy_node),
                )
            )
            parents = tuple(_edge_targets(api, "parent", current_hierarchy_node))
            if not parents:
                break
            if len(parents) != 1:
                raise GraphConservationError("hierarchy has multiple parents")
            current_hierarchy_node = parents[0]
        observed_path.reverse()
        observed_nodes.reverse()
        _expect_equal(
            tuple(observed_path), expected,
            context=f"hierarchy exact source path for {oraec_id}",
        )
        for position, (node, (_, href)) in enumerate(
            zip(observed_nodes, expected, strict=True), start=1
        ):
            # Derive metadata directly from the *raw linked href*, never the
            # generated parser IR or TF writer's internal node inventory.
            base = "https://thesaurus-linguae-aegyptiae.de/"
            suffix = href.removeprefix(base)
            parts = suffix.split("/")
            if not href.startswith(base) or len(parts) != 2 or (
                parts[0] not in {"object", "text"} or not parts[1]
            ):
                raise GraphConservationError(
                    f"unparseable raw TLA hierarchy URL: {href!r}"
                )
            prefix = tuple(expected[:position])
            digest = hashlib.sha256(
                json.dumps(
                    prefix, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            required = {
                "tla_kind": parts[0],
                "tla_id": parts[1],
                "hierarchy_depth": position,
                "hierarchy_id": f"oraec-hierarchy:path-prefix:{digest}",
            }
            for feature, expected_value in required.items():
                _expect_equal(
                    _node_value(api, feature, node), expected_value,
                    context=f"{oraec_id}.hierarchy[{position}].{feature}",
                )
            observed_prefixes.add(prefix)
    _expect_equal(
        observed_prefixes, expected_prefixes,
        context="all source hierarchy prefixes",
    )



def _verify_native_entity_oslots(api: Any, text_nodes: dict[str, int]) -> None:
    """Independently check complete native entity identities and span unions.

    All source relations and hierarchy paths must be checked first: they are
    then an independent oracle for each target's exact TF word membership.
    """
    text_words = {
        node: set(api.L.d(node, otype="word"))
        for node in text_nodes.values()
    }
    all_words = set().union(*text_words.values())
    # Sources, CV values and credited authors may be shared; idno occurrences
    # are distinct, one per owning text, even if their labels are identical.
    families = (
        ("author", ("author",)),
        ("source_ref", ("source",)),
        ("cv", ("date", "origplace", "objecttype", "location", "material")),
        ("idno", ("idno",)),
    )
    for node_type, edge_names in families:
        expected: dict[int, set[int]] = defaultdict(set)
        idno_owner: dict[int, int] = {}
        for text_node, slots in text_words.items():
            for edge_name in edge_names:
                edge = _edge_targets(api, edge_name, text_node)
                # TF valued edges expose (target, ordinal) pairs; plain
                # edges expose target node IDs. Only the latter are direct.
                targets = (
                    dict(edge) if edge_name in {
                        "source", "date", "origplace", "objecttype",
                        "location", "material",
                    } else edge
                )
                for target in targets:
                    if node_type == "idno":
                        previous = idno_owner.setdefault(target, text_node)
                        if previous != text_node:
                            raise GraphConservationError(
                                "idno occurrence is owned by multiple texts"
                            )
                    expected[target].update(slots)
        existing_nodes = set(api.F.otype.s(node_type))
        if node_type == "author":
            # README corpus contribution is global provenance, not text credit.
            # Such authors explicitly cover all corpus slots.
            for node in existing_nodes:
                if _node_value(api, "is_corpus_author", node) == 1:
                    expected[node] = all_words
        _expect_equal(
            set(expected), existing_nodes,
            context=f"{node_type} complete native node identities",
        )
        if node_type in {"source_ref", "cv"}:
            identity_features = (
                ("source_url",) if node_type == "source_ref"
                else ("cv_kind", "cv_id")
            )
            identities = [
                tuple(_node_value(api, feature, node) for feature in identity_features)
                for node in existing_nodes
            ]
            _expect_equal(
                len(identities), len(set(identities)),
                context=f"{node_type} source identity uniqueness",
            )
        for node, slots in expected.items():
            actual = set(api.L.d(node, otype="word"))
            if actual != slots:
                raise GraphConservationError(
                    f"{node_type}[{node}].oslots: expected {len(slots)} words, "
                    f"observed {len(actual)}; missing {len(slots - actual)}, "
                    f"extra {len(actual - slots)}"
                )

    # Each source text belongs to its exact leaf and all its ancestors.
    hierarchy_expected: dict[int, set[int]] = defaultdict(set)
    for text_node, slots in text_words.items():
        leaves = tuple(_edge_targets(api, "hierarchy", text_node))
        for leaf in leaves:
            node = leaf
            visited: set[int] = set()
            while node not in visited:
                visited.add(node)
                hierarchy_expected[node].update(slots)
                parents = tuple(_edge_targets(api, "parent", node))
                if not parents:
                    break
                node = parents[0]
    _expect_equal(
        set(hierarchy_expected), set(api.F.otype.s("hierarchy")),
        context="hierarchy complete path-prefix node identities",
    )
    for node, slots in hierarchy_expected.items():
        actual = set(api.L.d(node, otype="word"))
        if actual != slots:
            raise GraphConservationError(
                f"hierarchy[{node}].oslots: expected {len(slots)} words, "
                f"observed {len(actual)}"
            )

    # External references inherit the union of all referencing entity spans.
    # The earlier checks independently established those underlying spans.
    external_expected: dict[int, set[int]] = defaultdict(set)
    source_nodes = list(text_words)
    for kind in ("author", "cv", "lex"):
        source_nodes.extend(api.F.otype.s(kind))
    for node in source_nodes:
        targets = dict(_edge_targets(api, "external", node))
        if targets:
            slots = set(api.L.d(node, otype="word"))
            for target in targets:
                external_expected[target].update(slots)
    _expect_equal(
        set(external_expected), set(api.F.otype.s("external_ref")),
        context="external_ref complete node identities",
    )
    for node, slots in external_expected.items():
        actual = set(api.L.d(node, otype="word"))
        if actual != slots:
            raise GraphConservationError(
                f"external_ref[{node}].oslots: expected {len(slots)} words, "
                f"observed {len(actual)}"
            )


REQUIRED_SOURCE_COMPANIONS = (
    "README.md",
    "oraec_hierarchical_path.tsv",
    "mapping_oraec_trismegistos.csv",
    "mapping_oraec_lemmata_vega.tsv",
    "mapping_oraec_wikidata.tsv",
    # These two files are required for snapshot integrity but never released.
    "mapping_oraec_karnak.tsv",
    "mapping_oraec_lemmata_karnak.tsv",
)


def audit_basic_graph(
    source: str | Path, tf_dir: str | Path, *,
    require_complete_source: bool = False,
) -> dict[str, int]:
    """Independently compare raw ORAEC semantics against loaded TF."""
    root = Path(source)
    if require_complete_source:
        missing = [
            filename for filename in REQUIRED_SOURCE_COMPANIONS
            if not (root / filename).is_file()
        ]
        if missing:
            raise GraphConservationError(
                f"required source companion files missing: {missing}"
            )
    paths = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and TEXT_NAME_RE.fullmatch(path.name)
    )
    if not paths:
        raise GraphConservationError("no ORAEC JSON source files")

    output = Path(tf_dir)
    # Use Text-Fabric's built-in index to discover loadable features. This
    # includes all node and valued-edge features without assuming a writer
    # feature inventory or constructing a fragile string from file names.
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    if not api:
        raise GraphConservationError("generated Text-Fabric output did not load")

    tf_texts = {
        _node_value(api, "oraec_id", n): n for n in api.F.otype.s("text")
    }
    if len(tf_texts) != len(api.F.otype.s("text")):
        raise GraphConservationError("duplicate Text-Fabric text identity")
    if len(tf_texts) != len(paths):
        raise GraphConservationError("missing or extra Text-Fabric text nodes")

    counts = {"texts": 0, "sentences": 0, "tokens": 0, "anchors": 0}
    hiero_counts = {"present": 0, "placeholder": 0, "replacement": 0}
    observed_words: set[int] = set()
    expected_lemmas: dict[str, tuple[str, set[int]]] = {}
    credited_authors: set[str] = set()
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
        _reject_unmodeled_keys(
            source_text, RAW_RECORD_KEYS, context=f"{text_id}.record"
        )
        _expect_equal(
            source_text.get("oraecid"), text_id, context=f"{text_id}.oraecid"
        )
        credits = source_text.get("credits")
        if not isinstance(credits, dict):
            raise GraphConservationError(f"invalid credits object: {text_id}")
        _reject_unmodeled_keys(
            credits, RAW_CREDITS_KEYS, context=f"{text_id}.credits"
        )
        text_node = tf_texts.get(text_id)
        if text_node is None:
            raise GraphConservationError(f"missing TF text {text_id}")
        _expect_equal(
            _node_value(api, "title", text_node), source_text["title"], context=f"{text_id}.title"
        )
        _expect_equal(
            _node_value(api, "license", text_node),
            source_text["credits"]["license"],
            context=f"{text_id}.credits.license",
        )
        credited_authors.add(credits["author"])
        _verify_text_relations(api, text_node, source_text, text_id=text_id)
        for raw_name in ("bibliography", "condition"):
            # Absence is meaningful: reject invented annotations as well as
            # dropped values, and keep a present empty string distinct from None.
            _expect_equal(
                _node_value(api, raw_name, text_node),
                source_text.get(raw_name),
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
            if not isinstance(raw_sentence, dict):
                raise GraphConservationError("raw sentence is not an object")
            _reject_unmodeled_keys(
                raw_sentence, RAW_SENTENCE_KEYS,
                context=f"{text_id}.sentence[{index}]",
            )
            _expect_equal(
                api.F.sentence_index.v(sentence_node),
                index,
                context=f"{text_id}.sentence_index",
            )
            _expect_equal(
                _node_value(api, "translation", sentence_node),
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
                    _node_value(api, "token_id", anchor),
                    None,
                    context=f"{text_id}.sentence[{index}].anchor.token_id",
                )
                # A technical anchor represents zero source tokens; it may
                # never receive invented written forms, morphology, source
                # hieroglyphs, line annotations or cotext values.
                for tf_feature in SOURCE_WORD_FIELDS.values():
                    if tf_feature == "token_id":
                        continue
                    _expect_equal(
                        _node_value(api, tf_feature, anchor),
                        None,
                        context=f"{text_id}.sentence[{index}].anchor.{tf_feature}",
                    )
                _expect_equal(
                    _node_value(api, "word_cr_offsets", anchor),
                    None,
                    context=f"{text_id}.sentence[{index}].anchor.word_cr_offsets",
                )
                _expect_equal(
                    _node_value(api, "trailer", anchor),
                    "",
                    context=f"{text_id}.sentence[{index}].anchor.trailer",
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
                    # Count *source* code points; no TF/writer-derived tags.
                    # Distinguish missing hiero from a present empty string.
                    if "hiero" in raw_token:
                        value = raw_token["hiero"]
                        if not isinstance(value, str):
                            raise GraphConservationError(
                                f"invalid source hiero string in {text_id}"
                                f".sentence[{index}].token[{token_idx}]"
                            )
                        hiero_counts["present"] += 1
                        if value == "[⯑]":
                            hiero_counts["placeholder"] += 1
                        if "�" in value:
                            hiero_counts["replacement"] += 1
                    unknown = set(raw_token) - set(SOURCE_WORD_FIELDS) - {
                        "lemmaID", "lemma_form",
                    }
                    if unknown:
                        raise GraphConservationError(
                            f"unmodeled raw token annotations in {text_id}: "
                            f"{sorted(unknown)}"
                        )
                    for raw_field, tf_feature in SOURCE_WORD_FIELDS.items():
                        expected = raw_token.get(raw_field)
                        actual = _node_value(api, tf_feature, slot)
                        _expect_equal(
                            actual,
                            expected,
                            context=(
                                f"{text_id}.sentence[{index}].token[{token_idx}]"
                                f".{raw_field}/{tf_feature}"
                            ),
                        )
                    if "lemmaID" in raw_token:
                        lemma_id = raw_token["lemmaID"]
                        lemma_form = raw_token["lemma_form"]
                        entry = expected_lemmas.get(lemma_id)
                        if entry is None:
                            expected_lemmas[lemma_id] = (lemma_form, {slot})
                        elif entry[0] != lemma_form:
                            raise GraphConservationError(
                                f"{text_id}.lemmaID {lemma_id} has conflicting forms"
                            )
                        else:
                            entry[1].add(slot)
                    observed_words.add(slot)
                    counts["tokens"] += 1
            counts["sentences"] += 1
        counts["texts"] += 1

    actual_lex_nodes = tuple(api.F.otype.s("lex"))
    actual_lex = {
        _node_value(api, "lemma_id", node): node for node in actual_lex_nodes
    }
    _expect_equal(
        set(actual_lex), set(expected_lemmas), context="shared lexeme identity set"
    )
    _expect_equal(
        len(actual_lex), len(actual_lex_nodes), context="lexeme identity uniqueness"
    )
    for lemma_id, (lemma_form, expected_slots) in expected_lemmas.items():
        node = actual_lex[lemma_id]
        _expect_equal(
            _node_value(api, "lemma_form", node),
            lemma_form, context=f"lemma[{lemma_id}].lemma_form",
        )
        _expect_equal(
            set(api.L.d(node, otype="word")), expected_slots,
            context=f"lemma[{lemma_id}].oslots",
        )

    expected_word_count = counts["tokens"] + counts["anchors"]
    _expect_equal(
        len(observed_words), expected_word_count, context="unique TF word slots"
    )
    _expect_equal(
        len(api.F.otype.s("word")), expected_word_count, context="TF total slots"
    )
    _verify_readme_and_external_crosswalks(
        api, root, tf_texts, credited_authors,
    )
    _verify_hierarchy(api, root, tf_texts)
    _verify_native_entity_oslots(api, tf_texts)
    if require_complete_source:
        _validate_hiero_counts(hiero_counts)
    return counts


def audit_graph_with_provenance(
    source: str | Path,
    tf_dir: str | Path,
    *,
    source_revision: str,
    converter_revision: str,
    schema_version: int,
    require_complete_source: bool = False,
) -> dict[str, Any]:
    """Emit only reproducible build identities, counts and output hashes."""
    for kind, sha in (
        ("source revision", source_revision),
        ("converter revision", converter_revision),
    ):
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise GraphConservationError(f"{kind} must be a full commit SHA")
    if schema_version < 1:
        raise GraphConservationError("schema version must be a positive integer")
    counts = audit_basic_graph(
        source, tf_dir, require_complete_source=require_complete_source,
    )
    paths = sorted(
        path for path in Path(tf_dir).glob("*.tf")
        if path.is_file() and not path.name.startswith(".")
    )
    if not paths:
        raise GraphConservationError("generated TF contains no feature files")
    output_hashes: dict[str, str] = {}
    output_bytes: dict[str, int] = {}
    for path in paths:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        output_hashes[path.name] = digest.hexdigest()
        output_bytes[path.name] = path.stat().st_size
    return {
        "ok": True,
        "output_bytes": output_bytes,
        "total_tf_bytes": sum(output_bytes.values()),
        "source_revision": source_revision,
        "converter_revision": converter_revision,
        "schema_version": schema_version,
        "tf_version": version("text-fabric"),
        "counts": counts,
        "output_sha256": output_hashes,
    }
