"""RED-first semantic TF fingerprints: only a validated writer timestamp is ignored.

The source corpus is never copied into this test. Real writer-generated native TF
features are created independently at different controlled TF writer times.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from tf.core import data as tf_data

from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.tf_fingerprints import FingerprintError, hash_tf_feature
from oraec_tf.writer import write_tf

REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str,
    at: datetime,
) -> Path:
    monkeypatch.setattr(tf_data, "utcnow", lambda: at.replace(tzinfo=UTC))
    output = tmp_path / name
    text = TextIR(
        oraec_id="oraec1", title="Immutable glyph 𓀀",
        credits=CreditsIR(
            license="cc-by-sa-4.0", author="Editor",
            sources=("https://example.invalid/source",),
        ),
        sentences=(
            SentenceIR(index=1, translation="one\r\ntwo", tokens=(
                TokenIR(token_id="oraec1-1-1", written_form="nṯr"),
            )),
            SentenceIR(index=2, translation="", tokens=()),
        ),
    )
    write_tf((text,), output, source_revision=REVISION)
    return output


def test_real_writer_different_clocks_have_same_semantic_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _graph(tmp_path, monkeypatch, "first", datetime(2026, 10, 11, 8, 0, 0))
    second = _graph(tmp_path, monkeypatch, "second", datetime(2026, 10, 11, 8, 0, 5))
    paths = sorted(p.name for p in first.glob("*.tf") if p.is_file())
    assert paths and "otype.tf" in paths and "oslots.tf" in paths
    assert paths == sorted(p.name for p in second.glob("*.tf") if p.is_file())
    first_hashes = {name: hash_tf_feature(first / name) for name in paths}
    second_hashes = {name: hash_tf_feature(second / name) for name in paths}
    assert all(first_hashes[name][0] != second_hashes[name][0] for name in paths)
    assert all(first_hashes[name][1] == second_hashes[name][1] for name in paths)


@pytest.mark.parametrize("mutation", ["body", "metadata", "otype", "body-date-line"])
def test_semantic_hash_detects_content_and_nontimestamp_metadata_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    output = _graph(tmp_path, monkeypatch, "graph", datetime(2026, 10, 11, 8, 0))
    target = output / ("otype.tf" if mutation == "otype" else "title.tf")
    original = target.read_bytes()
    base = hash_tf_feature(target)
    if mutation == "body":
        changed = original.replace(b"Immutable glyph", b"Other glyph")
    elif mutation == "metadata":
        changed = original.replace(b"@writtenBy=Text-Fabric", b"@writtenBy=Unknown")
    elif mutation == "otype":
        changed = original.replace(b"word", b"wrod")
    else:
        changed = original + b"999999\t@dateWritten=2024-01-01T00:00:00Z\n"
    assert changed != original
    target.write_bytes(changed)
    raw, semantic = hash_tf_feature(target)
    assert raw != base[0] and semantic != base[1]


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "bad-date", "empty-date", "wrong-zone", "no-separator", "header-cr"],
)
def test_fails_closed_on_untrustworthy_timestamp_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    output = _graph(tmp_path, monkeypatch, "graph", datetime(2026, 10, 11, 8, 0))
    path = output / "otype.tf"
    original = path.read_bytes()
    timestamp = b"@dateWritten=2026-10-11T08:00:00+00:00Z\n"
    assert timestamp in original
    if mutation == "missing":
        altered = original.replace(timestamp, b"")
    elif mutation == "duplicate":
        altered = original.replace(timestamp, timestamp + timestamp)
    elif mutation == "bad-date":
        altered = original.replace(timestamp, b"@dateWritten=2026-99-99T08:00:00Z\n")
    elif mutation == "empty-date":
        altered = original.replace(timestamp, b"@dateWritten=\n")
    elif mutation == "wrong-zone":
        altered = original.replace(timestamp, b"@dateWritten=2026-10-11T08:00:00+03:00Z\n")
    elif mutation == "no-separator":
        altered = original.replace(b"\n\n", b"\n", 1)
    else:
        altered = original.replace(timestamp, timestamp + b"@extra=bad\rmetadata\n")
    assert altered != original
    path.write_bytes(altered)
    with pytest.raises(FingerprintError):
        hash_tf_feature(path)


def test_symlinked_features_are_not_hashable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _graph(tmp_path, monkeypatch, "graph", datetime(2026, 10, 11, 8, 0))
    linked = tmp_path / "linked.tf"
    linked.symlink_to(root / "otype.tf")
    with pytest.raises(FingerprintError, match="symlink"):
        hash_tf_feature(linked)


@pytest.mark.parametrize("marker", ["@node", "@edge", "@config"])
def test_windows_crlf_native_feature_header_preserves_timestamp_neutrality(
    tmp_path: Path, marker: str,
) -> None:
    """TF 13.1 uses text-mode writes, yielding CRLF on Windows."""
    path = tmp_path / "sample.tf"
    original = (
        f"{marker}\r\n@valueType=str\r\n"
        "@dateWritten=2026-10-11T08:00:00+00:00Z\r\n\r\n"
        "1\tword\r\n"
    ).encode("utf-8")
    path.write_bytes(original)
    first = hash_tf_feature(path)
    assert len(first[0]) == len(first[1]) == 64
    changed = original.replace(b"08:00:00", b"08:00:05")
    path.write_bytes(changed)
    second = hash_tf_feature(path)
    assert first[0] != second[0]
    assert first[1] == second[1]

    # The canonical hash removes *only* the clock line; it does not silently
    # normalize platform newlines (this is not a graph-isomorphism hash).
    lf_path = tmp_path / "unix.tf"
    lf_path.write_bytes(original.replace(b"\r\n", b"\n"))
    assert hash_tf_feature(lf_path)[1] != first[1]


@pytest.mark.parametrize("corruption", ["mixed", "embedded-cr", "oversized"])
def test_windows_header_rejects_unsafe_control_characters_and_bad_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str,
) -> None:
    from oraec_tf import tf_fingerprints

    feature = tmp_path / "header.tf"
    header = (
        b"@node\r\n@valueType=str\r\n"
        b"@dateWritten=2026-10-11T08:00:00+00:00Z\r\n\r\n"
        b"1\tword\r\n"
    )
    if corruption == "mixed":
        header = header.replace(
            b"@valueType=str\r\n", b"@valueType=str\n"
        )
    elif corruption == "embedded-cr":
        header = header.replace(
            b"@valueType=str\r\n", b"@valueType=s\rtr\r\n"
        )
    else:
        monkeypatch.setattr(tf_fingerprints, "HEADER_LIMIT", 128)
        header = header.replace(
            b"@valueType=str\r\n",
            b"@description=" + b"x" * 512 + b"\r\n",
        )
    feature.write_bytes(header)
    with pytest.raises(FingerprintError):
        hash_tf_feature(feature)
