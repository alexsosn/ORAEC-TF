"""TDD controls for lossless native carriage-return transport (ADR 0006)."""

from __future__ import annotations

import pytest

from oraec_tf.text_codec import (
    ControlCharacterError,
    encode_node_features,
    restore_source_string,
)


@pytest.mark.parametrize(
    ("value", "transport", "positions"),
    [
        ("A\r\nB", "A\nB", "1"),
        ("A\rB", "AB", "1"),
        ("\r\rA", "A", "0,1"),
        ("A\nB", "A\nB", None),
        ("", "", None),
        ("\\r literal and \r real", "\\r literal and  real", "15"),
        ("𓀀\r𓃀", "𓀀𓃀", "1"),
    ],
)
def test_roundtrip_exact_source_unicode(
    value: str, transport: str, positions: str | None,
) -> None:
    result = encode_node_features("text", {"bibliography": value})
    assert result["bibliography"] == transport
    assert result.get("text_cr_offsets") == (
        None if positions is None else f"bibliography={positions}"
    )
    assert restore_source_string(
        result["bibliography"], result.get("text_cr_offsets"), "bibliography"
    ) == value


def test_multiple_original_features_share_one_sparse_node_metadata_field() -> None:
    fields = {"title": "one\rtwo", "bibliography": "a\r\nb", "license": "cc"}
    encoded = encode_node_features("text", fields)
    assert encoded["title"] == "onetwo"
    assert encoded["bibliography"] == "a\nb"
    assert encoded["text_cr_offsets"] == "bibliography=1|title=3"
    for feature in ("title", "bibliography"):
        assert restore_source_string(
            encoded[feature], encoded["text_cr_offsets"], feature
        ) == fields[feature]
    assert restore_source_string(
        encoded["license"], encoded["text_cr_offsets"], "license"
    ) == "cc"


@pytest.mark.parametrize(
    "corrupt",
    [
        "bibliography=2,1",
        "bibliography=1,1",
        "bibliography=-1",
        "bibliography=a",
        "bibliography=999",
        "bibliography=",
        "bibliography=1|bibliography=2",
        "bibliography=0|not-an-identifier=1",
    ],
)
def test_reconstruction_fails_closed_on_invalid_offset_grammar(
    corrupt: str,
) -> None:
    with pytest.raises(ControlCharacterError):
        restore_source_string("a", corrupt, "bibliography")


def test_unspecified_source_strings_have_no_transport_metadata() -> None:
    result = encode_node_features("sentence", {"translation": "\nordinary"})
    assert result == {"translation": "\nordinary"}
    assert restore_source_string(result["translation"], None, "translation") == "\nordinary"


def test_reserved_codec_field_cannot_be_supplied_by_source() -> None:
    with pytest.raises(ControlCharacterError, match="reserved"):
        encode_node_features("word", {"word_cr_offsets": "token_id=0"})
