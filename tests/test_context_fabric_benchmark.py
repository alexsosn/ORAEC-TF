"""RED-first safeguards for the real-corpus Context-Fabric comparison (#84)."""

from __future__ import annotations

import pytest

from scripts.benchmark_context_fabric import (
    digest_graph,
    verify_compiled_metadata,
    verify_equivalence,
)


def _graph(
    *,
    change_parent: bool = False,
    change_slots: bool = False,
    change_type: bool = False,
) -> str:
    types = {1: "word", 2: "word", 3: "word", 4: "sentence", 5: "text"}
    slots = {4: (1, 2), 5: (1, 2, 3)}
    parents = {
        1: (4, 5), 2: (4, 5), 3: (5,), 4: (5,), 5: (),
    }
    if change_parent:
        parents[1] = (5, 4)
    if change_slots:
        slots[5] = (1, 3)
    if change_type:
        types[4] = "lex"
    return digest_graph(
        max_slot=3,
        max_node=5,
        node_type=types.__getitem__,
        node_slots=slots.__getitem__,
        node_parents=parents.__getitem__,
    )


def test_streaming_graph_digest_is_deterministic_and_complete() -> None:
    assert _graph() == _graph()
    assert len(_graph()) == 64
    assert _graph(change_parent=True) != _graph()
    assert _graph(change_slots=True) != _graph()
    assert _graph(change_type=True) != _graph()


def test_equivalence_requires_all_node_relationships_and_inventory() -> None:
    native = {
        "fingerprint": _graph(), "max_slot": 3, "max_node": 5,
        "feature_names": ["a", "b"], "texts": 1,
        "sentences": 1, "cr_occurrences": 0,
    }
    compiled = dict(native, loaded_from_cfm=True)
    verify_equivalence(native, compiled)
    with pytest.raises(ValueError, match="fingerprint"):
        verify_equivalence(native, dict(compiled, fingerprint=_graph(change_parent=True)))
    with pytest.raises(ValueError, match="feature_names"):
        verify_equivalence(native, dict(compiled, feature_names=["a"]))
    with pytest.raises(ValueError, match="compiled"):
        verify_equivalence(native, dict(compiled, loaded_from_cfm=False))


def test_compiler_inventory_never_silently_omits_source_features() -> None:
    expected = {"node_text", "node_id", "edge_target"}
    verify_compiled_metadata(
        {
            "features": {
                "node": ["node_id", "node_text"],
                "edge": ["edge_target"],
            }
        },
        expected,
    )
    with pytest.raises(ValueError, match="inventory"):
        verify_compiled_metadata(
            {"features": {"node": ["node_id"], "edge": ["edge_target"]}},
            expected,
        )
    with pytest.raises(ValueError, match="inventory"):
        verify_compiled_metadata({"features": {}}, expected)
