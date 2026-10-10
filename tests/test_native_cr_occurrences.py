"""RED: native carriage-return occurrence graph, never packed offset lists (#42)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tf.fabric import Fabric

from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.text_codec import (
    ControlCharacterError,
    NativeCRIndex,
    encode_node_features,
)
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


@pytest.mark.parametrize(
    ("raw", "clean", "positions"),
    [
        ("\r", "", (0,)),
        ("A\rB", "AB", (1,)),
        ("A\r\nB", "A\nB", (1,)),
        ("\r\rA", "A", (0, 1)),
        ("A\r", "A", (1,)),
        ("𓀀\r𓇾", "𓀀𓇾", (1,)),
        ("", "", ()),
        ("No CR", "No CR", ()),
    ],
)
def test_native_cr_encoder_returns_scalar_and_typed_offsets(
    raw: str, clean: str, positions: tuple[int, ...],
) -> None:
    scalars, occurrences = encode_node_features("text", {"bibliography": raw})
    assert scalars == {"bibliography": clean}
    assert occurrences == tuple(("bibliography", position) for position in positions)
    assert all("_cr_offsets" not in feature for feature in scalars)


def _sample(tf_dir: Path) -> tuple[str, str]:
    bibliography = "A\r\r\nB\r"
    translation = "T\r\nU"
    record = TextIR(
        oraec_id="oraec42",
        title="Source\r title",
        bibliography=bibliography,
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Editor",
            sources=("https://example.invalid/oraec",),
        ),
        sentences=(
            SentenceIR(
                index=1,
                translation=translation,
                tokens=(
                    TokenIR(
                        token_id="oraec42-1-1", written_form="𓀀\r𓇾",
                        hiero="𓀀𓇾",
                    ),
                ),
            ),
            SentenceIR(index=2, translation="", tokens=()),
        ),
    )
    write_tf((record,), tf_dir, source_revision=REVISION)
    return bibliography, translation


def test_native_cr_occurrences_are_queryable_without_packed_strings(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "tf"
    bibliography, translation = _sample(corpus)
    api = Fabric(locations=str(corpus), silent="deep").loadAll(silent="deep")
    assert api
    text = api.F.otype.s("text")[0]
    sentence = api.L.d(text, otype="sentence")[0]
    word = api.L.d(sentence, otype="word")[0]
    crs = api.F.otype.s("cr_occurrence")
    assert len(crs) == 6  # title 1 + bibliography 3 + translation 1 + word 1
    assert all(type(api.F.cr_offset.v(cr)) is int for cr in crs)
    assert all(len(api.E.cr_owner.f(cr)) == 1 for cr in crs)
    assert not tuple(p.name for p in corpus.glob("*_cr_offsets.tf"))
    index = NativeCRIndex(api)
    assert index.restore(text, "bibliography") == bibliography
    assert index.restore(text, "title") == "Source\r title"
    assert index.restore(sentence, "translation") == translation
    assert index.restore(word, "written_form") == "𓀀\r𓇾"
    assert index.restore(sentence, "sentence_index") == 1
    assert index.restore(text, "condition") is None

    matches = [
        cr for cr in crs
        if api.F.cr_feature.v(cr) == "bibliography"
        and tuple(api.E.cr_owner.f(cr)) == (text,)
    ]
    assert sorted(api.F.cr_offset.v(cr) for cr in matches) == [1, 2, 5]


def test_native_cr_index_rejects_forged_orphan_and_duplicate_offsets(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "tf"
    _sample(corpus)
    api = Fabric(locations=str(corpus), silent="deep").loadAll(silent="deep")
    assert api
    crs = api.F.otype.s("cr_occurrence")
    index = NativeCRIndex(api)
    text = api.F.otype.s("text")[0]
    assert index.restore(text, "bibliography") == "A\r\r\nB\r"

    offset = crs[1]
    original = api.F.cr_offset.data[offset]
    api.F.cr_offset.data[offset] = -1
    with pytest.raises(ControlCharacterError, match="offset|position"):
        NativeCRIndex(api)
    api.F.cr_offset.data[offset] = original

    api.F.cr_feature.data[offset] = "not_existing_feature"
    with pytest.raises(ControlCharacterError, match="feature"):
        NativeCRIndex(api)



def test_native_cr_occurrence_rejects_orphaned_and_wrong_span_owner(
    tmp_path: Path,
) -> None:
    """Tampering with real TF edge data must never silently transfer CR."""
    corpus = tmp_path / "tf"
    _sample(corpus)
    api = Fabric(locations=str(corpus), silent="deep").loadAll(silent="deep")
    assert api
    cr = api.F.otype.s("cr_occurrence")[0]
    original_owners = api.E.cr_owner.data[cr]
    api.E.cr_owner.data[cr] = set()
    with pytest.raises(ControlCharacterError, match="owner"):
        NativeCRIndex(api)
    api.E.cr_owner.data[cr] = original_owners

    # A different valid owner node does not have the same source slot span.
    actual_owner = next(iter(original_owners))
    other = next(n for n in api.F.otype.s("word") if n != actual_owner)
    api.E.cr_owner.data[cr] = {other}
    with pytest.raises(ControlCharacterError, match="feature|oslots|owner"):
        NativeCRIndex(api)



def test_native_cr_index_rejects_duplicate_source_coordinate(
    tmp_path: Path,
) -> None:
    """Different TF occurrence nodes cannot claim the same owner/offset."""
    corpus = tmp_path / "tf"
    _sample(corpus)
    api = Fabric(locations=str(corpus), silent="deep").loadAll(silent="deep")
    assert api
    text = api.F.otype.s("text")[0]
    bibliography_crs = [
        n for n in api.F.otype.s("cr_occurrence")
        if api.F.cr_feature.v(n) == "bibliography"
        and text in api.E.cr_owner.f(n)
    ]
    assert len(bibliography_crs) == 3
    first, second = bibliography_crs[:2]
    api.F.cr_offset.data[second] = api.F.cr_offset.v(first)
    with pytest.raises(ControlCharacterError, match="duplicate"):
        NativeCRIndex(api)
