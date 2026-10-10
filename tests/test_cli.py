from __future__ import annotations

import json
import os
from contextlib import ExitStack
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from tf.fabric import Fabric
from tf_build.validate import ArtifactValidationError
from tf_build.workspace import BuildWorkspace

from oraec_tf.cli import main
from oraec_tf.ir import CorpusMetadataIR, CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceSnapshot,
)
from oraec_tf.writer import write_tf as real_write_tf


def test_source_info_reports_reproducible_default() -> None:
    output = StringIO()
    with patch("sys.stdout", output):
        assert main(["source-info"]) == 0

    payload = json.loads(output.getvalue())
    assert payload == {
        "repository": SOURCE_REPOSITORY,
        "revision": DEFAULT_SOURCE_REVISION,
    }


def test_verify_source_cli_uses_same_identity_contract() -> None:
    output = StringIO()
    snapshot = SourceSnapshot(
        path=Path("/verified/source"),
        revision=DEFAULT_SOURCE_REVISION,
    )

    with (
        patch("oraec_tf.cli.verify_source", return_value=snapshot) as verify,
        patch("sys.stdout", output),
    ):
        assert (
            main(
                [
                    "verify-source",
                    "/candidate/source",
                    "--revision",
                    DEFAULT_SOURCE_REVISION,
                ]
            )
            == 0
        )

    verify.assert_called_once_with(
        "/candidate/source",
        expected_revision=DEFAULT_SOURCE_REVISION,
    )
    assert json.loads(output.getvalue()) == {
        "path": "/verified/source",
        "revision": DEFAULT_SOURCE_REVISION,
    }


def test_convert_cli_builds_and_reloads_native_tf(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    destination = tmp_path / "tf"
    record = TextIR(
        oraec_id="oraec1",
        title="A",
        sentences=(
            SentenceIR(
                index=1,
                translation="",
                tokens=(TokenIR(token_id="oraec1-1-1", written_form="nṯr"),),
            ),
        ),
        credits=CreditsIR(
            license="cc-by-sa-4.0", author="Editor", sources=("https://a.invalid",)
        ),
    )
    counts = {
        "texts": 1, "sentences": 1, "tokens": 1, "empty_token_sentences": 0,
    }
    output = StringIO()
    with (
        patch(
            "oraec_tf.cli.verify_source",
            return_value=SourceSnapshot(path=source, revision=DEFAULT_SOURCE_REVISION),
        ) as verify,
        patch("oraec_tf.cli.validate_corpus_source", return_value={"counts": counts}),
        patch("oraec_tf.cli.iter_texts", return_value=iter((record,))),
        patch(
            "oraec_tf.cli.parse_corpus_metadata",
            return_value=CorpusMetadataIR(("README Contributor",)),
        ),
        patch("oraec_tf.cli.parse_hierarchy", return_value=()),
        patch("oraec_tf.cli.parse_mapping_tables", return_value=()),
        patch("sys.stdout", output),
    ):
        assert main([
            "convert", str(source), "--output", str(destination),
            "--upstream-commit", DEFAULT_SOURCE_REVISION,
        ]) == 0
    verify.assert_called_once_with(str(source), expected_revision=DEFAULT_SOURCE_REVISION)
    api = Fabric(locations=str(destination), silent="deep").load(
        "oraec_id token_id title", silent="deep"
    )
    assert len(api.F.otype.s("word")) == 1
    assert len(api.F.otype.s("text")) == 1
    assert api.F.token_id.v(api.F.otype.s("word")[0]) == "oraec1-1-1"
    assert json.loads(output.getvalue())["counts"]["tokens"] == 1


def test_convert_cli_rejects_output_inside_verified_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with patch(
        "oraec_tf.cli.verify_source",
        return_value=SourceSnapshot(path=source, revision=DEFAULT_SOURCE_REVISION),
    ):
        with pytest.raises(ValueError, match="output"):
            main([
                "convert", str(source), "--output", str(source / "generated"),
                "--upstream-commit", DEFAULT_SOURCE_REVISION,
            ])


def test_convert_cli_refuses_revision_not_in_frozen_schema(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="revision"):
        main([
            "convert", str(tmp_path), "--output", str(tmp_path / "tf"),
            "--upstream-commit", "a" * 40,
        ])


def test_convert_cli_does_not_publish_partial_output_on_writer_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "tf"

    def broken_writer(
        texts: object,
        output_dir: str | Path,
        **kwargs: object,
    ) -> None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "partial.tf").write_text("bad", encoding="utf-8")
        raise RuntimeError("deliberate late graph writer failure")

    with (
        patch(
            "oraec_tf.cli.verify_source",
            return_value=SourceSnapshot(path=source, revision=DEFAULT_SOURCE_REVISION),
        ),
        patch("oraec_tf.cli.validate_corpus_source", return_value={"counts": {}}),
        patch("oraec_tf.cli.iter_texts", return_value=iter(())),
        patch(
            "oraec_tf.cli.parse_corpus_metadata",
            return_value=CorpusMetadataIR(("README Contributor",)),
        ),
        patch("oraec_tf.cli.parse_hierarchy", return_value=()),
        patch("oraec_tf.cli.parse_mapping_tables", return_value=()),
        patch("oraec_tf.cli.write_tf", side_effect=broken_writer),
    ):
        with pytest.raises(RuntimeError, match="deliberate late"):
            main([
                "convert", str(source), "--output", str(target),
                "--upstream-commit", DEFAULT_SOURCE_REVISION,
            ])

    assert not target.exists()
    assert not list(tmp_path.glob(".tf.oraec-tf-*"))


