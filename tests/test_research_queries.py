"""RED-first real-TF researcher query recipes (issue #10)."""

from __future__ import annotations

from pathlib import Path

from tf.fabric import Fabric

from oraec_tf.ir import ControlledValueIR, CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.research_queries import (
    find_text,
    hierarchy_path,
    lemma_occurrences,
    ordered_idnos,
    texts_with_cv_label,
    words_with_pos,
)
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def test_research_queries_run_against_real_native_fabric(tmp_path: Path) -> None:
    record = TextIR(
        oraec_id="oraec42",
        title="Source title",
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Research Editor",
            sources=("https://example.invalid/source",),
        ),
        sentences=(
            SentenceIR(
                index=1,
                translation="translation",
                tokens=(
                    TokenIR(
                        token_id="oraec42-1-1",
                        written_form="nṯr",
                        lemma_id="L1",
                        lemma_form="nṯr",
                        pos="substantive",
                        hiero="𓀀",
                        line_count="[Vs 1]",
                    ),
                ),
            ),
        ),
        dates=(ControlledValueIR(kind="date", cv_id="D1", label="Era A"),),
        idnos=("same", "same"),
    )
    output = tmp_path / "tf"
    write_tf((record,), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    assert api
    text = find_text(api, "oraec42")
    assert text is not None
    assert text in api.F.otype.s("text")
    assert find_text(api, "oraec-no-such-text") is None

    words = words_with_pos(api, "substantive")
    assert len(words) == 1
    assert api.F.written_form.v(words[0]) == "nṯr"
    assert lemma_occurrences(api, "L1") == words
    assert texts_with_cv_label(api, "date", "Era A") == (text,)
    assert ordered_idnos(api, text) == ("same", "same")
    assert hierarchy_path(api, text) == ()
    assert api.T.sectionFromNode(words[0]) == ("oraec42", 1)
    assert api.T.text(words[0], fmt="text-hiero") == "𓀀 "
    assert list(api.S.search("word pos=substantive", silent="deep")) == [
        (words[0],)
    ]


def test_research_queries_reject_unsupported_cv_family(tmp_path: Path) -> None:
    text = TextIR(
        oraec_id="oraec1",
        title="Only text",
        sentences=(
            SentenceIR(index=1, translation="", tokens=(
                TokenIR(token_id="oraec1-1-1", written_form="X"),
            )),
        ),
        credits=CreditsIR(license="cc-by-sa-4.0", author="A", sources=()),
    )
    output = tmp_path / "tf"
    write_tf((text,), output, source_revision=REVISION)
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    import pytest

    with pytest.raises(ValueError, match="unsupported controlled-vocabulary"):
        texts_with_cv_label(api, "made_up_domain", "A")
