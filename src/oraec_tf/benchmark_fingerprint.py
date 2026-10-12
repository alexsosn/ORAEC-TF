"""Pure fail-closed graph equivalence checks for compiled-corpus research.

This module does not import Text-Fabric or Context-Fabric, and cannot change
the ORAEC converter or independent source validator.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Callable, Iterable
from typing import Any


def digest_graph(
    *,
    max_slot: int,
    max_node: int,
    node_type: Callable[[int], str | None],
    node_slots: Callable[[int], Iterable[int]],
    node_parents: Callable[[int], Iterable[int]],
) -> str:
    """SHA256 of ALL ordered types, slot memberships, and levUp tuples.

    Length-prefix every sequence to disambiguate structure and retain parent
    ordering. Stable across native tuple and CF numpy/CSR-backed objects.
    """
    h = hashlib.sha256()
    h.update(struct.pack("<QQ", max_slot, max_node))
    for node in range(1, max_node + 1):
        typ = node_type(node)
        if typ is None:
            raise ValueError(f"missing otype at node {node}")
        encoded = str(typ).encode("utf-8")
        h.update(struct.pack("<Q", len(encoded)))
        h.update(encoded)
        if node > max_slot:
            slots = tuple(int(n) for n in node_slots(node))
            h.update(struct.pack("<Q", len(slots)))
            for n in slots:
                h.update(struct.pack("<Q", n))
        parents = tuple(int(n) for n in node_parents(node))
        h.update(struct.pack("<Q", len(parents)))
        for n in parents:
            h.update(struct.pack("<Q", n))
    return h.hexdigest()


def verify_compiled_metadata(meta: dict[str, Any], expected: set[str]) -> None:
    features = meta.get("features", {})
    actual = set(features.get("node", ())) | set(features.get("edge", ()))
    if actual != expected:
        raise ValueError(
            "compiled feature inventory mismatch: "
            f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def verify_equivalence(native: dict[str, Any], compiled: dict[str, Any]) -> None:
    if not compiled.get("loaded_from_cfm"):
        raise ValueError("compiled data did not load from .cfm mmap")
    for field in (
        "fingerprint", "max_slot", "max_node", "feature_names",
        "texts", "sentences", "cr_occurrences",
    ):
        if native[field] != compiled[field]:
            raise ValueError(f"native-vs-CFM {field} mismatch")