def _synthetic_conversion_inputs(source: Path) -> ExitStack:
    """Mock source-only inputs, while exercising the real writer and TF loader."""
    record = TextIR(
        oraec_id="oraec1",
        title="A",
        sentences=(
            SentenceIR(
                index=1,
                translation="",
                tokens=(TokenIR(token_id="oraec1-1-1", written_form="nṯr"),),
            ),
        ),
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Editor",
            sources=("https://a.invalid",),
        ),
    )
    counts = {
        "texts": 1,
        "sentences": 1,
        "tokens": 1,
        "empty_token_sentences": 0,
    }
    stack = ExitStack()
    stack.enter_context(
        patch(
            "oraec_tf.cli.verify_source",
            return_value=SourceSnapshot(path=source, revision=DEFAULT_SOURCE_REVISION),
        )
    )
    stack.enter_context(
        patch("oraec_tf.cli.validate_corpus_source", return_value={"counts": counts})
    )
    stack.enter_context(
        patch("oraec_tf.cli.iter_texts", side_effect=lambda _source: iter((record,)))
    )
    stack.enter_context(
        patch(
            "oraec_tf.cli.parse_corpus_metadata",
            return_value=CorpusMetadataIR(("README Contributor",)),
        )
    )
    stack.enter_context(patch("oraec_tf.cli.parse_hierarchy", return_value=()))
    stack.enter_context(patch("oraec_tf.cli.parse_mapping_tables", return_value=()))
    return stack


def _synthetic_convert(source: Path, target: Path) -> int:
    return main(
        [
            "convert",
            str(source),
            "--output",
            str(target),
            "--upstream-commit",
            DEFAULT_SOURCE_REVISION,
        ]
    )


def test_convert_atomic_publication_preserves_concurrent_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED: a target appearing at publish time must never be overwritten."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "published"
    native_publish = BuildWorkspace.publish
    raced = False

    def competitor_at_publish(workspace: BuildWorkspace) -> Path:
        nonlocal raced
        assert workspace.destination == target
        target.mkdir()
        (target / "sentinel").write_text("concurrent owner's bytes", encoding="utf-8")
        raced = True
        return native_publish(workspace)

    monkeypatch.setattr("tf_build.workspace.BuildWorkspace.publish", competitor_at_publish)
    with _synthetic_conversion_inputs(source):
        with pytest.raises(FileExistsError):
            _synthetic_convert(source, target)

    assert raced, "the actual tf-build workspace must perform the final promotion"
    assert (target / "sentinel").read_text(encoding="utf-8") == "concurrent owner's bytes"
    assert sorted(p.name for p in target.iterdir()) == ["sentinel"]
    assert not tuple(tmp_path.glob(".published.tf-build-*"))


