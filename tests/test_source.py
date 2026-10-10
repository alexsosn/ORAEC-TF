from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from tf_build._atomic import publish_path_no_clobber
from tf_build.source import GitSourceError

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

        with patch("tf_build.source._run_git") as run_git:
            with pytest.raises(SourceAcquisitionError, match="not empty"):
                fetch_source(target)

        run_git.assert_not_called()


def test_fetch_rejects_symlink_destination_before_running_git(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    target = tmp_path / "source"
    target.symlink_to(real, target_is_directory=True)

    with patch("tf_build.source._run_git") as run_git:
        with pytest.raises(SourceAcquisitionError, match="symlink"):
            fetch_source(target)

    run_git.assert_not_called()


def test_fetch_rejects_dangling_symlink_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "source"
    target.symlink_to(tmp_path / "missing", target_is_directory=True)

    assert target.is_symlink()
    assert not target.exists()

    with patch("tf_build.source._run_git") as run_git:
        with pytest.raises(SourceAcquisitionError, match="symlink"):
            fetch_source(target)

    run_git.assert_not_called()
    assert target.is_symlink()
    assert target.readlink() == tmp_path / "missing"


def test_fetch_rejects_symbolic_revision_before_running_git() -> None:
    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"

        with patch("tf_build.source._run_git") as run_git:
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



def test_fetch_materializes_real_local_commit_without_storing_source_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED: old ORAEC fetch leaves the origin URL and FETCH_HEAD in the checkout."""
    from oraec_tf import source as source_module

    upstream, revision = _make_git_source(tmp_path)
    monkeypatch.setattr(source_module, "SOURCE_REPOSITORY", str(upstream))
    target = tmp_path / "acquired"
    snapshot = fetch_source(target, revision=revision.upper())

    assert snapshot.path == target.resolve()
    assert snapshot.revision == revision
    assert (target / "README.md").read_text(encoding="utf-8") == "source\n"
    assert _git(target, "status", "--porcelain", "--untracked-files=all") == ""
    assert _git(target, "rev-parse", "HEAD") == revision
    symbolic = subprocess.run(
        ["git", "-C", str(target), "symbolic-ref", "-q", "HEAD"],
        capture_output=True, text=True,
    )
    assert symbolic.returncode != 0
    assert _git(target, "remote") == "", "published source must not retain a remote URL"
    assert not (target / ".git" / "FETCH_HEAD").exists()
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))


def test_fetch_uses_source_specific_40_hex_contract_before_acquisition(
    tmp_path: Path,
) -> None:
    from oraec_tf import source as source_module

    with patch.object(source_module, "_run_git") as old_git:
        with pytest.raises(SourceAcquisitionError, match="40-hex"):
            fetch_source(tmp_path / "source", revision="f" * 64)
    old_git.assert_not_called()
    assert not (tmp_path / "source").exists()



def test_fetch_into_preexisting_empty_directory_preserves_detached_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from oraec_tf import source as source_module

    upstream, revision = _make_git_source(tmp_path)
    monkeypatch.setattr(source_module, "SOURCE_REPOSITORY", str(upstream))
    target = tmp_path / "acquired"
    target.mkdir()
    snapshot = fetch_source(target, revision=revision)
    assert snapshot.path == target.resolve()
    assert _git(target, "rev-parse", "HEAD") == revision
    assert _git(target, "remote") == ""
    assert not (target / ".git" / "FETCH_HEAD").exists()


def test_fetch_does_not_overwrite_concurrently_created_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from oraec_tf import source as source_module

    upstream, revision = _make_git_source(tmp_path)
    monkeypatch.setattr(source_module, "SOURCE_REPOSITORY", str(upstream))
    destination = tmp_path / "acquired"
    raced = False

    def raced_publish(staging: Path, target: Path) -> None:
        nonlocal raced
        assert target == destination
        target.mkdir()
        (target / "sentinel").write_text("other owner's bytes", encoding="utf-8")
        raced = True
        publish_path_no_clobber(staging, target)

    monkeypatch.setattr("tf_build.source.publish_path_no_clobber", raced_publish)
    with pytest.raises(SourceAcquisitionError):
        fetch_source(destination, revision=revision)

    assert raced
    assert (destination / "sentinel").read_text(encoding="utf-8") == "other owner's bytes"
    assert {p.name for p in destination.iterdir()} == {"sentinel"}
    assert not tuple(tmp_path.glob(".acquired.tf-build-*"))



def test_fetch_failure_does_not_leave_partial_destination() -> None:

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        with patch("tf_build.source._run_git", side_effect=GitSourceError("fetch failed")):
            with pytest.raises(SourceAcquisitionError, match="fetch failed"):
                fetch_source(target)

        assert not target.exists()


def test_fetch_failure_preserves_preexisting_empty_destination() -> None:

    with TemporaryDirectory() as temp:
        target = Path(temp) / "source"
        target.mkdir()

        with patch("tf_build.source._run_git", side_effect=GitSourceError("fetch failed")):
            with pytest.raises(SourceAcquisitionError, match="fetch failed"):
                fetch_source(target)

        assert target.is_dir()
        assert not any(target.iterdir())
