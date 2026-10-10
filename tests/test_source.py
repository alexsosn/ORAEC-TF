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
    validate_revision,
    verify_source,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_source(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init")
    _git(source, "config", "user.email", "oraec-tf@example.invalid")
    _git(source, "config", "user.name", "ORAEC-TF tests")
    (source / "README.md").write_text("source\n", encoding="utf-8")
    _git(source, "add", "README.md")
    _git(source, "commit", "-m", "source")
    return source, _git(source, "rev-parse", "HEAD")


def test_supported_source_is_pinned_to_immutable_commit() -> None:
    assert SOURCE_REPOSITORY == "https://github.com/oraec/corpus_raw_data.git"
    assert DEFAULT_SOURCE_REVISION == "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"
    assert validate_revision(DEFAULT_SOURCE_REVISION) == DEFAULT_SOURCE_REVISION


@pytest.mark.parametrize(
    "revision",
    [
        "main",
        "HEAD",
        "v1.0",
        "b83a0ee",
        "g" * 40,
        "0" * 39,
        "0" * 41,
    ],
)
def test_revision_must_be_a_full_immutable_git_commit(revision: str) -> None:
    with pytest.raises(SourceAcquisitionError, match="full 40-hex"):
        validate_revision(revision)


def test_revision_is_normalized_to_lowercase() -> None:
    revision = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
    assert validate_revision(revision) == revision.lower()


def test_fetch_rejects_nonempty_destination_before_running_git() -> None:
    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        target.mkdir()
        (target / "sentinel").write_text("keep", encoding="utf-8")

        with patch("oraec_tf.source._run_git") as run_git:
            with pytest.raises(SourceAcquisitionError, match="not empty"):
                fetch_source(target)

        run_git.assert_not_called()


def test_fetch_rejects_symlink_destination_before_running_git(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    target = tmp_path / "source"
    target.symlink_to(real, target_is_directory=True)

    with patch("oraec_tf.source._run_git") as run_git:
        with pytest.raises(SourceAcquisitionError, match="symlink"):
            fetch_source(target)

    run_git.assert_not_called()


def test_fetch_rejects_dangling_symlink_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "source"
    target.symlink_to(tmp_path / "missing", target_is_directory=True)

    assert target.is_symlink()
    assert not target.exists()

    with patch("oraec_tf.source._run_git") as run_git:
        with pytest.raises(SourceAcquisitionError, match="symlink"):
            fetch_source(target)

    run_git.assert_not_called()
    assert target.is_symlink()
    assert target.readlink() == tmp_path / "missing"


def test_fetch_rejects_symbolic_revision_before_running_git() -> None:
    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"

        with patch("oraec_tf.source._run_git") as run_git:
            with pytest.raises(SourceAcquisitionError, match="full 40-hex"):
                fetch_source(target, revision="main")

        run_git.assert_not_called()


def test_verify_source_accepts_clean_exact_git_checkout(tmp_path: Path) -> None:
    source, revision = _make_git_source(tmp_path)

    snapshot = verify_source(source, expected_revision=revision)

    assert snapshot.path == source.resolve()
    assert snapshot.revision == revision


def test_verify_source_rejects_clean_nested_git_directory(tmp_path: Path) -> None:
    source, revision = _make_git_source(tmp_path)
    nested = source / "corpus"
    nested.mkdir()
    (nested / "oraec1.json").write_text("{}", encoding="utf-8")
    _git(source, "add", "corpus/oraec1.json")
    _git(source, "commit", "-m", "add nested corpus")

    with pytest.raises(SourceAcquisitionError, match="worktree root"):
        verify_source(nested, expected_revision=_git(source, "rev-parse", "HEAD"))


def test_verify_source_accepts_resolved_root_symlink(tmp_path: Path) -> None:
    source, revision = _make_git_source(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)

    snapshot = verify_source(alias, expected_revision=revision)

    assert snapshot.path == source.resolve()


def test_verify_source_rejects_revision_mismatch(tmp_path: Path) -> None:
    source, _revision = _make_git_source(tmp_path)

    with pytest.raises(SourceAcquisitionError, match="revision mismatch"):
        verify_source(source, expected_revision="0" * 40)


def test_verify_source_rejects_tracked_changes(tmp_path: Path) -> None:
    source, revision = _make_git_source(tmp_path)
    (source / "README.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(SourceAcquisitionError, match="dirty"):
        verify_source(source, expected_revision=revision)


def test_verify_source_rejects_untracked_files(tmp_path: Path) -> None:
    source, revision = _make_git_source(tmp_path)
    (source / "untracked.txt").write_text("x\n", encoding="utf-8")

    with pytest.raises(SourceAcquisitionError, match="dirty"):
        verify_source(source, expected_revision=revision)


def test_fetch_uses_exact_commit_fetch_and_detached_checkout() -> None:
    revision = DEFAULT_SOURCE_REVISION
    calls: list[tuple[list[str], bool]] = []

    def fake_run(
        args: list[str], *, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, capture_output))
        stdout = ""
        if args[-2:] == ["rev-parse", "HEAD"]:
            stdout = f"{revision}\n"
        elif args[-2:] == ["rev-parse", "--show-toplevel"]:
            stdout = str(Path(args[1]).resolve()) + "\n"
        elif args[-3:] == ["status", "--porcelain", "--untracked-files=all"]:
            stdout = ""
        return subprocess.CompletedProcess(["git", *args], 0, stdout=stdout, stderr="")

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        with patch("oraec_tf.source._run_git", side_effect=fake_run):
            snapshot = fetch_source(target)

        assert target.is_dir()

    assert snapshot.revision == revision
    command_args = [args for args, _capture in calls]
    assert any(args[-2:] == ["init", "--quiet"] for args in command_args)
    assert any(
        args[-5:] == ["fetch", "--depth", "1", "origin", revision]
        for args in command_args
    )
    assert any(
        args[-3:] == ["checkout", "--detach", "FETCH_HEAD"]
        for args in command_args
    )
    assert any(args[-2:] == ["rev-parse", "HEAD"] for args in command_args)
    assert any(args[-2:] == ["rev-parse", "--show-toplevel"] for args in command_args)
    assert any(
        args[-3:] == ["status", "--porcelain", "--untracked-files=all"]
        for args in command_args
    )


def test_fetch_failure_does_not_leave_partial_destination() -> None:
    def fail_fetch(
        args: list[str], *, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        if "fetch" in args:
            raise SourceAcquisitionError("fetch failed")
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        with patch("oraec_tf.source._run_git", side_effect=fail_fetch):
            with pytest.raises(SourceAcquisitionError, match="fetch failed"):
                fetch_source(target)

        assert not target.exists()


def test_fetch_failure_preserves_preexisting_empty_destination() -> None:
    def fail_fetch(
        args: list[str], *, capture_output: bool = False
    ) -> subprocess.CompletedProcess[str]:
        if "fetch" in args:
            raise SourceAcquisitionError("fetch failed")
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        target.mkdir()

        with patch("oraec_tf.source._run_git", side_effect=fail_fetch):
            with pytest.raises(SourceAcquisitionError, match="fetch failed"):
                fetch_source(target)

        assert target.is_dir()
        assert not any(target.iterdir())
