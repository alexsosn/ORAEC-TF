"""RED-first equivalence tests for a non-production TF levUp optimization prototype.

The oracle is Text-Fabric 13.1's real prepare.levUp(), not our writer or
independent corpus audit. The proposed implementation is never used there.
"""

from __future__ import annotations

from random import Random
from typing import Any

from tf.core import prepare

from oraec_tf.experimental_levup import candidate_superset_levup


def _compare(
    max_slot: int, non_slot_membership: tuple[tuple[int, ...], ...],
    ranks: tuple[int, ...],
) -> None:
    max_node = max_slot + len(non_slot_membership)
    warp_otype = (tuple("node" for _ in non_slot_membership), max_slot, max_node, "word")
    warp_oslots = (non_slot_membership,)
    messages: list[str] = []
    info = messages.append
    baseline: Any = prepare.levUp(info, info, warp_otype, warp_oslots, ranks)
    alternative = candidate_superset_levup(
        info, info, warp_otype, warp_oslots, ranks,
    )
    assert len(baseline) == len(alternative) == max_node
    # Compare EACH original TF embedder sequence, including rank order.
    for node_id, (native, proposed) in enumerate(zip(baseline, alternative), start=1):
        assert native == proposed, f"node {node_id}: changed native TF embedding"
    assert alternative == baseline


def test_candidate_superset_levup_preserves_overlapping_and_empty_nodes() -> None:
    # Slot 3 has three embedding nodes; 7 has no slots, 8 skips a slot;
    # 9 spans the graph and 10 has identical oslots to an earlier node.
    graph = (
        (1, 2, 3),
        (3, 4),
        (),
        (2, 4, 5),
        (1, 2, 3, 4, 5),
        (1, 2, 3),
    )
    ranks = (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
    _compare(5, graph, ranks)


def test_candidate_superset_levup_preserves_isolated_and_anchor_slots() -> None:
    graph = ((1,), (), (1, 3), (3,), (5,), (2, 4))
    ranks = tuple(range(1, 12))
    _compare(5, graph, ranks)


def test_candidate_superset_levup_matches_native_for_deterministic_random_graphs() -> None:
    rng = Random(82542)
    for _ in range(120):
        n_slots = rng.randrange(1, 23)
        n_nodes = rng.randrange(1, 30)
        graph = tuple(
            tuple(
                slot for slot in range(1, n_slots + 1)
                if rng.randrange(5) == 0
            )
            for _ in range(n_nodes)
        )
        ranks = list(range(1, n_slots + n_nodes + 1))
        rng.shuffle(ranks)
        _compare(n_slots, graph, tuple(ranks))
