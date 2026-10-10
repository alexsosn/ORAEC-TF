from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from tf.fabric import Fabric

from oraec_tf.cli import main
from oraec_tf.ir import CorpusMetadataIR, CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceSnapshot,
)


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
