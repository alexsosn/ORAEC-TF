from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from oraec_tf.source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceAcquisitionError,
    fetch_source,
)


def test_supported_source_is_pinned_to_immutable_commit() -> None:
    assert SOURCE_REPOSITORY == "https://github.com/oraec/corpus_raw_data.git"
    assert DEFAULT_SOURCE_REVISION == "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"
    assert len(DEFAULT_SOURCE_REVISION) == 40


def test_fetch_rejects_nonempty_destination_before_running_git() -> None:
    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        target.mkdir()
        (target / "sentinel").write_text("keep", encoding="utf-8")

        with patch("oraec_tf.source._run_git") as run_git:
            with pytest.raises(SourceAcquisitionError, match="not empty"):
                fetch_source(target)

        run_git.assert_not_called()


def test_fetch_clones_detached_revision_and_verifies_head() -> None:
    revision = DEFAULT_SOURCE_REVISION
    calls: list[tuple[list[str], bool]] = []

    def fake_run(
        args: list[str], *, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, capture_output))
        stdout = f"{revision}\n" if args[-2:] == ["rev-parse", "HEAD"] else ""
        return subprocess.CompletedProcess(["git", *args], 0, stdout=stdout, stderr="")

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        with patch("oraec_tf.source._run_git", side_effect=fake_run):
            snapshot = fetch_source(target)

    assert snapshot.revision == revision
    assert calls[0][0][:3] == ["clone", "--filter=blob:none", "--no-checkout"]
    assert SOURCE_REPOSITORY in calls[0][0]
    assert calls[1][0][-2:] == ["--detach", revision]
    assert calls[2][0][-2:] == ["rev-parse", "HEAD"]
    assert calls[2][1] is True


def test_fetch_fails_closed_on_revision_mismatch() -> None:
    wrong = "0" * 40

    def fake_run(
        args: list[str], *, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        stdout = f"{wrong}\n" if args[-2:] == ["rev-parse", "HEAD"] else ""
        return subprocess.CompletedProcess(["git", *args], 0, stdout=stdout, stderr="")

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        with patch("oraec_tf.source._run_git", side_effect=fake_run):
            with pytest.raises(SourceAcquisitionError, match="revision mismatch"):
                fetch_source(target)
