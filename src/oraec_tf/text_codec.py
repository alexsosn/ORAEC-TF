"""Queryable native Text-Fabric CR occurrences (schema v3, ADR 0007).

Text-Fabric 13.1 cannot escape literal U+000D in its line-oriented feature
files. The source scalar is transported without CR; *each* original CR is an
ordinary typed TF node linked to its exact owner, never a packed string.
"""

from __future__ import annotations

import re
from typing import Any

FEATURE_RE = re.compile(r"[a-z][a-z0-9_]*\Z")
NODE_TYPES = frozenset({
    "word", "sentence", "text", "lex", "cv", "author", "source_ref",
    "idno", "hierarchy", "external_ref",
})


class ControlCharacterError(ValueError):
    """A native TF control-character occurrence was forged or incomplete."""


def encode_node_features(
    node_type: str, fields: dict[str, Any],
) -> tuple[dict[str, Any], tuple[tuple[str, int], ...]]:
    """Return TF-safe scalars and one (feature, original offset) per CR.

    Original offsets are Unicode code-point positions, not byte or UTF-16
    indices; missing and explicitly empty source fields are distinguishable.
    """
    if node_type not in NODE_TYPES:
        raise ControlCharacterError(f"unregistered node type: {node_type}")
    encoded: dict[str, Any] = {}
    occurrences: list[tuple[str, int]] = []
    for name, value in fields.items():
        if FEATURE_RE.fullmatch(name) is None:
            raise ControlCharacterError(f"invalid feature name: {name!r}")
        if name.endswith("_cr_offsets") or name in {"cr_feature", "cr_offset"}:
            raise ControlCharacterError(f"reserved native CR feature: {name}")
        if isinstance(value, str) and "\r" in value:
            occurrences.extend(
                (name, offset) for offset, char in enumerate(value)
                if char == "\r"
            )
            encoded[name] = value.replace("\r", "")
        else:
            encoded[name] = value
    return encoded, tuple(occurrences)


def _restore(transport: str, offsets: tuple[int, ...]) -> str:
    """Restore Unicode positions in source-coordinate order."""
    if "\r" in transport:
        raise ControlCharacterError("transport value still contains raw CR")
    if not offsets:
        return transport
    if offsets != tuple(sorted(set(offsets))):
        raise ControlCharacterError("duplicate or unordered CR positions")
    total = len(transport) + len(offsets)
    if offsets[0] < 0 or offsets[-1] >= total:
        raise ControlCharacterError("CR offset outside original source string")
    source: list[str] = []
    index = 0
    for original_position in range(total):
        if index < len(offsets) and offsets[index] == original_position:
            source.append("\r")
            index += 1
        else:
            source.append(transport[original_position - index])
    return "".join(source)


class NativeCRIndex:
    """Reusable native-Fabric lookup of original CR source strings.

    Ordinary `F.cr_feature`, `F.cr_offset`, `E.cr_owner`, and `oslots` are
    the entire semantic representation; no hidden sidecar or packed grammar.
    """

    def __init__(self, api: Any) -> None:
        self.api = api
        self.positions: dict[tuple[int, str], tuple[int, ...]] = {}
        nodes = tuple(api.F.otype.s("cr_occurrence"))
        feature_accessor = getattr(api.F, "cr_feature", None)
        offset_accessor = getattr(api.F, "cr_offset", None)
        owner_edge = getattr(api.E, "cr_owner", None)
        if nodes and (
            feature_accessor is None or offset_accessor is None
            or owner_edge is None
        ):
            raise ControlCharacterError("missing native CR feature or owner edge")
        mutable: dict[tuple[int, str], list[int]] = {}
        for occurrence in nodes:
            feature = feature_accessor.v(occurrence)
            offset = offset_accessor.v(occurrence)
            if not isinstance(feature, str) or FEATURE_RE.fullmatch(feature) is None:
                raise ControlCharacterError("invalid CR feature identity")
            if type(offset) is not int or offset < 0:
                raise ControlCharacterError("invalid CR offset integer")
            owners = tuple(owner_edge.f(occurrence))
            if len(owners) != 1:
                raise ControlCharacterError("CR occurrence has no unique owner")
            owner = owners[0]
            owner_type = api.F.otype.v(owner)
            if owner_type not in NODE_TYPES:
                raise ControlCharacterError("invalid CR owner node type")
            accessor = getattr(api.F, feature, None)
            original = None if accessor is None else accessor.v(owner)
            if not isinstance(original, str):
                raise ControlCharacterError("unknown or nonstring CR owner feature")
            owner_words = (
                (owner,) if owner_type == "word"
                else tuple(api.L.d(owner, otype="word"))
            )
            occurrence_words = tuple(api.L.d(occurrence, otype="word"))
            if set(owner_words) != set(occurrence_words):
                raise ControlCharacterError("CR occurrence oslots mismatch owner")
            mutable.setdefault((owner, feature), []).append(offset)

        for key, offsets in mutable.items():
            position_list = tuple(sorted(offsets))
            if len(set(position_list)) != len(position_list):
                raise ControlCharacterError("duplicate CR offset for owner feature")
            scalar = getattr(api.F, key[1]).v(key[0])
            _restore(scalar, position_list)
            self.positions[key] = position_list

    def restore(self, node: int, feature: str) -> Any:
        """Return exact source Unicode from ordinary TF native graph APIs."""
        if FEATURE_RE.fullmatch(feature) is None:
            raise ControlCharacterError("invalid source feature identifier")
        accessor = getattr(self.api.F, feature, None)
        value = None if accessor is None else accessor.v(node)
        offsets = self.positions.get((node, feature), ())
        if offsets and not isinstance(value, str):
            raise ControlCharacterError("CR occurrence references missing scalar")
        return value if not isinstance(value, str) else _restore(value, offsets)
