"""Lossless carriage-return transport for native Text-Fabric feature strings.

Text-Fabric 13.1 serializes LF/TAB/backslash but does not escape CR. A literal
CR splits a .tf row under Python universal-newline mode, corrupting sparse
node-feature addresses. We remove CR *only from the transport value* and store
its exact Unicode codepoint offsets in an ordinary TF node feature. Both fields
are queryable with the standard Fabric API; no JSON, XML, or sidecar is needed.

Offsets refer to the original string before any CR was removed. For example,
"X\\r\\nY" has encoded text "X\\nY" and offsets "bibliography=1".
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
    """Invalid or incomplete reversible control-character transport."""


def encode_node_features(node_type: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Return safe TF values plus sparse native source-CR-offset annotation."""
    if node_type not in NODE_TYPES:
        raise ControlCharacterError(f"unregistered node type: {node_type}")
    meta_name = f"{node_type}_cr_offsets"
    if meta_name in fields:
        raise ControlCharacterError(f"{meta_name} is reserved for codec metadata")

    encoded: dict[str, Any] = {}
    positions: list[str] = []
    for name, value in fields.items():
        if FEATURE_RE.fullmatch(name) is None:
            raise ControlCharacterError(f"invalid feature name: {name!r}")
        if isinstance(value, str) and "\r" in value:
            offsets = [str(i) for i, ch in enumerate(value) if ch == "\r"]
            encoded[name] = value.replace("\r", "")
            positions.append(f"{name}={','.join(offsets)}")
        else:
            encoded[name] = value

    if positions:
        # Delimiters never occur in feature names or decimal offsets.
        encoded[meta_name] = "|".join(sorted(positions))
    return encoded


def restore_source_string(
    transport: str | None, cr_offsets: str | None, feature: str,
) -> str | None:
    """Reconstruct the exact raw string from two standard TF feature values."""
    if FEATURE_RE.fullmatch(feature) is None:
        raise ControlCharacterError(f"invalid source feature: {feature!r}")
    if not cr_offsets:
        return transport
    if transport is not None and "\r" in transport:
        raise ControlCharacterError("transport contains an unescaped CR")
    located: dict[str, tuple[int, ...]] = {}
    for entry in cr_offsets.split("|"):
        parts = entry.split("=", 1)
        if len(parts) != 2 or FEATURE_RE.fullmatch(parts[0]) is None:
            raise ControlCharacterError("invalid control-character map entry")
        name, serial = parts
        if name in located or not serial:
            raise ControlCharacterError("duplicate/empty control-character offsets")
        try:
            offsets = tuple(int(piece) for piece in serial.split(","))
        except ValueError as exc:
            raise ControlCharacterError("noninteger carriage-return offset") from exc
        if any(i < 0 for i in offsets) or offsets != tuple(sorted(set(offsets))):
            raise ControlCharacterError("offsets must be strictly increasing")
        located[name] = offsets
    if feature not in located:
        return transport
    if transport is None:
        raise ControlCharacterError(f"missing encoded source feature: {feature}")
    result = transport
    for index in located[feature]:
        if index > len(result):
            raise ControlCharacterError("carriage-return offset out of bounds")
        result = result[:index] + "\r" + result[index:]
    return result
