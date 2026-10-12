"""Research-only, unused-in-production prototype of Text-Fabric levUp.

Native Text-Fabric v13.1's tf.core.prepare.levUp is the reference oracle.
Neither the ORAEC writer, tf-build validation nor the independent auditor
imports this module. Its behavior and performance need real-source validation
before considering an upstream optimization proposal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence


def candidate_superset_levup(
    info: Callable[[str], object],
    error: Callable[[str], object],
    otype: tuple[Sequence[str], int, int, str],
    oslots: tuple[Sequence[Sequence[int]], ...],
    rank: Sequence[int],
) -> tuple[tuple[int, ...], ...]:
    """Compute every native embedding tuple via candidate slot-set containment.

    A node *m* embeds node *n* iff every slot in oslots[n] occurs in
    oslots[m]. Native Text-Fabric allocates repeated intermediate posting-set
    intersections. We choose the smallest existing inverted posting as a
    candidate list and test membership in the others directly; no contiguous
    assumption or cached copies of large per-node slot sets are needed.

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

    # An empty oslots list has no non-slot embedders in native Text-Fabric.
    # For a nonempty list, native computes the intersection of inverted
    # postings. Iterate the smallest posting (fewest candidate parents), then
    # test membership in all other postings. This uses no cached/frozenset
    # copies of entire text-node slot sets.
    embedders: list[tuple[int, ...]] = []
    for node in range(1, max_node + 1):
        if node <= max_slot:
            candidates = inverse.get(node, set())
            eligible = (candidate for candidate in candidates if candidate != node)
        else:
            slots = membership[node - max_slot - 1]
            if not slots:
                embedders.append(())
                continue
            # Materialize all lookups first so invalid missing slot postings
            # still raise the same KeyError as native prepare.levUp().
            postings = tuple(inverse[slot] for slot in slots)
            pivot = min(postings, key=len)
            eligible = (
                candidate for candidate in pivot
                if candidate != node
                and all(candidate in posting for posting in postings)
            )
        ordered = tuple(sorted(
            eligible,
            key=lambda candidate: -rank[candidate - 1],
        ))
        embedders.append(ordered)

    seen: dict[tuple[int, ...], tuple[int, ...]] = {}
    result: list[tuple[int, ...]] = []
    for embedding in embedders:
        result.append(seen.setdefault(embedding, embedding))
    return tuple(result)
