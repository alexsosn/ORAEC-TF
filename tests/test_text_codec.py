"""TDD controls for lossless native CR occurrences under ADR 0007."""

from __future__ import annotations

import pytest

from oraec_tf.text_codec import ControlCharacterError, encode_node_features


@pytest.mark.parametrize(
    ("original", "transport", "offsets"),
    [
        ("A\r\nB", "A\nB", (1,)),
        ("A\rB", "AB", (1,)),
        ("\r\rA", "A", (0, 1)),
        ("A\nB", "A\nB", ()),
        ("", "", ()),
        ("\\r literal and \r real", "\\r literal and  real", (15,)),
        ("𓀀\r𓃀", "𓀀𓃀", (1,)),
    ],
)
def test_native_codec_retains_exact_codepoint_locations(
    original: str, transport: str, offsets: tuple[int, ...],
) -> None:
    data, occurrences = encode_node_features("text", {"bibliography": original})
    assert data == {"bibliography": transport}
    assert occurrences == tuple(("bibliography", i) for i in offsets)


def test_multiple_fields_are_individual_native_occurrences() -> None:
    fields = {"title": "one\rtwo", "bibliography": "a\r\nb", "license": "cc"}
    scalars, occurrences = encode_node_features("text", fields)
    assert scalars == {"title": "onetwo", "bibliography": "a\nb", "license": "cc"}
    assert occurrences == (("title", 3), ("bibliography", 1))
    assert all(not key.endswith("_cr_offsets") for key in scalars)


def test_missing_and_empty_source_fields_are_unchanged() -> None:
    clean, positions = encode_node_features(
        "sentence", {"translation": "", "sentence_index": 1}
    )
    assert clean == {"translation": "", "sentence_index": 1}
    assert positions == ()


@pytest.mark.parametrize("node_type", ["bogus", "cr_occurrence", ""])
def test_unknown_annotated_source_owner_is_rejected(node_type: str) -> None:
    with pytest.raises(ControlCharacterError, match="node type"):
        encode_node_features(node_type, {"translation": "x\ry"})


@pytest.mark.parametrize("feature", ["word_cr_offsets", "cr_feature", "cr_offset"])
def test_old_packed_or_internal_native_features_cannot_enter_source(
    feature: str,
) -> None:
    with pytest.raises(ControlCharacterError, match="reserved"):
        encode_node_features("word", {feature: "x"})
