"""Researcher-facing, ordinary Text-Fabric queries over a *generated* ORAEC corpus.

Usage after the README's pinned-source conversion:
    python docs/examples.py build/oraec-tf/0.1.0-dev oraec1

No parser, IR object, sidecar, network request, or fabricated TF feature is used.
All APIs below accept the standard tf.fabric.Fabric API returned by loadAll().
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tf.fabric import Fabric

CV_EDGES = ("date", "origplace", "objecttype", "location", "material")


def load_corpus(tf_dir: str | Path) -> Any:
    """Load a locally materialized, independently validated TF feature graph."""
    api = Fabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    if not api:
        raise ValueError(f"cannot load ORAEC Text-Fabric at {tf_dir}")
    return api


def find_text(api: Any, oraec_id: str) -> int:
    """Resolve the upstream ORAEC identity without relying on node numbers."""
    for node in api.F.otype.s("text"):
        if api.F.oraec_id.v(node) == oraec_id:
            return int(node)
    raise KeyError(f"ORAEC text not found: {oraec_id}")


def sentences(api: Any, text_node: int) -> tuple[int, ...]:
    """Navigate text → ordered sentence nodes via native TF oslots."""
    return tuple(api.L.d(text_node, otype="sentence"))


def lexeme_words(api: Any, lemma_id: str) -> tuple[int, ...]:
    """Return slots annotated with a particular original lemma identity."""
    for node in api.F.otype.s("lex"):
        if api.F.lemma_id.v(node) == lemma_id:
            return tuple(api.L.d(node, otype="word"))
    return ()


def word_annotations(api: Any, word: int) -> dict[str, str | None]:
    """Read source morphology and writing without inventing annotations."""
    return {
        "token_id": api.F.token_id.v(word),
        "transliteration": api.F.written_form.v(word),
        "hieroglyphs": api.F.hiero.v(word),
        "pos": api.F.pos.v(word),
        "morphology": api.F.morphology.v(word),
        "lemma_id": api.F.lemma_id.v(word),
    }


def hierarchy_path(api: Any, text_node: int) -> list[dict[str, Any]]:
    """Traverse exact native TLA-linked ancestors, from root to leaf."""
    leaves = tuple(api.E.hierarchy.f(text_node))
    if len(leaves) != 1:
        raise ValueError("text must have exactly one native hierarchy leaf")
    node = leaves[0]
    visited: set[int] = set()
    path: list[dict[str, Any]] = []
    while node not in visited:
        visited.add(node)
        path.append({
            "label": api.F.hierarchy_label.v(node),
            "tla_url": api.F.tla_url.v(node),
            "depth": api.F.hierarchy_depth.v(node),
        })
        parents = tuple(api.E.parent.f(node))
        if len(parents) > 1:
            raise ValueError("hierarchy child has multiple parents")
        if not parents:
            return list(reversed(path))
        node = parents[0]
    raise ValueError("cycle in TLA hierarchy")


def controlled_values(api: Any, text_node: int, family: str) -> list[dict[str, Any]]:
    """Read ordered controlled-vocabulary values (source order is semantic)."""
    if family not in CV_EDGES:
        raise ValueError(f"unknown controlled-vocabulary family: {family}")
    accessor = getattr(api.E, family)
    rows = list(accessor.f(text_node))
    return [
        {
            "order": order,
            "id": api.F.cv_id.v(node),
            "label": api.F.cv_label.v(node),
        }
        for node, order in sorted(rows, key=lambda row: row[1])
    ]


def external_identifiers(api: Any, node: int) -> list[dict[str, str]]:
    """Read licensed external crosswalk targets and mapping provenance."""
    edge = getattr(api.E, "external", None)
    if edge is None:
        return []
    return [
        {
            "system": api.F.external_system.v(target),
            "id": api.F.external_value.v(target),
            "mapping_file": mapping_filename,
        }
        for target, mapping_filename in edge.f(node)
    ]


def search_nouns(api: Any, limit: int = 10) -> tuple[tuple[int, ...], ...]:
    """Use the normal TF search engine; 'pos=N' is an exact source tag.

    The source may use other POS values; this example does not interpret or
    normalize a tagset and does not assume the result is nonempty.
    """
    if "pos" not in api.Fall():
        return ()
    query = "word pos=N"
    return tuple(tuple(hit) for hit in api.S.search(query, limit=limit, silent=True))


def source_bibliography(api: Any, text_node: int) -> str | None:
    """Restore literal CR if the pinned raw bibliography contained U+000D."""
    from oraec_tf.text_codec import restore_source_string

    return restore_source_string(
        api.F.bibliography.v(text_node),
        api.F.text_cr_offsets.v(text_node) if hasattr(api.F, "text_cr_offsets") else None,
        "bibliography",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect native ORAEC Text-Fabric")
    parser.add_argument("tf_dir", type=Path, help="directory holding generated .tf files")
    parser.add_argument("oraec_id", help="exact upstream ORAEC text identity")
    args = parser.parse_args()
    api = load_corpus(args.tf_dir)
    text = find_text(api, args.oraec_id)
    print(f"{args.oraec_id}: {api.F.title.v(text)}")
    print(f"sentences: {len(sentences(api, text))}")
    for sentence in sentences(api, text)[:3]:
        print(f"sentence {api.F.sentence_index.v(sentence)}")
        print("  transliteration:", api.T.text(sentence, fmt="text-orig-full"))
    print("source metadata dates:", controlled_values(api, text, "date"))
    print("TLA hierarchy:", hierarchy_path(api, text))
    print("external identifiers:", external_identifiers(api, text))
    print("first noun search hits:", search_nouns(api, limit=3))


if __name__ == "__main__":
    main()