def test_convert_never_replaces_competing_empty_directory(
    tmp_path: Path,
) -> None:
    """POSIX regression: Path.replace could overwrite a raced EMPTY directory."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "published"
    competing_inode: list[int] = []

    def competitor_during_real_write(*args: Any, **kwargs: Any) -> None:
        assert not target.exists()
        target.mkdir()
        competing_inode.append(target.stat().st_ino)
        real_write_tf(*args, **kwargs)

    with (
        _synthetic_conversion_inputs(source),
        patch("oraec_tf.cli.write_tf", side_effect=competitor_during_real_write),
    ):
        with pytest.raises(FileExistsError):
            _synthetic_convert(source, target)

    assert competing_inode
    assert target.is_dir()
    assert target.stat().st_ino == competing_inode[0]
    assert not any(target.iterdir())
    assert not tuple(tmp_path.glob(".published.tf-build-*"))


def test_convert_rejects_invalid_raw_tf_despite_newer_binary_cache(
    tmp_path: Path,
) -> None:
    """RED: selected TF load alone is insufficient if a stale binary cache exists."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "published"

    def corrupt_after_writing(*args: Any, **kwargs: Any) -> None:
        real_write_tf(*args, **kwargs)
        stage = Path(args[1])
        feature = stage / "sentence_index.tf"
        cached_api = Fabric(locations=[str(stage)], silent="deep").load(
            "sentence_index", silent="deep"
        )
        assert cached_api is not None
        cached = tuple((stage / ".tf").rglob("sentence_index.tfx"))
        assert cached
        original = feature.stat()
        header, separator, _body = feature.read_bytes().partition(b"\n\n")
        assert separator
        feature.write_bytes(header + separator + b"1\tNOT_AN_INTEGER\n")
        os.utime(feature, ns=(original.st_atime_ns, original.st_mtime_ns))
        assert min(c.stat().st_mtime_ns for c in cached) >= feature.stat().st_mtime_ns

    with (
        _synthetic_conversion_inputs(source),
        patch("oraec_tf.cli.write_tf", side_effect=corrupt_after_writing),
    ):
        with pytest.raises(ArtifactValidationError, match="load"):
            _synthetic_convert(source, target)
    assert not target.exists()
    assert not tuple(tmp_path.glob(".published.tf-build-*"))


def test_convert_preserves_preexisting_empty_output_on_success_and_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    good = tmp_path / "good"
    good.mkdir()
    with _synthetic_conversion_inputs(source):
        assert _synthetic_convert(source, good) == 0
    assert (good / "otype.tf").is_file()

    failed = tmp_path / "failed"
    failed.mkdir()
    with (
        _synthetic_conversion_inputs(source),
        patch("oraec_tf.cli.write_tf", side_effect=RuntimeError("late writer failure")),
    ):
        with pytest.raises(RuntimeError, match="late writer failure"):
            _synthetic_convert(source, failed)
    assert failed.is_dir()
    assert not any(failed.iterdir())
    assert not tuple(tmp_path.glob(".failed.tf-build-*"))



def test_convert_rejects_parent_symlink_swapped_into_verified_source(
    tmp_path: Path,
) -> None:
    """A canonical output must be rechecked after the source audit boundary."""
    source = tmp_path / "source"
    source.mkdir()
    safe = tmp_path / "safe"
    safe.mkdir()
    alias = tmp_path / "output-alias"
    alias.symlink_to(safe, target_is_directory=True)
    target = alias / "generated"

    def adversarial_source_audit(_source: Path) -> dict[str, object]:
        # Initial target.resolve() is outside source; the parent alias changes
        # while the source is being audited, before BuildWorkspace canonicalizes.
        assert target.resolve() == (safe / "generated").resolve()
        alias.unlink()
        alias.symlink_to(source, target_is_directory=True)
        return {
            "counts": {
                "texts": 1, "sentences": 1, "tokens": 1,
                "empty_token_sentences": 0,
            }
        }

    with (
        _synthetic_conversion_inputs(source),
        patch(
            "oraec_tf.cli.validate_corpus_source",
            side_effect=adversarial_source_audit,
        ),
    ):
        with pytest.raises(ValueError, match="inside the source|source checkout"):
            _synthetic_convert(source, target)

    assert not (source / "generated").exists()
    assert not tuple(source.glob(".generated.tf-build-*"))
