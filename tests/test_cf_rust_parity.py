"""RED-first typed feature parity for optional Rust Context-Fabric (#91).

Small adversarial fixtures do not require Context-Fabric. The dedicated Python
3.13 workflow must separately exercise the published 0.6.0rc1 wheel.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from oraec_tf.cf_rust_parity import (
    FeatureParityError,
    compare_feature_streams,
    fingerprint_feature_items,
)


@dataclass
class Cases:
    baseline: list[tuple[int, object]]
    other: list[tuple[int, object]]


@pytest.mark.parametrize("different", [
    Cases([(1, "nṯr"), (2, "𓀀")], [(1, "ntr"), (2, "𓀀")]),
    Cases([(1, None), (2, "")], [(1, ""), (2, "")]),
    Cases([(1, 42)], [(1, "42")]),
    Cases([(1, "a\r\nb")], [(1, "a\nb")]),
    Cases([(1, "")], []),
])
def test_a_changed_node_feature_value_or_missingness_fails_closed(
    different: Cases,
) -> None:
    with pytest.raises(FeatureParityError, match="node|mismatch"):
        compare_feature_streams(
            "written_form", different.baseline, different.other, kind="node"
        )


@pytest.mark.parametrize("baseline,other", [
    ([(5, {101: "mapping_oraec_karnak.tsv", 102: "mapping_oraec_karnak.tsv"})],
     [(5, {101: "mapping_oraec_karnak.tsv"})]),
    ([(5, {101: "mapping_oraec_karnak.tsv"})],
     [(5, {101: "mapping_oraec_lemmata_karnak.tsv"})]),
    ([(5, {101: None})], [(5, (101,))]),
    ([(5, {101: ""})], [(5, {101: None})]),
])
def test_corrupted_valued_edge_targets_and_provenance_fail(
    baseline: list[tuple[int, object]], other: list[tuple[int, object]],
) -> None:
    with pytest.raises(FeatureParityError, match="edge|mismatch"):
        compare_feature_streams("external", baseline, other, kind="edge")


def test_feature_inventory_and_edge_ordering_preserved_canonically() -> None:
    rows = [(1, {101: "file.tsv", 102: "file.tsv"}), (9, {100: "x"})]
    reordered = [(9, {100: "x"}), (1, {102: "file.tsv", 101: "file.tsv"})]
    assert fingerprint_feature_items(rows, kind="edge") == fingerprint_feature_items(
        reordered, kind="edge"
    )
    summary = compare_feature_streams("external", rows, reordered, kind="edge")
    assert summary["annotated_nodes"] == 2
    assert summary["sha256"]


def test_node_sequence_normalization_does_not_forge_numeric_strings() -> None:
    assert fingerprint_feature_items([(1, "001")], kind="node") != (
        fingerprint_feature_items([(1, 1)], kind="node")
    )


def test_empty_node_feature_cannot_impersonate_nonempty_feature() -> None:
    assert fingerprint_feature_items([], kind="node") != (
        fingerprint_feature_items([(1, None)], kind="node")
    )
