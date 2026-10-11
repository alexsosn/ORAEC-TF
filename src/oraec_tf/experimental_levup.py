"""Research-only, unused-in-production prototype of Text-Fabric levUp.

Native Text-Fabric v13.1's tf.core.prepare.levUp is the reference oracle.
Neither the ORAEC writer, tf-build validation nor the independent auditor
imports this module. Its behavior and performance need real-source validation
before considering an upstream optimization proposal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache


def candidate_superset_levup(
    info: Callable[[str], object],
    error: Callable[[str], object],
    otype: tuple[Sequence[str], int, int, str],
    oslots: tuple[Sequence[Sequence[int]], ...],
    rank: Sequence[int],
) -> tuple[tuple[int, ...], ...]:
    """Compute every native embedding tuple via candidate slot-set containment.

    A node *m* embeds node *n* iff oslots[n] is a subset of oslots[m].
    Native Text-Fabric implements this as repeated posting-list intersections.
    We restrict candidates using the first required slot, then test complete
    containment with compiled set operations; no contiguous-slot assumption.

    This is an experimental pure function; it MUST NOT be used to bypass
    unmodified Text-Fabric loading in the independent corpus auditor.
    """
    del info, error
    _, max_slot, max_node, _ = otype
    membership = oslots[0]
    inverse: dict[int, set[int]] = {}
    for offset, slots in enumerate(membership):
        candidate_node = max_slot + offset + 1
        for slot in slots:
            inverse.setdefault(slot, set()).add(candidate_node)

    @lru_cache(maxsize=2048)
    def node_slot_set(node: int) -> frozenset[int]:
        return frozenset(membership[node - max_slot - 1])

    embedders: list[tuple[int, ...]] = []
    for node in range(1, max_node + 1):
        if node <= max_slot:
            candidates = inverse.get(node, set())
        else:
            slots = membership[node - max_slot - 1]
            if not slots:
                embedders.append(())
                continue
            required = frozenset(slots)
            candidates = {
                candidate for candidate in inverse.get(slots[0], set())
                if candidate != node
                and len(node_slot_set(candidate)) >= len(required)
                and node_slot_set(candidate).issuperset(required)
            }
        ordered = tuple(sorted(
            (candidate for candidate in candidates if candidate != node),
            key=lambda candidate: -rank[candidate - 1],
        ))
        embedders.append(ordered)

    seen: dict[tuple[int, ...], tuple[int, ...]] = {}
    result: list[tuple[int, ...]] = []
    for embedding in embedders:
        result.append(seen.setdefault(embedding, embedding))
    return tuple(result)
