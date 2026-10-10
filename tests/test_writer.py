"""RED-first Text-Fabric round-trip tests for issue #6, not test doubles."""

from __future__ import annotations

from pathlib import Path

from tf.fabric import Fabric

from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _texts() -> tuple[TextIR, ...]:
    return (
        TextIR(
            oraec_id="oraec1",
            title="First source text",
            sentences=(
                SentenceIR(
                    index=1,
                    translation="",
                    tokens=(
                        TokenIR(
                            token_id="oraec1-1-1",
                            written_form="nṯr",
                            hiero="[⯑]�",
                            line_count=" [Vs 1] ",
                            pos="N",
                        ),
                    ),
                ),
                SentenceIR(index=2, translation="", tokens=()),
            ),
            credits=CreditsIR(
                license="cc-by-sa-4.0",
                author="Credited A",
                sources=("https://example.invalid/source",),
            ),
        ),
        TextIR(
            oraec_id="oraec2",
            title="Second source text",
            sentences=(
                SentenceIR(
                    index=1,
                    translation="Different translation",
                    tokens=(
                        TokenIR(
                            token_id="oraec2-1-1",
                            written_form="ḫpr",
                            line_count="0",
                        ),
                    ),
                ),
            ),
            credits=CreditsIR(
                license="cc-by-sa-4.0",
                author="Credited B",
                sources=("https://example.invalid/source",),
            ),
        ),
    )


def test_write_tf_preserves_word_sentence_text_and_technical_anchor(tmp_path: Path) -> None:
    output = tmp_path / "tf"
    write_tf(_texts(), output, source_revision=REVISION)

    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id title license sentence_index translation "
        "token_id written_form hiero line_count pos is_anchor trailer",
        silent="deep",
    )

    words = api.F.otype.s("word")
    sentences = api.F.otype.s("sentence")
    texts = api.F.otype.s("text")
    assert len(words) == 3  # two source tokens + exactly one technical anchor
    assert len(sentences) == 3
    assert len(texts) == 2

    source_tokens = [w for w in words if api.F.token_id.v(w) is not None]
    anchors = [w for w in words if api.F.is_anchor.v(w) == 1]
    assert len(source_tokens) == 2
    assert len(anchors) == 1
    assert api.F.token_id.v(anchors[0]) is None
    assert api.F.written_form.v(anchors[0]) is None
    assert api.F.trailer.v(anchors[0]) == ""

    first_word = source_tokens[0]
    assert api.F.token_id.v(first_word) == "oraec1-1-1"
    assert api.F.written_form.v(first_word) == "nṯr"
    assert api.F.hiero.v(first_word) == "[⯑]�"
    assert api.F.line_count.v(first_word) == " [Vs 1] "
    assert api.F.pos.v(first_word) == "N"

    first_text = next(n for n in texts if api.F.oraec_id.v(n) == "oraec1")
    first_sentences = api.L.d(first_text, otype="sentence")
    assert len(first_sentences) == 2
    assert [api.F.sentence_index.v(n) for n in first_sentences] == [1, 2]
    assert api.F.translation.v(first_sentences[0]) == ""
    assert api.F.translation.v(first_sentences[1]) == ""
    assert api.L.d(first_sentences[1], otype="word") == tuple(anchors)
    assert api.F.title.v(first_text) == "First source text"
    assert api.F.license.v(first_text) == "cc-by-sa-4.0"


def test_write_tf_retains_missingness_without_sentinel(tmp_path: Path) -> None:
    output = tmp_path / "tf"
    write_tf(_texts(), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").load(
        "token_id hiero line_count pos is_anchor written_form",
        silent="deep",
    )
    second_word = next(
        n for n in api.F.otype.s("word")
        if api.F.token_id.v(n) == "oraec2-1-1"
    )
    assert api.F.hiero.v(second_word) is None
    assert api.F.pos.v(second_word) is None
    assert api.F.line_count.v(second_word) == "0"
