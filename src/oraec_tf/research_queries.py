"""Small, reproducible researcher recipes over an existing ORAEC Fabric API.

These are deliberately just ordinary Text-Fabric F/E/L/T/S operations.
They do not parse upstream JSON or require semantic sidecars.
"""

from __future__ import annotations

from typing import Any

CV_EDGE_FAMILIES = frozenset({
    "date", "origplace", "objecttype", "location", "material",
})


def find_text(api: Any, oraec_id: str) -> int | None:
    """Find a native text by its exact stable upstream ORAEC identifier."""
    return next(
        (n for n in api.F.otype.s("text") if api.F.oraec_id.v(n) == oraec_id),
        None,
    )


def words_with_pos(api: Any, pos: str) -> tuple[int, ...]:
    """Return real source word slots with a supplied exact POS label."""
    return tuple(
        n for n in api.F.otype.s("word")
        if api.F.token_id.v(n) is not None and api.F.pos.v(n) == pos
    )


def lemma_occurrences(api: Any, lemma_id: str) -> tuple[int, ...]:
    """Read a lex node's original word occurrences through native oslots."""
    lex = next(
        (n for n in api.F.otype.s("lex") if api.F.lemma_id.v(n) == lemma_id),
        None,
    )
    return () if lex is None else tuple(api.L.d(lex, otype="word"))


def texts_with_cv_label(
    api: Any, family: str, label: str,
) -> tuple[int, ...]:
    """Filter texts by their native ordered, ID-backed CV relation."""
    if family not in CV_EDGE_FAMILIES:
        raise ValueError(f"unsupported controlled-vocabulary family: {family}")
    edge = getattr(api.E, family, None)
    if edge is None:
        return ()
    return tuple(
        text
        for text in api.F.otype.s("text")
        if any(
            api.F.cv_label.v(target) == label
            and api.F.cv_kind.v(target) == family
            for target, _ordinal in edge.f(text)
        )
    )


def ordered_idnos(api: Any, text_node: int) -> tuple[str, ...]:
    """Preserve source idno list order and deliberately keep duplicates."""
    edge = getattr(api.E, "idno", None)
    if edge is None:
        return ()
    source_ordered = sorted(
        (
            api.F.idno_index.v(node),
            api.F.idno_value.v(node),
        )
        for node in edge.f(text_node)
    )
    return tuple(value for _ordinal, value in source_ordered)


def hierarchy_path(api: Any, text_node: int) -> tuple[tuple[str, str], ...]:
    """Return root→leaf linked TLA hierarchy from native parent edges."""
    relation = getattr(api.E, "hierarchy", None)
    if relation is None:
        return ()
    leaves = tuple(relation.f(text_node))
    if not leaves:
        return ()
    if len(leaves) != 1:
        raise ValueError("text has ambiguous hierarchy leaf identity")
    parent_edge = getattr(api.E, "parent", None)
    current = leaves[0]
    seen: set[int] = set()
    path: list[tuple[str, str]] = []
    while True:
        if current in seen:
            raise ValueError("hierarchy parent cycle")
        seen.add(current)
        path.append(
            (api.F.hierarchy_label.v(current), api.F.tla_url.v(current))
        )
        parents = () if parent_edge is None else tuple(parent_edge.f(current))
        if not parents:
            break
        if len(parents) != 1:
            raise ValueError("ambiguous hierarchy parent")
        current = parents[0]
    return tuple(reversed(path))
