"""RED-first real Text-Fabric publication invariants for issue #54.

The source-checkout/parser boundaries are controlled tiny fixtures, but the TF
writer, TF reader and tf-build's atomic file publication are *real*.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from oraec_tf import cli
from oraec_tf.ir import CorpusMetadataIR, CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.source import DEFAULT_SOURCE_REVISION, SourceSnapshot


def _minimal_real_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    record = TextIR(
        oraec_id="oraec1",
        title="Source title",
        sentences=(
            SentenceIR(
                index=1,
                translation="",
                tokens=(TokenIR(token_id="oraec1-1-1", written_form="nṯr"),),
            ),
        ),
        credits=CreditsIR(
            license="cc-by-sa-4.0", author="Researcher",
            sources=("https://example.invalid/oraec",),
        ),
    )
    monkeypatch.setattr(
        cli, "verify_source",
        lambda *args, **kwargs: SourceSnapshot(source, DEFAULT_SOURCE_REVISION),
    )
    monkeypatch.setattr(
        cli, "validate_corpus_source",
        lambda *args, **kwargs: {
            "counts": {
                "texts": 1, "sentences": 1, "tokens": 1,
                "empty_token_sentences": 0,
            },
        },
    )
    monkeypatch.setattr(cli, "iter_texts", lambda *args: iter((record,)))
    monkeypatch.setattr(
        cli, "parse_corpus_metadata",
        lambda *args: CorpusMetadataIR(("Corpus Editor",)),
    )
    monkeypatch.setattr(cli, "parse_mapping_tables", lambda *args: ())
    monkeypatch.setattr(cli, "parse_hierarchy", lambda *args: ())
    return source


def test_publication_cannot_replace_destination_created_during_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real OS no-clobber primitive is exercised after generated TF validates."""
    from tf_build import workspace as ws

    source = _minimal_real_build(monkeypatch, tmp_path)
    target = tmp_path / "output"
    original_publish = ws.publish_path_no_clobber

    def competing_publish(staging: Path, destination: Path) -> None:
        assert (staging / "otype.tf").is_file()
        # A second process can create the target after our preflight.
        destination.mkdir()
        (destination / "sentinel").write_text("competing owner", encoding="utf-8")
        original_publish(staging, destination)

    monkeypatch.setattr(ws, "publish_path_no_clobber", competing_publish)
    with pytest.raises((FileExistsError, OSError)):
        cli._convert(str(source), str(target), DEFAULT_SOURCE_REVISION)
    assert (target / "sentinel").read_text(encoding="utf-8") == "competing owner"
    assert not (target / "otype.tf").exists()
    assert not tuple(tmp_path.glob(".output.tf-build-*"))
    assert not tuple(tmp_path.glob(".output.oraec-tf-*"))


def test_reject_unselected_corrupt_feature_even_if_counts_still_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counts-only loading misses damaged title.tf; full TF validation must fail."""
    source = _minimal_real_build(monkeypatch, tmp_path)
    target = tmp_path / "output"
    genuine_writer = cli.write_tf

    def corrupt_title(*args: Any, **kwargs: Any) -> None:
        genuine_writer(*args, **kwargs)
        stage = Path(args[1])
        assert (stage / "title.tf").is_file()
        # 'title' isn't among the three features selected by old _convert.
        (stage / "title.tf").write_text(
            "@node\n@valueType=wrong\n1\tchanged\n", encoding="utf-8"
        )

    monkeypatch.setattr(cli, "write_tf", corrupt_title)
    with pytest.raises(ValueError, match="title|value type|valueType|feature"):
        cli._convert(str(source), str(target), DEFAULT_SOURCE_REVISION)
    assert not target.exists()
    assert not tuple(tmp_path.glob(".output.tf-build-*"))


def test_existing_empty_output_remains_supported_with_atomic_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ORAEC allowed existing empty directories before tf-build integration."""
    source = _minimal_real_build(monkeypatch, tmp_path)
    target = tmp_path / "output"
    target.mkdir()
    summary = cli._convert(str(source), str(target), DEFAULT_SOURCE_REVISION)
    assert summary["counts"]["tokens"] == 1
    assert (target / "otype.tf").is_file()
    assert (target / "title.tf").is_file()
    assert not tuple(tmp_path.glob(".output.tf-build-*"))


def test_existing_empty_target_restored_after_late_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve original empty directory without deleting a rival's content."""
    source = _minimal_real_build(monkeypatch, tmp_path)
    target = tmp_path / "output"
    target.mkdir()

    def fail_writer(*args: Any, **kwargs: Any) -> None:
        stage = Path(args[1])
        (stage / "partial.tf").write_text("incomplete", encoding="utf-8")
        raise RuntimeError("deliberate late writer failure")

    monkeypatch.setattr(cli, "write_tf", fail_writer)
    with pytest.raises(RuntimeError, match="deliberate late"):
        cli._convert(str(source), str(target), DEFAULT_SOURCE_REVISION)
    assert target.is_dir()
    assert not tuple(target.iterdir())
    assert not tuple(tmp_path.glob(".output.tf-build-*"))
