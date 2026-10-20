"""Typed source-independent Text-Fabric feature parity for optional Rust CF.

Only public node/edge items() values are used. Names or cache existence alone
are insufficient. Source validation remains the independent ORAEC graph audit.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Iterable, Mapping
from typing import Any, Literal, cast

FeatureKind = Literal["node", "edge"]


class FeatureParityError(ValueError):
    """A typed TF feature or Context-Fabric value diverged."""


def _typed_scalar(value: object) -> list[object]:
    if value is None:
        return ["none"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, float):
        return ["float", repr(value)]
    raise FeatureParityError(f"unsupported scalar feature type: {type(value).__name__}")


def _canonical_edge(value: object) -> list[object]:
    if isinstance(value, Mapping):
        pairs: list[list[object]] = []
        for destination, edge_value in value.items():
            if not isinstance(destination, int) or isinstance(destination, bool):
                raise FeatureParityError("edge destination must be integer TF node")
            pairs.append([destination, _typed_scalar(edge_value)])
        pairs.sort(key=lambda pair: cast(int, pair[0]))
        if len({pair[0] for pair in pairs}) != len(pairs):
            raise FeatureParityError("duplicate valued edge destination")
        return ["valued", pairs]
    if isinstance(value, (tuple, list, set, frozenset)):
        destinations = list(value)
        if any(not isinstance(x, int) or isinstance(x, bool) for x in destinations):
            raise FeatureParityError("unvalued edge destination is not TF node ID")
        if len(set(destinations)) != len(destinations):
            raise FeatureParityError("duplicate unvalued edge destination")
        return ["unvalued", sorted(destinations)]
    raise FeatureParityError(f"unsupported TF edge type: {type(value).__name__}")


def _canonical_row(source: int, value: object, *, kind: FeatureKind) -> list[object]:
    if not isinstance(source, int) or isinstance(source, bool) or source < 1:
        raise FeatureParityError("feature source must be positive TF node ID")
    return [source, _typed_scalar(value) if kind == "node" else _canonical_edge(value)]


def _encode_row(row: list[object]) -> bytes:
    return (json.dumps(row, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def _ordered_rows(items: Iterable[tuple[int, object]], *,
                  kind: FeatureKind) -> Iterable[list[object]]:
    # Materialize at most one feature's annotations, not the entire graph.
    ordered = sorted(
        (_canonical_row(src, val, kind=kind) for src, val in items),
        key=lambda row: cast(int, row[0]),
    )
    previous = 0
    for row in ordered:
        if cast(int, row[0]) == previous:
            raise FeatureParityError(f"duplicate feature source node {previous}")
        previous = cast(int, row[0])
        yield row


def fingerprint_feature_items(
    items: Iterable[tuple[int, object]], *, kind: FeatureKind,
) -> str:
    digest = hashlib.sha256()
    digest.update((kind + "\n").encode())
    for row in _ordered_rows(items, kind=kind):
        digest.update(_encode_row(row))
    return digest.hexdigest()


def compare_feature_streams(
    name: str,
    baseline: Iterable[tuple[int, object]],
    candidate: Iterable[tuple[int, object]],
    *,
    kind: FeatureKind,
) -> dict[str, str | int]:
    """Compare actual typed values; report first mismatch without source data."""
    if not name or kind not in ("node", "edge"):
        raise FeatureParityError("feature name/kind missing")
    left_rows = _ordered_rows(baseline, kind=kind)
    right_rows = _ordered_rows(candidate, kind=kind)
    digest = hashlib.sha256()
    digest.update((kind + "\n").encode())
    count = 0
    for left, right in itertools.zip_longest(left_rows, right_rows):
        if left != right:
            node = (left or right or [None])[0]
            raise FeatureParityError(
                f"{kind} feature {name!r} mismatch at TF source node {node!r}"
            )
        assert left is not None
        digest.update(_encode_row(left))
        count += 1
    return {"feature": name, "kind": kind, "annotated_nodes": count,
            "sha256": digest.hexdigest()}


def compare_native_and_rust(
    native: Any,
    rust: Any,
    *,
    node_features: Iterable[str],
    edge_features: Iterable[str],
) -> dict[str, dict[str, str | int]]:
    """Exhaustively compare every declared node and edge feature."""
    result: dict[str, dict[str, str | int]] = {}
    for kind, features, namespace in (
        ("node", node_features, "F"),
        ("edge", edge_features, "E"),
    ):
        for name in sorted(features):
            label = f"{kind}:{name}"
            base = getattr(getattr(native, namespace), name, None)
            trial = getattr(getattr(rust, namespace), name, None)
            if base is None or trial is None:
                raise FeatureParityError(f"missing {label} API accessor")
            if not callable(getattr(base, "items", None)) or not callable(
                getattr(trial, "items", None)
            ):
                raise FeatureParityError(f"{label} items() unavailable")
            result[label] = compare_feature_streams(
                name, base.items(), trial.items(), kind=cast(FeatureKind, kind),
            )
    return result
