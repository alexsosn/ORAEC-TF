"""RED first: experimental streaming TF source-only count probe for #64.

The fast probe is only compared to the already-required native Fabric reload;
it is not a substitute for the uncached exhaustive TF validation/auditor.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tf.fabric import Fabric

from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.tf_count_probe import ProbeError, probe_tf_counts
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _graph(tmp_path: Path) -> Path:
    corpus = (
        TextIR(
            oraec_id="oraec1",
            title="TF count oracle",
            credits=CreditsIR(
                license="cc-by-sa-4.0",
                author="Editor",
                sources=("https://example.invalid/source",),
            ),
            sentences=(
                SentenceIR(
                    index=1,
                    translation="One\r\nvalue",
                    tokens=(
                        TokenIR(token_id="oraec1-1-1", written_form="nṯr"),
                        TokenIR(token_id="oraec1-1-2", written_form="pr"),
                    ),
                ),
                SentenceIR(index=2, translation="", tokens=()),
            ),
        ),
    )
    output = tmp_path / "tf"
    write_tf(corpus, output, source_revision=REVISION)
    return output


def test_native_source_count_probe_matches_actual_fabric_on_real_graph(
    tmp_path: Path,
) -> None:
    output = _graph(tmp_path)
    api = Fabric(locations=str(output), silent="deep").load(
        "oraec_id sentence_index token_id", silent="deep"
    )
    assert api
    words = api.F.otype.s("word")
    counts = {
        "texts": len(api.F.otype.s("text")),
        "sentences": len(api.F.otype.s("sentence")),
        "tokens": sum(api.F.token_id.v(word) is not None for word in words),
        "technical_anchors": len(words) - sum(
            api.F.token_id.v(word) is not None for word in words
        ),
        "slots": len(words),
        "cr_occurrences": len(api.F.otype.s("cr_occurrence")),
    }
    assert counts == {
        "texts": 1, "sentences": 2, "tokens": 2,
        "technical_anchors": 1, "slots": 3, "cr_occurrences": 1,
    }
    assert probe_tf_counts(output) == counts


@pytest.mark.parametrize("corruption", ["missing-token", "nonword-token", "duplicate"])
def test_native_count_probe_rejects_corrupted_feature_identity(
    tmp_path: Path, corruption: str,
) -> None:
    output = _graph(tmp_path)
    token_feature = output / "token_id.tf"
    if corruption == "missing-token":
        token_feature.unlink()
    else:
        with token_feature.open("a", encoding="utf-8") as stream:
            stream.write(
                "999999\tforged-token\n" if corruption == "nonword-token"
                else "1\tduplicate-token\n"
            )
    with pytest.raises(ProbeError, match="token_id|word|duplicate|missing"):
        probe_tf_counts(output)


def test_native_count_probe_rejects_unknown_otype_without_fabric_cache(
    tmp_path: Path,
) -> None:
    output = _graph(tmp_path)
    otype = output / "otype.tf"
    text = otype.read_text(encoding="utf-8")
    assert "word" in text
    otype.write_text(text.replace("word", "wrod"), encoding="utf-8")
    with pytest.raises(ProbeError, match="otype|word|unknown"):
        probe_tf_counts(output)


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_source_count_probe_matches_real_tf_with_platform_newlines(
    tmp_path: Path, line_ending: bytes,
) -> None:
    """Text-Fabric writes CRLF on Windows: exact native counts must still pass."""
    root = _graph(tmp_path)
    expected = probe_tf_counts(root)
    assert expected["cr_occurrences"] == 1
    for filename in ("otype.tf", "token_id.tf"):
        target = root / filename
        original = target.read_bytes()
        assert b"\r" not in original
        target.write_bytes(original.replace(b"\n", line_ending))
    assert probe_tf_counts(root) == expected


@pytest.mark.parametrize("corruption", ["mixed", "embedded-cr"])
def test_source_count_probe_rejects_mixed_or_embedded_cr(
    tmp_path: Path, corruption: str,
) -> None:
    root = _graph(tmp_path)
    for filename in ("otype.tf", "token_id.tf"):
        target = root / filename
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    target = root / "otype.tf"
    body = target.read_bytes()
    if corruption == "mixed":
        body = body.replace(b"@schemaVersion=3\r\n", b"@schemaVersion=3\n")
    else:
        body = body.replace(b"@schemaVersion=3\r\n", b"@schemaVersion=3\rtr\r\n")
    assert body != target.read_bytes()
    target.write_bytes(body)
    with pytest.raises(ProbeError, match="CR|newline|metadata|header"):
        probe_tf_counts(root)
